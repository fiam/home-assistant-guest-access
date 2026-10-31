"""Use real HA authentication, routing and service dispatch with synthetic locks."""

from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer
from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry,
    device_registry,
    entity_registry,
    floor_registry,
    frame,
    label_registry,
)
from homeassistant.setup import async_setup_component

from custom_components.guest_access import entity_available
from custom_components.guest_access.const import DOMAIN
from custom_components.guest_access.http import register_views
from custom_components.guest_access.manager import Manager


@pytest.fixture
async def http(setup, tmp_path):
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    frame.async_setup(hass)
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    device_registry.async_setup(hass)
    for registry in (
        floor_registry,
        area_registry,
        label_registry,
        device_registry,
        entity_registry,
    ):
        await registry.async_load(hass)
    hass.auth = await auth_manager_from_config(hass, [{"type": "homeassistant"}], [])

    async def opened(call):
        setup.calls.append((call.data["entity_id"], call.service))

    hass.services.async_register("lock", "open", opened)
    hass.services.async_register("lock", "unlock", opened)
    for entity in ("lock.synthetic_building", "lock.synthetic_apartment"):
        hass.states.async_set(entity, "locked", {"supported_features": 1})

    async def dispatch(entity, action):
        await hass.services.async_call(
            "lock", action, {"entity_id": entity}, blocking=True
        )

    manager = Manager(
        setup.store,
        dispatch,
        lambda e: hass.states.get(e) is not None,
        key_store=setup.key_store,
        now=lambda: setup.now,
    )
    await manager.load()
    setup.manager = hass.data[DOMAIN] = manager
    assets = {
        p.name: p.read_text()
        for p in (
            Path(__file__).parents[1] / "custom_components/guest_access/frontend"
        ).iterdir()
    }
    await async_setup_component(
        hass,
        "api",
        {
            "http": {
                "server_host": "127.0.0.1",
                "use_x_forwarded_for": True,
                "trusted_proxies": ["127.0.0.1"],
            }
        },
    )
    register_views(hass, assets)
    setup.hass = hass
    setup.headers = {}
    for role, group in (("admin", GROUP_ID_ADMIN), ("user", GROUP_ID_USER)):
        user = await hass.auth.async_create_user(role, group_ids=[group])
        refresh = await hass.auth.async_create_refresh_token(
            user, client_id="http://localhost/"
        )
        setup.headers[role] = {
            "Authorization": "Bearer " + hass.auth.async_create_access_token(refresh)
        }
    async with TestClient(TestServer(hass.http.app)) as client:
        setup.client = client
        yield setup
    await hass.async_stop(force=True)


async def create_guest(http, link_data):
    client = http.client
    response = await client.post(
        "/api/guest_access/admin/manage",
        headers=http.headers["admin"],
        json={
            "operation": "save",
            "link": link_data,
            "password": "synthetic-password-one",
        },
    )
    assert response.status == 200, await response.text()
    link_id = (await response.json())["id"]
    response = await client.post(
        "/api/guest_access/admin/manage",
        headers=http.headers["admin"],
        json={"operation": "enabled", "enabled": True},
    )
    assert response.status == 200
    response = await client.post(
        "/api/guest_access/login",
        json={"link": link_id, "password": "synthetic-password-one"},
    )
    assert response.status == 200, await response.text()
    result = await response.json()
    return link_id, {"X-Guest-Session": result["session"]}, result["actions"][0]["id"]


async def test_admin_requires_ha_admin_not_guest_session(http, link_data):
    link_id, guest, _ = await create_guest(http, link_data)
    for headers, expected in (({}, 401), (http.headers["user"], 403), (guest, 401)):
        response = await http.client.post(
            "/api/guest_access/admin/manage",
            headers=headers,
            json={"operation": "list"},
        )
        assert response.status == expected
    response = await http.client.get("/api/states", headers=guest)
    assert response.status == 401
    response = await http.client.get(
        "/api/states", headers={"Authorization": "Bearer " + guest["X-Guest-Session"]}
    )
    assert response.status == 401
    assert http.calls == []


async def test_page_loads_without_login_but_no_control_is_possible(http):
    response = await http.client.get("/guest-access")
    assert response.status == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    response = await http.client.post("/api/guest_access/status", json={})
    assert response.status == 401
    response = await http.client.get("/api/guest_access/action")
    assert response.status == 405
    assert http.calls == []


