import asyncio
import copy
import json
from datetime import timedelta

import pytest

from custom_components.guest_access.manager import AccessError, Manager, validate_link


async def test_link_alone_and_wrong_password_never_authorize(setup, link_data):
    result = await setup.manager.save_link(link_data, password="synthetic-password-one")
    for password in ("", "wrong-password"):
        with pytest.raises(AccessError, match="invalid_credentials"):
            await setup.manager.login(result["id"], password, "peer")
    with pytest.raises(AccessError, match="sign_in"):
        setup.manager.status(result["id"])
    assert setup.calls == []
    stored = json.dumps(setup.store.data)
    assert "synthetic-password-one" not in stored
    assert "password_hash" not in json.dumps(setup.manager.admin_state())


async def test_explicit_actions_and_no_target_substitution(authorized):
    m = authorized.manager
    status = m.status(authorized.session)
    assert "entity_id" not in json.dumps(status)
    with pytest.raises(AccessError, match="not_allowed"):
        await m.action(authorized.session, "lock.other.unlock", "request-substitute-01")
    await m.action(authorized.session, authorized.action_id, "request-approved-001")
    assert authorized.calls == [("lock.synthetic_building", "open")]


async def test_edit_applies_to_existing_session(authorized, link_data):
    m = authorized.manager
    link_data["grants"].pop(0)
    await m.save_link(link_data, link_id=authorized.link_id)
    with pytest.raises(AccessError, match="not_allowed"):
        await m.action(authorized.session, authorized.action_id, "request-removed-0001")
    assert len(m.status(authorized.session)["actions"]) == 1
    link_data["expires_at"] = authorized.now.isoformat()
    await m.save_link(link_data, link_id=authorized.link_id)
    with pytest.raises(AccessError, match="outside_window"):
        m.status(authorized.session)
    # Extension uses current settings without minting a stale session scope.
    link_data["expires_at"] = (authorized.now + timedelta(hours=1)).isoformat()
    await m.save_link(link_data, link_id=authorized.link_id)
    assert m.status(authorized.session)
    assert authorized.calls == []


async def test_start_and_end_boundaries(authorized, link_data):
    m = authorized.manager
    authorized.now = authorized.now.replace(hour=11)
    assert m.status(authorized.session)
    authorized.now -= timedelta(microseconds=1)
    with pytest.raises(AccessError, match="outside_window"):
        m.status(authorized.session)
    authorized.now = authorized.now.replace(hour=14, minute=0, second=0, microsecond=0)
    with pytest.raises(AccessError, match="outside_window"):
        await m.action(authorized.session, authorized.action_id, "request-expired-0001")
    assert authorized.calls == []


@pytest.mark.parametrize("operation", ["pause", "global", "delete", "password"])
async def test_revocation_invalidates_existing_session(
    authorized, link_data, operation
):
    m = authorized.manager
    if operation == "global":
        await m.set_enabled(False)
        await m.set_enabled(True)
    elif operation == "delete":
        await m.delete_link(authorized.link_id)
    elif operation == "password":
        await m.save_link(
            link_data, link_id=authorized.link_id, password="synthetic-new-password"
        )
    else:
        link_data["enabled"] = False
        await m.save_link(link_data, link_id=authorized.link_id)
        link_data["enabled"] = True
        await m.save_link(link_data, link_id=authorized.link_id)
    with pytest.raises(AccessError, match="sign_in"):
        await m.action(authorized.session, authorized.action_id, "request-revoked-001")
    assert authorized.calls == []


async def test_rate_limit_cannot_be_bypassed_by_changing_links(setup):
    for i in range(10):
        with pytest.raises(AccessError, match="invalid_credentials"):
            await setup.manager.login(f"unknown-{i}", "wrong", "same-peer")
    with pytest.raises(AccessError, match="try_later"):
        await setup.manager.login("another-unknown", "wrong", "same-peer")


async def test_rate_limit_cannot_be_bypassed_by_changing_peers(authorized):
    for i in range(4):
        with pytest.raises(AccessError, match="invalid_credentials"):
            await authorized.manager.login(authorized.link_id, "wrong", f"peer-{i}")
    with pytest.raises(AccessError, match="try_later"):
        await authorized.manager.login(authorized.link_id, "wrong", "another-peer")


async def test_concurrent_and_replayed_actions_only_dispatch_once(authorized):
    started, release = asyncio.Event(), asyncio.Event()

    async def dispatch(entity, action):
        authorized.calls.append((entity, action))
        started.set()
        await release.wait()

    authorized.manager.dispatch = dispatch
    pending = asyncio.create_task(
        authorized.manager.action(
            authorized.session, authorized.action_id, "request-concurrent-1"
        )
    )
    await started.wait()
    with pytest.raises(AccessError, match="try_later"):
        await authorized.manager.action(
            authorized.session, authorized.action_id, "request-concurrent-2"
        )
    release.set()
    await pending
    authorized.clock += 5
    with pytest.raises(AccessError, match="duplicate_request"):
        await authorized.manager.action(
            authorized.session, authorized.action_id, "request-concurrent-1"
        )
    assert len(authorized.calls) == 1


