"""Management logic; the HTTP adapter requires an authenticated HA administrator."""

from .const import ACTION_NAMES, ALLOWED_ACTIONS, DOMAIN
from .manager import AccessError, validate_link


async def manage(hass, msg):
    if not isinstance(msg, dict) or set(msg) - {
        "operation",
        "link_id",
        "link",
        "password",
        "enabled",
    }:
        raise AccessError("invalid_request", 400)
    if "link_id" in msg and not isinstance(msg["link_id"], str):
        raise AccessError("invalid_request", 400)
    manager = hass.data.get(DOMAIN)
    if manager is None or manager.closed:
        raise AccessError("unavailable", 503)
    result = {}
    operation = msg.get("operation")
    if operation not in {"list", "save", "delete", "enabled", "reveal_password"}:
        raise AccessError("invalid_request", 400)
    if operation == "reveal_password":
        if set(msg) != {"operation", "link_id"}:
            raise AccessError("invalid_request", 400)
        return await manager.reveal_password(msg["link_id"])
    if operation == "save":
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
            entity = hass.states.get(grant["entity_id"])
            domain = grant["entity_id"].split(".", 1)[0]
            if entity is None or not hass.services.has_service(domain, grant["action"]):
                raise AccessError("entity_or_action_missing", 400)
            if (
                domain == "lock"
                and grant["action"] == "open"
                and not (entity.attributes.get("supported_features", 0) & 1)
            ):
                raise AccessError("open_not_supported", 400)
        result = await manager.save_link(
            link, link_id=msg.get("link_id"), password=msg.get("password")
        )
    elif operation == "delete":
        await manager.delete_link(msg.get("link_id"))
    elif operation == "enabled":
        await manager.set_enabled(msg.get("enabled"))
    catalog = []
    for state in hass.states.async_all():
        domain = state.entity_id.split(".", 1)[0]
        for action in ALLOWED_ACTIONS.get(domain, ()):
            if not hass.services.has_service(domain, action):
                continue
            if (
                domain == "lock"
                and action == "open"
                and not state.attributes.get("supported_features", 0) & 1
            ):
                continue
            catalog.append(
                {
                    "entity_id": state.entity_id,
                    "action": action,
                    "name": state.attributes.get("friendly_name", state.entity_id),
                    "action_name": ACTION_NAMES[action],
                }
            )
    base_url = hass.config.external_url or hass.config.internal_url or ""
    return {**manager.admin_state(), "catalog": catalog, "base_url": base_url, **result}