async def test_http_scoping_edit_and_no_guest_override(http, link_data):
    link_id, guest, action_id = await create_guest(http, link_data)
    payload = {"action_id": action_id, "request_id": "request-synthetic-001"}
    response = await http.client.post(
        "/api/guest_access/action",
        headers=guest,
        json=payload | {"entity_id": "lock.other"},
    )
    assert response.status == 400
    response = await http.client.post(
        "/api/guest_access/action", headers=guest, json=payload
    )
    assert response.status == 200
    assert http.calls == [("lock.synthetic_building", "open")]
    link_data["grants"].pop(0)
    response = await http.client.post(
        "/api/guest_access/admin/manage",
        headers=http.headers["admin"],
        json={"operation": "save", "link_id": link_id, "link": link_data, "version": 1},
    )
    assert response.status == 200
    response = await http.client.post(
        "/api/guest_access/action",
        headers=guest,
        json=payload | {"request_id": "request-synthetic-002"},
    )
    assert response.status == 403
    assert len(http.calls) == 1


@pytest.mark.parametrize(
    "headers,body,expected",
    [
        ({"Content-Type": "text/plain"}, "{}", 415),
        (
            {"Content-Type": "application/json", "Origin": "https://evil.invalid"},
            "{}",
            403,
        ),
        (
            {"Content-Type": "application/json", "Sec-Fetch-Site": "same-site"},
            "{}",
            403,
        ),
        ({"Content-Type": "application/json"}, "[]", 400),
        ({"Content-Type": "application/json"}, "{", 400),
        ({"Content-Type": "application/json"}, "x" * 5000, 413),
    ],
    ids=[
        "content-type",
        "foreign-origin",
        "same-site",
        "array",
        "invalid-json",
        "large-body",
    ],
)
async def test_rejects_bad_public_requests(http, headers, body, expected):
    response = await http.client.post(
        "/api/guest_access/action", headers=headers, data=body
    )
    assert response.status == expected
    assert http.calls == []


async def test_disabled_integration_closes_guest_access(http, link_data):
    _, guest, _ = await create_guest(http, link_data)
    http.hass.data.pop(DOMAIN)
    response = await http.client.post(
        "/api/guest_access/status", headers=guest, json={}
    )
    assert response.status == 503


async def test_http_revocation_and_password_reset(http, link_data):
    link_id, guest, action_id = await create_guest(http, link_data)
    response = await http.client.post(
        "/api/guest_access/admin/manage",
        headers=http.headers["admin"],
        json={
            "operation": "save",
            "link_id": link_id,
            "version": 1,
            "link": link_data,
            "password": "synthetic-password-two",
        },
    )
    assert response.status == 200
    response = await http.client.post(
        "/api/guest_access/action",
        headers=guest,
        json={"action_id": action_id, "request_id": "request-reset-000001"},
    )
    assert response.status == 401
    assert http.calls == []


async def test_https_origin_and_client_ip_behind_trusted_proxy(http, link_data):
    link_id, _, _ = await create_guest(http, link_data)
    response = await http.client.post(
        "/api/guest_access/login",
        headers={
            "Host": "ha.example.invalid",
            "Origin": "https://ha.example.invalid",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "203.0.113.10",
        },
        json={"link": link_id, "password": "synthetic-password-one"},
    )
    assert response.status == 200, await response.text()
    assert ("peer", "203.0.113.10") in http.manager.attempts


async def test_missing_device_cannot_block_pausing_its_link(http, link_data):
    link_id, guest, _ = await create_guest(http, link_data)
    http.hass.states.async_remove("lock.synthetic_building")
    link_data["enabled"] = False
    response = await http.client.post(
        "/api/guest_access/admin/manage",
        headers=http.headers["admin"],
        json={"operation": "save", "link_id": link_id, "link": link_data, "version": 1},
    )
    assert response.status == 200
    response = await http.client.post(
        "/api/guest_access/status", headers=guest, json={}
    )
    assert response.status == 401


async def test_password_retrieval_is_explicit_admin_only_and_not_cached(
    http, link_data
):
    link_id, guest, _ = await create_guest(http, link_data)
    payload = {"operation": "reveal_password", "link_id": link_id}
    for headers, expected in (({}, 401), (http.headers["user"], 403), (guest, 401)):
        response = await http.client.post(
            "/api/guest_access/admin/manage", headers=headers, json=payload
        )
        assert response.status == expected
        assert "synthetic-password-one" not in await response.text()
    for _ in range(2):
        response = await http.client.post(
            "/api/guest_access/admin/manage",
            headers=http.headers["admin"],
            json=payload,
        )
        assert response.status == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert await response.json() == {"password": "synthetic-password-one"}
    for operation in ("list",):
        response = await http.client.post(
            "/api/guest_access/admin/manage",
            headers=http.headers["admin"],
            json={"operation": operation},
        )
        text = await response.text()
        assert "synthetic-password-one" not in text
        assert "password_encrypted" not in text
    response = await http.client.post(
        "/api/guest_access/reveal_password", headers=guest, json={}
    )
    assert response.status == 404
    response = await http.client.post(
        "/api/guest_access/status", headers=guest, json={}
    )
    data = await response.json()
    assert data["actions"][0]["kind"] == "lock.open"
    assert "synthetic-password-one" not in str(data)
    assert http.calls == []


