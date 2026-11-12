"""Management logic; the HTTP adapter requires an authenticated HA administrator."""

from .catalog import build_catalog
from .const import DOMAIN
from .controls import action_supported
from .manager import AccessError, validate_link


async def manage(hass, msg):
    if not isinstance(msg, dict) or set(msg) - {
        "operation",
        "link_id",
        "link",
        "password",
        "enabled",
        "version",
    }:
        raise AccessError("invalid_request", 400)
    if "link_id" in msg and not isinstance(msg["link_id"], str):
        raise AccessError("invalid_request", 400)
    manager = hass.data.get(DOMAIN)
    if manager is None or manager.closed:
        raise AccessError("unavailable", 503)
    result = {}
    operation = msg.get("operation")
    if operation not in {
        "list",
        "save",
        "delete",
        "enabled",
        "link_enabled",
        "reveal_password",
    }:
        raise AccessError("invalid_request", 400)
    if operation == "reveal_password":
        if set(msg) != {"operation", "link_id"}:
            raise AccessError("invalid_request", 400)
        return await manager.reveal_password(msg["link_id"])
    if operation == "save":
        if "link_id" in msg and type(msg.get("version")) is not int:
            raise AccessError("conflict", 409)
        link = msg.get("link")
        cleaned = validate_link(link)
        existing = manager.links.get(msg.get("link_id"), {})
        previous_grants = {
            (g["entity_id"], g["action"]) for g in existing.get("grants", [])
        }
        for grant in cleaned["grants"]:
            # A disappeared device must not prevent pausing or shortening a link.
            if (grant["entity_id"], grant["action"]) in previous_grants:
                continue
            if not action_supported(hass, grant["entity_id"], grant["action"]):
                raise AccessError("entity_or_action_missing", 400)
        result = await manager.save_link(
            link,
            link_id=msg.get("link_id"),
            password=msg.get("password"),
            expected_version=msg.get("version"),
        )
    elif operation == "delete":
        await manager.delete_link(msg.get("link_id"))
    elif operation == "link_enabled":
        if set(msg) != {"operation", "link_id", "enabled"}:
            raise AccessError("invalid_request", 400)
        await manager.set_link_enabled(msg["link_id"], msg["enabled"])
    elif operation == "enabled":
        await manager.set_enabled(msg.get("enabled"))
    catalog = build_catalog(hass, manager.links)
    base_url = hass.config.external_url or hass.config.internal_url or ""
    return {**manager.admin_state(), "catalog": catalog, "base_url": base_url, **result}