async def test_pause_during_inflight_call_does_not_queue_another(authorized):
    started, release = asyncio.Event(), asyncio.Event()

    async def dispatch(entity, action):
        started.set()
        await release.wait()

    authorized.manager.dispatch = dispatch
    pending = asyncio.create_task(
        authorized.manager.action(
            authorized.session, authorized.action_id, "request-inflight-001"
        )
    )
    await started.wait()
    await authorized.manager.set_enabled(False)
    with pytest.raises(AccessError):
        await authorized.manager.action(
            authorized.session, authorized.action_id, "request-afterpause-1"
        )
    release.set()
    await pending


async def test_cancelled_action_is_recorded_and_not_replayed(authorized):
    started = asyncio.Event()

    async def dispatch(entity, action):
        authorized.calls.append((entity, action))
        started.set()
        await asyncio.Event().wait()

    authorized.manager.dispatch = dispatch
    pending = asyncio.create_task(
        authorized.manager.action(
            authorized.session, authorized.action_id, "request-cancelled-001"
        )
    )
    await started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert authorized.manager.idle.is_set()
    assert authorized.manager.audit[-1]["event"] == "unconfirmed"
    authorized.clock += 10
    with pytest.raises(AccessError, match="duplicate_request"):
        await authorized.manager.action(
            authorized.session, authorized.action_id, "request-cancelled-001"
        )
    assert len(authorized.calls) == 1


async def test_storage_failure_closes_access(authorized, link_data):
    authorized.store.fail = True
    with pytest.raises(AccessError, match="storage_failed"):
        await authorized.manager.save_link(link_data, link_id=authorized.link_id)
    with pytest.raises(AccessError):
        authorized.manager.status(authorized.session)
    assert not authorized.manager.enabled


async def test_restart_preserves_policy_but_not_sessions(authorized):
    m = Manager(
        authorized.store,
        authorized.manager.dispatch,
        lambda _: True,
        key_store=authorized.key_store,
        now=lambda: authorized.now,
    )
    await m.load()
    assert m.admin_state() == authorized.manager.admin_state()
    with pytest.raises(AccessError, match="sign_in"):
        m.status(authorized.session)
    session = await m.login(authorized.link_id, "synthetic-password-one", "peer")
    assert m.status(session)


async def test_expired_session_cannot_be_extended_by_extending_link(
    authorized, link_data
):
    link_data["expires_at"] = (authorized.now + timedelta(days=2)).isoformat()
    await authorized.manager.save_link(link_data, link_id=authorized.link_id)
    authorized.now += timedelta(hours=12)
    with pytest.raises(AccessError, match="sign_in"):
        authorized.manager.status(authorized.session)


@pytest.mark.parametrize(
    "change",
    [
        {"expires_at": None},
        {"starts_at": "2026-10-31T11:00:00"},
        {"expires_at": "2026-10-31T10:00:00+00:00"},
        {"grants": []},
        {"grants": [{"entity_id": "lock.all", "action": "turn_on", "label": "Bad"}]},
        {
            "grants": [
                {"entity_id": "script.anything", "action": "turn_on", "label": "Bad"}
            ]
        },
        {
            "grants": [
                {"entity_id": "lock.all", "action": "open", "label": "Bad", "data": {}}
            ]
        },
    ],
)
def test_rejects_unbounded_or_arbitrary_grants(link_data, change):
    with pytest.raises(AccessError):
        validate_link(copy.deepcopy(link_data) | change)


async def test_password_reveal_survives_restart_and_never_leaks_in_lists(authorized):
    m = authorized.manager
    encrypted = authorized.store.data["links"][authorized.link_id]["password_encrypted"]
    assert "synthetic-password-one" not in encrypted
    assert "synthetic-password-one" not in json.dumps(authorized.store.data)
    assert authorized.key_store.data["key"] not in json.dumps(authorized.store.data)
    for _ in range(2):
        assert await m.reveal_password(authorized.link_id) == {
            "password": "synthetic-password-one"
        }
    restarted = Manager(
        authorized.store,
        m.dispatch,
        m.available,
        key_store=authorized.key_store,
        now=m.now,
    )
    await restarted.load()
    assert await restarted.reveal_password(authorized.link_id) == {
        "password": "synthetic-password-one"
    }
    for public in (restarted.admin_state(), m.status(authorized.session)):
        assert "synthetic-password-one" not in json.dumps(public)
        assert encrypted not in json.dumps(public)
        assert "password_hash" not in json.dumps(public)
    assert restarted.admin_state()["links"][0]["password_available"] is True