async def remembered_cookie(http, link_data, remember=True):
    link_id, _, _ = await create_guest(http, link_data)
    headers = {
        "Host": "ha.example.invalid",
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "203.0.113.10",
        "Origin": "https://ha.example.invalid",
    }
    response = await http.client.post(
        "/api/guest_access/login",
        headers=headers,
        json={
            "link": link_id,
            "password": "synthetic-password-one",
            "remember": remember,
        },
    )
    assert response.status == 200, await response.text()
    assert "session" not in await response.json()
    cookie = next(iter(response.cookies.values()))
    assert cookie["secure"] and cookie["httponly"]
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/api/guest_access"
    assert not cookie["domain"]
    assert cookie.key.startswith("__Secure-guest_access_")
    assert cookie["max-age"] == ("31536000" if remember else "")
    return (
        link_id,
        headers | {"X-Guest-Link": link_id, "Cookie": f"{cookie.key}={cookie.value}"},
        cookie,
    )


async def test_cookie_resume_after_reload_and_logout_is_persistent(http, link_data):
    link_id, headers, cookie = await remembered_cookie(http, link_data)
    m = http.manager
    restarted = Manager(
        http.store, m.dispatch, m.available, key_store=http.key_store, now=m.now
    )
    await restarted.load()
    http.hass.data[DOMAIN] = restarted
    response = await http.client.post(
        "/api/guest_access/status", headers=headers, json={}
    )
    assert response.status == 200
    assert len((await response.json())["actions"]) == 2
    response = await http.client.get("/api/states", headers=headers)
    assert response.status == 401
    response = await http.client.post(
        "/api/guest_access/admin/manage", headers=headers, json={"operation": "list"}
    )
    assert response.status == 401
    response = await http.client.post(
        "/api/guest_access/logout", headers=headers, json={}
    )
    assert response.status == 200
    assert response.cookies[cookie.key]["max-age"] == "0"
    await restarted.load()
    response = await http.client.post(
        "/api/guest_access/status", headers=headers, json={}
    )
    assert response.status == 401
    assert http.calls == []


async def test_cookie_cannot_select_another_link_or_allow_foreign_origin(
    http, link_data
):
    _, headers, _ = await remembered_cookie(http, link_data)
    response = await http.client.post(
        "/api/guest_access/status",
        headers=headers | {"X-Guest-Link": "a" * 43},
        json={},
    )
    assert response.status == 401
    response = await http.client.post(
        "/api/guest_access/action",
        headers=headers | {"Origin": "https://evil.invalid"},
        json={},
    )
    assert response.status == 403
    response = await http.client.post(
        "/api/guest_access/action",
        headers=headers | {"Sec-Fetch-Site": "cross-site"},
        json={},
    )
    assert response.status == 403
    assert http.calls == []


async def test_browser_can_choose_a_nonpersistent_cookie(http, link_data):
    _, headers, _ = await remembered_cookie(http, link_data, remember=False)
    assert not http.store.data["sessions"]
    await http.manager.load()
    response = await http.client.post(
        "/api/guest_access/status", headers=headers, json={}
    )
    assert response.status == 401


async def test_admin_updates_require_current_version_and_pause_is_scoped(
    http, link_data
):
    link_id, _, _ = await create_guest(http, link_data)
    url = "/api/guest_access/admin/manage"
    for version in (None, True, 0):
        response = await http.client.post(
            url,
            headers=http.headers["admin"],
            json={
                "operation": "save",
                "link_id": link_id,
                "link": link_data,
                "version": version,
            },
        )
        assert response.status == 409
    response = await http.client.post(
        url,
        headers=http.headers["admin"],
        json={
            "operation": "link_enabled",
            "link_id": link_id,
            "enabled": False,
        },
    )
    assert response.status == 200
    state = await response.json()
    assert state["links"][0]["enabled"] is False
    assert len(state["links"][0]["grants"]) == 2
    response = await http.client.post(
        url,
        headers=http.headers["admin"],
        json={
            "operation": "link_enabled",
            "link_id": link_id,
            "enabled": True,
            "link": link_data,
        },
    )
    assert response.status == 400


