"""Describe controllable entities using their Home Assistant device and area."""

from homeassistant.helpers import area_registry, device_registry, entity_registry

from .const import ACTION_NAMES, ALLOWED_ACTIONS
from .controls import action_supported, entity_available


def build_catalog(hass, links):
    """Group presentation by device; permissions remain explicit entity/actions."""
    entities = entity_registry.async_get(hass)
    devices = device_registry.async_get(hass)
    areas = area_registry.async_get(hass)
    metadata = {}
    choices = {}

    def describe(entity_id):
        if entity_id in metadata:
            return metadata[entity_id]
        state = hass.states.get(entity_id)
        entity = entities.async_get(entity_id)
        device = (
            devices.async_get(entity.device_id) if entity and entity.device_id else None
        )
        area_id = (entity.area_id if entity else None) or (
            device.area_id if device else None
        )
        area = areas.async_get_area(area_id) if area_id else None
        name = (
            (state.attributes.get("friendly_name") if state else None)
            or (entity.name or entity.original_name if entity else None)
            or entity_id
        )
        metadata[entity_id] = {
            "entity_id": entity_id,
            "name": name,
            "device_id": device.id if device else None,
            "device_name": (device.name_by_user or device.name if device else None)
            or name,
            "area": area.name if area else None,
            "maintenance": bool(
                entity and entity.entity_category in ("config", "diagnostic")
            ),
            "available": entity_available(hass, entity_id),
        }
        return metadata[entity_id]

    def add(entity_id, action, selectable):
        choices[(entity_id, action)] = {
            **describe(entity_id),
            "action": action,
            "action_name": ACTION_NAMES.get(action, action.replace("_", " ")),
            "selectable": selectable,
        }

    for state in hass.states.async_all():
        domain = state.entity_id.split(".", 1)[0]
        for action in ALLOWED_ACTIONS.get(domain, ()):
            if action_supported(hass, state.entity_id, action):
                add(state.entity_id, action, True)

    # Keep unavailable saved permissions editable, with their registry grouping.
    # They are offered only on links that already contain the permission.
    for record in links.values():
        for grant in record["grants"]:
            pair = (grant["entity_id"], grant["action"])
            if pair not in choices:
                add(*pair, False)
    return list(choices.values())