async def test_password_reset_replaces_recoverable_copy(authorized, link_data):
    m = authorized.manager
    await m.save_link(
        link_data, link_id=authorized.link_id, password="synthetic-password-two"
    )
    assert await m.reveal_password(authorized.link_id) == {
        "password": "synthetic-password-two"
    }
    await m.set_enabled(False)
    assert await m.reveal_password(authorized.link_id) == {
        "password": "synthetic-password-two"
    }
    await m.delete_link(authorized.link_id)
    with pytest.raises(AccessError, match="not_found"):
        await m.reveal_password(authorized.link_id)
    assert "password_encrypted" not in json.dumps(authorized.store.data)


async def test_encrypted_password_cannot_be_tampered_or_swapped(authorized, link_data):
    m = authorized.manager
    other = await m.save_link(link_data, password="synthetic-password-two")
    m.links[authorized.link_id]["password_encrypted"] = m.links[other["id"]][
        "password_encrypted"
    ]
    with pytest.raises(AccessError, match="password_unavailable"):
        await m.reveal_password(authorized.link_id)
    m.links[authorized.link_id]["password_encrypted"] = "tampered"
    with pytest.raises(AccessError, match="password_unavailable"):
        await m.reveal_password(authorized.link_id)


async def test_missing_encryption_key_cannot_silently_replace_existing_key(authorized):
    authorized.key_store.data = None
    with pytest.raises(AccessError, match="password_key_missing"):
        await authorized.manager.load()
    assert authorized.key_store.data is None


async def test_remembered_session_survives_restart_without_persisting_token(authorized):
    m = authorized.manager
    token = await m.login(
        authorized.link_id, "synthetic-password-one", "remembered-peer", remember=True
    )
    assert token not in json.dumps(authorized.store.data)
    assert "synthetic-password-one" not in json.dumps(authorized.store.data)
    assert len(authorized.store.data["sessions"]) == 1
    restarted = Manager(
        authorized.store,
        m.dispatch,
        m.available,
        key_store=authorized.key_store,
        now=m.now,
    )
    await restarted.load()
    assert restarted.status(token)["name"] == "Synthetic guest"
    with pytest.raises(AccessError, match="sign_in"):
        restarted.status(authorized.session)
    await restarted.logout(token)
    await restarted.load()
    with pytest.raises(AccessError, match="sign_in"):
        restarted.status(token)


@pytest.mark.parametrize("revoke", ["password", "delete"])
async def test_remembered_sessions_stay_revoked_after_restart(
    authorized, link_data, revoke
):
    m = authorized.manager
    token = await m.login(
        authorized.link_id, "synthetic-password-one", "remembered-peer", remember=True
    )
    if revoke == "password":
        await m.save_link(
            link_data, link_id=authorized.link_id, password="synthetic-password-two"
        )
    else:
        await m.delete_link(authorized.link_id)
    await m.load()
    with pytest.raises(AccessError, match="sign_in"):
        m.status(token)


async def test_remembered_session_renews_but_current_scope_and_time_always_apply(
    authorized, link_data
):
    m = authorized.manager
    link_data["expires_at"] = (authorized.now + timedelta(days=400)).isoformat()
    await m.save_link(link_data, link_id=authorized.link_id)
    token = await m.login(
        authorized.link_id, "synthetic-password-one", "remembered-peer", remember=True
    )
    authorized.now += timedelta(days=364, minutes=1)
    assert await m.refresh_session(token, authorized.link_id)
    await m.load()
    authorized.now += timedelta(days=20)
    assert m.status(token)
    link_data["grants"].pop(0)
    await m.save_link(link_data, link_id=authorized.link_id)
    assert len(m.status(token)["actions"]) == 1
    link_data["expires_at"] = authorized.now.isoformat()
    await m.save_link(link_data, link_id=authorized.link_id)
    with pytest.raises(AccessError, match="outside_window"):
        m.status(token)
    with pytest.raises(AccessError):
        await m.action(token, authorized.action_id, "expired-persistent-01")
    assert authorized.calls == []


@pytest.mark.parametrize("global_pause", [False, True])
async def test_paused_browser_is_remembered_but_cannot_act(
    authorized, link_data, global_pause
):
    m = authorized.manager
    token = await m.login(
        authorized.link_id, "synthetic-password-one", "remembered-peer", remember=True
    )
    if global_pause:
        await m.set_enabled(False)
    else:
        await m.save_link(link_data | {"enabled": False}, link_id=authorized.link_id)
    await m.load()
    with pytest.raises(AccessError, match="access_paused"):
        await m.action(token, authorized.action_id, "paused-persistent-001")
    assert authorized.calls == []
    if global_pause:
        await m.set_enabled(True)
    else:
        await m.save_link(link_data, link_id=authorized.link_id)
    assert m.status(token)