async def test_new_unpressed_button_is_available_but_unknown_lock_is_not(http):
    hass = http.hass
    assert await async_setup_component(
        hass,
        "input_button",
        {"input_button": {"synthetic_new": {"name": "Synthetic new button"}}},
    )
    await hass.async_block_till_done()
    entity = "input_button.synthetic_new"
    assert hass.states.get(entity).state == "unknown"
    assert entity_available(hass, entity)
    hass.states.async_set("button.synthetic_new", "unknown")
    assert entity_available(hass, "button.synthetic_new")
    hass.states.async_set("lock.synthetic_unknown", "unknown")
    assert not entity_available(hass, "lock.synthetic_unknown")
    hass.states.async_set(entity, "unavailable")
    assert not entity_available(hass, entity)
    assert not entity_available(hass, "button.synthetic_missing")


async def test_device_catalog_and_slider_dispatch_use_only_granted_targets(
    http, link_data
):
    from custom_components.guest_access.controls import device_state, dispatch_action

    hass, m = http.hass, http.manager
    calls = []

    async def record(call):
        calls.append((call.domain, call.service, dict(call.data)))

    for domain, services in {
        "light": ("turn_on", "turn_off"),
        "cover": ("open_cover", "close_cover", "stop_cover", "set_cover_position"),
    }.items():
        for service in services:
            hass.services.async_register(domain, service, record)
    hass.states.async_set(
        "light.synthetic_dimmer",
        "on",
        {
            "supported_color_modes": ["brightness"],
            "brightness": 128,
        },
    )
    hass.states.async_set(
        "light.synthetic_basic", "off", {"supported_color_modes": ["onoff"]}
    )
    hass.states.async_set(
        "cover.synthetic_blind",
        "open",
        {"supported_features": 15, "current_position": 75},
    )
    hass.states.async_set("cover.synthetic_basic", "closed", {"supported_features": 3})
    result = await http.client.post(
        "/api/guest_access/admin/manage",
        headers=http.headers["admin"],
        json={"operation": "list"},
    )
    catalog = {(c["entity_id"], c["action"]) for c in (await result.json())["catalog"]}
    assert ("light.synthetic_dimmer", "set_brightness") in catalog
    assert ("cover.synthetic_blind", "set_cover_position") in catalog
    assert ("light.synthetic_basic", "set_brightness") not in catalog
    assert ("cover.synthetic_basic", "set_cover_position") not in catalog
    assert ("cover.synthetic_basic", "stop_cover") not in catalog
    link_data["grants"] = [
        {
            "entity_id": "light.synthetic_dimmer",
            "action": "set_brightness",
            "label": "Room light",
        },
        {
            "entity_id": "cover.synthetic_blind",
            "action": "set_cover_position",
            "label": "Room blind",
        },
    ]
    saved = await m.save_link(link_data, password="synthetic-password-one")
    await m.set_enabled(True)
    m.describe = lambda entity: device_state(hass, entity)
    m.monotonic = lambda: http.clock

    async def dispatch(entity, action, value=None):
        await dispatch_action(hass, entity, action, value)

    m.dispatch = dispatch
    token = await m.login(saved["id"], "synthetic-password-one", "peer")
    headers = {"X-Guest-Session": token}
    actions = m.status(token)["actions"]
    assert [action["value"] for action in actions] == [50, 75]
    assert all("entity_id" not in action for action in actions)
    for i, value in enumerate([0, 100]):
        reply = await http.client.post(
            "/api/guest_access/action",
            headers=headers,
            json={
                "action_id": actions[i]["id"],
                "request_id": f"synthetic-slider-{i}",
                "value": value,
            },
        )
        assert reply.status == 200
        http.clock += 4
    assert calls == [
        (
            "light",
            "turn_on",
            {"entity_id": "light.synthetic_dimmer", "brightness_pct": 0},
        ),
        (
            "cover",
            "set_cover_position",
            {"entity_id": "cover.synthetic_blind", "position": 100},
        ),
    ]
    reply = await http.client.post(
        "/api/guest_access/action",
        headers=headers,
        json={
            "action_id": actions[0]["id"],
            "request_id": "synthetic-bad-target",
            "value": 25,
            "entity_id": "light.synthetic_basic",
        },
    )
    assert reply.status == 400
    assert len(calls) == 2
