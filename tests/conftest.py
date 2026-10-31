import copy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from custom_components.guest_access.manager import Manager


class MemoryStore:
    def __init__(self):
        self.data = None
        self.fail = False

    async def async_load(self):
        return copy.deepcopy(self.data)

    async def async_save(self, data):
        if self.fail:
            raise OSError("synthetic disk failure")
        self.data = copy.deepcopy(data)


@pytest.fixture
async def setup():
    state = SimpleNamespace(
        now=datetime(2026, 10, 31, 12, tzinfo=UTC),
        clock=1000.0,
        calls=[],
        unavailable=set(),
        store=MemoryStore(),
        key_store=MemoryStore(),
    )

    async def dispatch(entity_id, action):
        state.calls.append((entity_id, action))

    state.manager = Manager(
        state.store,
        dispatch,
        lambda e: e not in state.unavailable,
        key_store=state.key_store,
        now=lambda: state.now,
        monotonic=lambda: state.clock,
    )
    await state.manager.load()
    return state


@pytest.fixture
def link_data():
    return {
        "name": "Synthetic guest",
        "enabled": True,
        "starts_at": "2026-10-31T11:00:00+00:00",
        "expires_at": "2026-10-31T14:00:00+00:00",
        "grants": [
            {
                "entity_id": "lock.synthetic_building",
                "action": "open",
                "label": "Abrir prédio",
            },
            {
                "entity_id": "lock.synthetic_apartment",
                "action": "open",
                "label": "Abrir casa",
            },
        ],
    }


@pytest.fixture
async def authorized(setup, link_data):
    manager = setup.manager
    await manager.set_enabled(True)
    result = await manager.save_link(link_data, password="synthetic-password-one")
    setup.link_id = result["id"]
    setup.session = await manager.login(
        setup.link_id, "synthetic-password-one", "test-peer"
    )
    setup.action_id = manager.status(setup.session)["actions"][0]["id"]
    return setup