async def test_save_waiting_for_hash_cannot_overwrite_reloaded_policy(
    authorized, link_data
):
    old = authorized.manager
    await old.hash_slots.acquire()
    await old.hash_slots.acquire()
    pending = asyncio.create_task(
        old.save_link(
            link_data, link_id=authorized.link_id, password="synthetic-password-two"
        )
    )
    await asyncio.sleep(0)
    await old.close()
    replacement = Manager(
        authorized.store,
        old.dispatch,
        old.available,
        key_store=authorized.key_store,
        now=old.now,
    )
    await replacement.load()
    await replacement.set_enabled(False)
    old.hash_slots.release()
    old.hash_slots.release()
    with pytest.raises(AccessError, match="unavailable"):
        await pending
    await replacement.load()
    assert replacement.enabled is False


async def test_close_waits_for_an_accepted_storage_write(authorized):
    old = authorized.manager
    original_save = authorized.store.async_save
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_save(data):
        started.set()
        await release.wait()
        await original_save(data)

    authorized.store.async_save = slow_save
    pending = asyncio.create_task(old.set_enabled(False))
    await started.wait()
    closing = asyncio.create_task(old.close())
    await asyncio.sleep(0)
    assert not closing.done()
    release.set()
    await pending
    await closing
    assert authorized.store.data["enabled"] is False
    with pytest.raises(AccessError, match="unavailable"):
        await old.set_enabled(True)


async def test_pause_does_not_restore_stale_policy_and_edits_conflict(
    authorized, link_data
):
    m = authorized.manager
    stale = copy.deepcopy(link_data)
    version = m.admin_state()["links"][0]["version"]
    shortened = copy.deepcopy(link_data)
    shortened["grants"].pop()
    shortened["expires_at"] = "2026-10-31T13:00:00+00:00"
    await m.save_link(shortened, link_id=authorized.link_id, expected_version=version)
    await m.set_link_enabled(authorized.link_id, False)
    await m.set_link_enabled(authorized.link_id, True)
    record = m.links[authorized.link_id]
    assert len(record["grants"]) == 1
    assert record["expires_at"] == shortened["expires_at"]
    with pytest.raises(AccessError, match="conflict"):
        await m.save_link(stale, link_id=authorized.link_id, expected_version=version)
    assert len(m.links[authorized.link_id]["grants"]) == 1


async def test_rejected_peer_cannot_exhaust_other_guests_login_budget(authorized):
    m = authorized.manager
    for i in range(60):
        with pytest.raises(AccessError):
            await m.login(f"synthetic-unknown-{i}", "wrong", "attacker-peer")
    token = await m.login(authorized.link_id, "synthetic-password-one", "guest-peer")
    assert m.status(token)
    assert len(m.attempts["global"]) == 12  # Initial sign-in, ten attempts, guest.


async def test_rejected_link_does_not_exhaust_shared_login_budget(authorized):
    m = authorized.manager
    for i in range(60):
        with pytest.raises(AccessError):
            await m.login("synthetic-unknown", "wrong", f"attacker-{i}")
    token = await m.login(authorized.link_id, "synthetic-password-one", "guest-peer")
    assert m.status(token)
    assert len(m.attempts["global"]) == 7


@pytest.mark.parametrize(
    "domain,action", [("light", "set_brightness"), ("cover", "set_cover_position")]
)
@pytest.mark.parametrize("value", [None, -1, 101, 20.5, True, "50", {}, []])
async def test_slider_values_must_be_bounded_integers(
    setup, link_data, domain, action, value
):
    m = setup.manager
    link_data["grants"] = [
        {
            "entity_id": f"{domain}.synthetic",
            "action": action,
            "label": "Synthetic control",
        }
    ]
    result = await m.save_link(link_data, password="synthetic-password-one")
    await m.set_enabled(True)
    token = await m.login(result["id"], "synthetic-password-one", "peer")
    action_id = m.status(token)["actions"][0]["id"]
    with pytest.raises(AccessError, match="invalid_value"):
        await m.action(token, action_id, "synthetic-slider-request", value)
    assert setup.calls == []


async def test_door_actions_reject_slider_values(authorized):
    with pytest.raises(AccessError, match="invalid_request"):
        await authorized.manager.action(
            authorized.session, authorized.action_id, "synthetic-door-value", 50
        )
    assert authorized.calls == []
