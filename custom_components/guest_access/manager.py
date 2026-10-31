"""Guest-link policy, password verification and sessions, independent of HA.

Link identifiers are random and appear only in URL fragments. They are not
passwords. Scrypt verifies passwords; a separately keyed encrypted copy permits
explicit administrator retrieval. Session credentials are separate random
tokens. Remembered token hashes are persisted; they never become HA access tokens.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import OrderedDict, deque
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken

from .const import ALLOWED_ACTIONS


class AccessError(Exception):
    """A bounded error code safe to expose to a guest."""

    def __init__(self, code, status=403):
        super().__init__(code)
        self.code, self.status = code, status


def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=67108864
    )
    return f"{salt.hex()}:{digest.hex()}"


def password_matches(password, stored):
    salt, _ = stored.split(":")
    return hmac.compare_digest(password_hash(password, bytes.fromhex(salt)), stored)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except ValueError, TypeError:
        raise AccessError("invalid_time", 400) from None


def validate_link(data):
    """Require a finite interval and explicit entity/action pairs."""
    if not isinstance(data, dict) or set(data) != {
        "name",
        "enabled",
        "starts_at",
        "expires_at",
        "grants",
    }:
        raise AccessError("invalid_link", 400)
    if not isinstance(data["name"], str) or not 1 <= len(data["name"].strip()) <= 80:
        raise AccessError("invalid_name", 400)
    if not isinstance(data["enabled"], bool):
        raise AccessError("invalid_link", 400)
    start, end = timestamp(data["starts_at"]), timestamp(data["expires_at"])
    if end <= start:
        raise AccessError("invalid_time", 400)
    if not isinstance(data["grants"], list) or not 1 <= len(data["grants"]) <= 32:
        raise AccessError("invalid_grants", 400)
    grants, seen = [], set()
    for grant in data["grants"]:
        if not isinstance(grant, dict) or set(grant) != {
            "entity_id",
            "action",
            "label",
        }:
            raise AccessError("invalid_grants", 400)
        entity, action, label = grant["entity_id"], grant["action"], grant["label"]
        if not isinstance(entity, str) or not re.fullmatch(
            r"[a-z_]+\.[a-z0-9_]+", entity
        ):
            raise AccessError("invalid_entity", 400)
        domain = entity.split(".", 1)[0]
        if action not in ALLOWED_ACTIONS.get(domain, ()):
            raise AccessError("invalid_action", 400)
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80:
            raise AccessError("invalid_label", 400)
        key = hashlib.sha256(f"{entity}:{action}".encode()).hexdigest()[:24]
        if key in seen:
            raise AccessError("duplicate_action", 400)
        seen.add(key)
        grants.append({**grant, "label": label.strip(), "id": key})
    return {
        "name": data["name"].strip(),
        "enabled": data["enabled"],
        "starts_at": start.isoformat(),
        "expires_at": end.isoformat(),
        "grants": grants,
    }


class Manager:
    """All public operations apply current policy, never a session's old grants."""

    def __init__(
        self, store, dispatch, available, *, key_store, now=None, monotonic=None
    ):
        self.store, self.dispatch, self.available = store, dispatch, available
        self.key_store = key_store
        self.cipher = None
        self.now = now or (lambda: datetime.now(UTC))
        self.monotonic = monotonic or time.monotonic
        self.links = {}
        self.enabled = False
        self.audit = []
        self.sessions = {}
        self.lock = asyncio.Lock()
        self.hash_slots = asyncio.Semaphore(2)
        self.attempts = OrderedDict()
        self.recent = OrderedDict()
        self.busy = set()
        self.idle = asyncio.Event()
        self.idle.set()
        self.last_action = {}
        self.closed = False
        self.dummy_hash = ""

    async def load(self):
        self.dummy_hash = await asyncio.to_thread(
            password_hash, secrets.token_urlsafe(32)
        )
        data = await self.store.async_load() or {}
        self.links = data.get("links", {})
        self.enabled = data.get("enabled", False) is True
        self.audit = data.get("audit", [])[-100:]
        key_data = await self.key_store.async_load()
        if key_data is None:
            if any(r.get("password_encrypted") for r in self.links.values()):
                raise AccessError("password_key_missing", 503)
            key_data = {"key": Fernet.generate_key().decode()}
            await self.key_store.async_save(key_data)
        self.cipher = Fernet(key_data["key"].encode())
        # Fail closed on invalid stored records rather than silently broadening them.
        for record in self.links.values():
            validate_link(
                {
                    k: (
                        [{g: v for g, v in item.items() if g != "id"} for item in value]
                        if k == "grants"
                        else value
                    )
                    for k, value in record.items()
                    if k in {"name", "enabled", "starts_at", "expires_at", "grants"}
                }
            )
        self.sessions = {}
        for digest, session in data.get("sessions", {}).items():
            record = self.links.get(session.get("link"))
            if (
                re.fullmatch(r"[0-9a-f]{64}", digest)
                and record
                and session.get("revision") == record["revision"]
                and timestamp(session["until"]) > self.now()
            ):
                self.sessions[bytes.fromhex(digest)] = {
                    **session,
                    "until": timestamp(session["until"]),
                    "persistent": True,
                }

    async def _save(self):
        try:
            await self.store.async_save(
                {
                    "links": copy.deepcopy(self.links),
                    "enabled": self.enabled,
                    "audit": copy.deepcopy(self.audit[-100:]),
                    "sessions": {
                        digest.hex(): {
                            "link": session["link"],
                            "revision": session["revision"],
                            "until": session["until"].isoformat(),
                        }
                        for digest, session in self.sessions.items()
                        if session.get("persistent") and session["until"] > self.now()
                    },
                }
            )
        except Exception:
            self.enabled = False
            self.sessions.clear()
            raise AccessError("storage_failed", 503) from None

    def _event(self, event, record=None, **details):
        self.audit.append(
            {
                "time": self.now().isoformat(),
                "event": event,
                "name": record["name"] if record else "All links",
                **details,
            }
        )
        self.audit = self.audit[-100:]

    def admin_state(self):
        return {
            "enabled": self.enabled,
            "links": [
                {
                    k: copy.deepcopy(v)
                    for k, v in r.items()
                    if k not in {"password_hash", "password_encrypted", "revision"}
                }
                | {"id": key, "password_available": bool(r.get("password_encrypted"))}
                for key, r in self.links.items()
            ],
            "audit": copy.deepcopy(self.audit[-100:]),
        }

    def _ensure_open(self):
        if self.closed:
            raise AccessError("unavailable", 503)

    async def close(self):
        """Reject queued mutations and drain accepted writes before replacement."""
        self.closed = True
        await self.idle.wait()
        async with self.lock:
            self.sessions.clear()

    async def set_enabled(self, enabled):
        if not isinstance(enabled, bool):
            raise AccessError("invalid_link", 400)
        async with self.lock:
            self._ensure_open()
            self.enabled = enabled
            if not enabled:
                self.sessions = {
                    key: session
                    for key, session in self.sessions.items()
                    if session.get("persistent")
                }
            self._event("enabled" if enabled else "paused")
            await self._save()

    async def save_link(self, data, *, link_id=None, password=None):
        cleaned = validate_link(data)
        generated = None
        if link_id is None and password is None:
            password = generated = secrets.token_urlsafe(18)
        hashed = None
        if password is not None:
            if not isinstance(password, str) or not 12 <= len(password) <= 128:
                raise AccessError("password_length", 400)
            async with self.hash_slots:
                hashed = await asyncio.to_thread(password_hash, password)
        async with self.lock:
            self._ensure_open()
            if link_id is None:
                if len(self.links) >= 100:
                    raise AccessError("too_many_links", 400)
                link_id = secrets.token_urlsafe(32)
                previous = {"revision": 0}
            else:
                if link_id not in self.links:
                    raise AccessError("not_found", 404)
                previous = self.links[link_id]
            record = self.links[link_id] = {
                **cleaned,
                "password_hash": hashed or previous["password_hash"],
                "password_encrypted": (
                    self._encrypt_password(link_id, password)
                    if hashed
                    else previous.get("password_encrypted")
                ),
                "revision": previous["revision"] + (1 if hashed else 0),
            }
            if hashed or not cleaned["enabled"]:
                self.sessions = {
                    key: session
                    for key, session in self.sessions.items()
                    if session["link"] != link_id
                    or (not hashed and session.get("persistent"))
                }
            self._event("saved", record)
            await self._save()
        return {"id": link_id, "generated_password": generated}

    def _encrypt_password(self, link_id, password):
        return self.cipher.encrypt(
            json.dumps({"link": link_id, "password": password}).encode()
        ).decode()

    async def reveal_password(self, link_id):
        """Called only by the authenticated admin endpoint, never guest endpoints."""
        async with self.lock:
            self._ensure_open()
            record = self.links.get(link_id)
            if record is None:
                raise AccessError("not_found", 404)
            if not record.get("password_encrypted"):
                raise AccessError("password_not_retained", 409)
            try:
                value = json.loads(
                    self.cipher.decrypt(record["password_encrypted"].encode())
                )
                if value["link"] != link_id or not isinstance(value["password"], str):
                    raise ValueError
            except InvalidToken, ValueError, KeyError, TypeError, AttributeError:
                raise AccessError("password_unavailable", 503) from None
            self._event("password_viewed", record)
            await self._save()
            return {"password": value["password"]}

    async def delete_link(self, link_id):
        async with self.lock:
            self._ensure_open()
            record = self.links.pop(link_id, None)
            if record is None:
                raise AccessError("not_found", 404)
            self.sessions = {
                key: session
                for key, session in self.sessions.items()
                if session["link"] != link_id
            }
            self.last_action.pop(link_id, None)
            self._event("deleted", record)
            await self._save()

    def _limit(self, key, limit):
        now = self.monotonic()
        while self.attempts and next(iter(self.attempts.values()))[-1] <= now - 60:
            self.attempts.popitem(last=False)
        bucket = self.attempts.setdefault(key, deque())
        self.attempts.move_to_end(key)
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            raise AccessError("try_later", 429)
        bucket.append(now)
        while len(self.attempts) > 1024:
            self.attempts.popitem(last=False)

    def _active(self, record):
        if self.closed or not self.enabled or not record["enabled"]:
            raise AccessError("access_paused")
        now = self.now()
        if not timestamp(record["starts_at"]) <= now < timestamp(record["expires_at"]):
            raise AccessError("outside_window")

    async def login(self, link_id, password, peer, *, remember=False):
        if not isinstance(remember, bool):
            raise AccessError("invalid_request", 400)
        if not isinstance(link_id, str) or len(link_id) > 64:
            raise AccessError("invalid_credentials", 401)
        if not isinstance(password, str) or len(password) > 128:
            raise AccessError("invalid_credentials", 401)
        # Count all attempts before expensive hashing, including unknown link IDs.
        self._limit("global", 60)
        self._limit(("peer", peer), 10)
        self._limit(("link", link_id), 5)
        record = self.links.get(link_id)
        snapshot = copy.deepcopy(record)
        async with self.hash_slots:
            valid = await asyncio.to_thread(
                password_matches,
                password,
                record["password_hash"] if record else self.dummy_hash,
            )
        async with self.lock:
            current = self.links.get(link_id)
            if not valid or current is None or current != snapshot:
                raise AccessError("invalid_credentials", 401)
            self._active(current)
            self.sessions = {
                k: v for k, v in self.sessions.items() if v["until"] > self.now()
            }
            if len(self.sessions) >= 256:
                raise AccessError("try_later", 429)
            token = secrets.token_urlsafe(32)
            self.sessions[hashlib.sha256(token.encode()).digest()] = {
                "link": link_id,
                "revision": current["revision"],
                "until": self.now()
                + (timedelta(days=365) if remember else timedelta(hours=12)),
                "persistent": remember,
            }
            if remember:
                await self._save()
            return token

    async def refresh_session(self, token, link_id):
        """Bind the cookie to its link; renew remembered browsers once per day."""
        async with self.lock:
            actual_link, _ = self._session(token)
            if actual_link != link_id:
                raise AccessError("sign_in", 401)
            session = self.sessions[hashlib.sha256(token.encode()).digest()]
            if session.get("persistent") and session["until"] < self.now() + timedelta(
                days=364
            ):
                session["until"] = self.now() + timedelta(days=365)
                await self._save()
            return session.get("persistent", False)

    def _session(self, token):
        if not isinstance(token, str) or len(token) > 64:
            raise AccessError("sign_in", 401)
        session = self.sessions.get(hashlib.sha256(token.encode()).digest())
        record = self.links.get(session["link"]) if session else None
        if (
            not record
            or session["until"] <= self.now()
            or session["revision"] != record["revision"]
        ):
            raise AccessError("sign_in", 401)
        self._active(record)
        return session["link"], record

    def status(self, token):
        _, record = self._session(token)
        return {
            "name": record["name"],
            "expires_at": record["expires_at"],
            "actions": [
                {
                    "id": g["id"],
                    "label": g["label"],
                    "kind": g["entity_id"].split(".", 1)[0] + "." + g["action"],
                    "available": self.available(g["entity_id"]),
                }
                for g in record["grants"]
            ],
        }

    async def logout(self, token):
        async with self.lock:
            self._ensure_open()
            removed = self.sessions.pop(hashlib.sha256(token.encode()).digest(), None)
            if removed and removed.get("persistent"):
                await self._save()

    async def action(self, token, action_id, request_id):
        if not isinstance(request_id, str) or not re.fullmatch(
            r"[a-zA-Z0-9-]{16,64}", request_id
        ):
            raise AccessError("invalid_request", 400)
        async with self.lock:
            link_id, record = self._session(token)
            grant = next((g for g in record["grants"] if g["id"] == action_id), None)
            if grant is None:
                raise AccessError("not_allowed")
            if not self.available(grant["entity_id"]):
                raise AccessError("unavailable", 503)
            now = self.monotonic()
            while self.recent and next(iter(self.recent.values())) <= now - 600:
                self.recent.popitem(last=False)
            if (link_id, request_id) in self.recent:
                raise AccessError("duplicate_request", 409)
            if link_id in self.busy or self.last_action.get(link_id, -100) > now - 3:
                raise AccessError("try_later", 429)
            self.recent[link_id, request_id] = now
            while len(self.recent) > 2048:
                self.recent.popitem(last=False)
            self.busy.add(link_id)
            self.idle.clear()
            self.last_action[link_id] = now
        # Authorization is complete. Revocation cannot undo an already dispatched action.
        outcome = "requested"
        try:
            async with asyncio.timeout(20):
                await self.dispatch(grant["entity_id"], grant["action"])
        except asyncio.CancelledError:
            outcome = "unconfirmed"
            raise
        except TimeoutError:
            outcome = "unconfirmed"
            raise AccessError("unconfirmed", 503) from None
        except Exception:
            outcome = "failed"
            raise AccessError("action_failed", 503) from None
        finally:
            async with self.lock:
                self.busy.discard(link_id)
                self._event(outcome, record, action=grant["label"])
                try:
                    await self._save()
                finally:
                    if not self.busy:
                        self.idle.set()
