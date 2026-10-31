"""Minimal public endpoints. Guests cannot call HA APIs with these sessions."""

import hashlib
import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.const import KEY_HASS_USER

from .admin import manage
from .const import DOMAIN
from .manager import AccessError

HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    ),
}


def register_views(hass, assets):
    class AdminView(HomeAssistantView):
        url = "/api/guest_access/admin/manage"
        name = "guest_access:admin"
        requires_auth = True

        async def post(self, request):
            try:
                if not request[KEY_HASS_USER].is_admin:
                    raise AccessError("admin_required")
                if request.content_type != "application/json":
                    raise AccessError("json_required", 415)
                body = bytearray()
                async for chunk in request.content.iter_chunked(4096):
                    body.extend(chunk)
                    if len(body) > 32768:
                        raise AccessError("body_too_large", 413)
                import json

                try:
                    data = json.loads(body)
                except ValueError, UnicodeDecodeError:
                    raise AccessError("invalid_request", 400) from None
                return web.json_response(await manage(hass, data), headers=HEADERS)
            except AccessError as error:
                return web.json_response(
                    {"message": error.code.replace("_", " ")},
                    status=error.status,
                    headers=HEADERS,
                )

    class AssetView(HomeAssistantView):
        url = "/guest-access"
        extra_urls = ["/guest-access/assets/{filename}"]
        name = "guest_access:page"
        requires_auth = False

        async def get(self, request, filename="guest.html"):
            if filename not in assets:
                raise web.HTTPNotFound()
            content_type = {
                "html": "text/html",
                "js": "text/javascript",
                "css": "text/css",
            }[filename.rsplit(".", 1)[1]]
            return web.Response(
                text=assets[filename], content_type=content_type, headers=HEADERS
            )

    class GuestView(HomeAssistantView):
        url = "/api/guest_access/{operation}"
        name = "guest_access:api"
        requires_auth = False

        async def post(self, request, operation):
            cookie_name = None
            try:
                if operation not in {"login", "status", "action", "logout"}:
                    raise AccessError("not_found", 404)
                if request.content_type != "application/json":
                    raise AccessError("json_required", 415)
                if request.headers.get("Sec-Fetch-Site", "same-origin") not in {
                    "same-origin",
                    "none",
                }:
                    raise AccessError("origin_rejected")
                origin = request.headers.get("Origin")
                if origin and origin != f"{request.scheme}://{request.host}":
                    raise AccessError("origin_rejected")
                # Bound both declared and chunked bodies before decoding.
                body = bytearray()
                async for chunk in request.content.iter_chunked(2048):
                    body.extend(chunk)
                    if len(body) > 4096:
                        raise AccessError("body_too_large", 413)
                import json

                try:
                    data = json.loads(body)
                except ValueError, UnicodeDecodeError:
                    raise AccessError("invalid_request", 400) from None
                if not isinstance(data, dict):
                    raise AccessError("invalid_request", 400)
                manager = hass.data.get(DOMAIN)
                if manager is None or manager.closed:
                    raise AccessError("unavailable", 503)
                link_id = (
                    data.get("link")
                    if operation == "login"
                    else request.headers.get("X-Guest-Link")
                )
                cookie_mode = (operation == "login" and "remember" in data) or (
                    operation != "login"
                    and bool(link_id)
                    and not request.headers.get("X-Guest-Session")
                )
                if cookie_mode:
                    if not isinstance(link_id, str) or not re.fullmatch(
                        r"[A-Za-z0-9_-]{43}", link_id
                    ):
                        raise AccessError("invalid_request", 400)
                    cookie_name = (
                        ("__Secure-" if request.scheme == "https" else "")
                        + "guest_access_"
                        + hashlib.sha256(link_id.encode()).hexdigest()[:32]
                    )
                token = request.headers.get(
                    "X-Guest-Session", ""
                ) or request.cookies.get(cookie_name, "")
                remembered = False
                if operation == "login":
                    if set(data) not in (
                        {"link", "password"},
                        {"link", "password", "remember"},
                    ):
                        raise AccessError("invalid_request", 400)
                    old_token = token
                    token = await manager.login(
                        data["link"],
                        data["password"],
                        request.remote,
                        remember=data.get("remember", False),
                    )
                    if cookie_mode and old_token:
                        await manager.logout(old_token)
                    remembered = data.get("remember", False)
                    result = manager.status(token)
                    if not cookie_mode:
                        result["session"] = token
                else:
                    if cookie_mode and operation != "logout":
                        remembered = await manager.refresh_session(token, link_id)
                    if operation == "action":
                        if set(data) != {"action_id", "request_id"}:
                            raise AccessError("invalid_request", 400)
                        await manager.action(
                            token, data["action_id"], data["request_id"]
                        )
                        result = {"requested": True}
                    else:
                        if data:
                            raise AccessError("invalid_request", 400)
                        if operation == "logout":
                            await manager.logout(token)
                            result = {}
                        else:
                            result = manager.status(token)
                response = web.json_response(result, headers=HEADERS)
                if cookie_name:
                    if operation == "logout":
                        response.del_cookie(
                            cookie_name,
                            path="/api/guest_access",
                            secure=request.scheme == "https",
                            httponly=True,
                            samesite="Strict",
                        )
                    else:
                        response.set_cookie(
                            cookie_name,
                            token,
                            path="/api/guest_access",
                            max_age=31536000 if remembered else None,
                            secure=request.scheme == "https",
                            httponly=True,
                            samesite="Strict",
                        )
                return response
            except AccessError as error:
                headers = HEADERS | (
                    {"Retry-After": "60"} if error.status == 429 else {}
                )
                response = web.json_response(
                    {"error": error.code}, status=error.status, headers=headers
                )
                if cookie_name and error.status == 401:
                    response.del_cookie(
                        cookie_name,
                        path="/api/guest_access",
                        secure=request.scheme == "https",
                        httponly=True,
                        samesite="Strict",
                    )
                return response

    hass.http.register_view(AssetView())
    hass.http.register_view(AdminView())
    hass.http.register_view(GuestView())
