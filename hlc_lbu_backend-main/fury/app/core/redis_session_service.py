"""RedisSessionService — ADK session service backed by Redis.

Persists ADK sessions across Celery workers, preventing session loss when
a task gets re-queued to a different worker (the InMemorySessionService bug).

Key schema:
  fury:session:<app>:<user>:<session_id>  → JSON with state + events
  fury:sessions:<app>:<user>              → Redis Set with session IDs
"""
from __future__ import annotations

import copy
import json
import time
import uuid
import logging
from typing import Any, Optional

from typing_extensions import override

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.adk.sessions.state import State

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 86400 * 7  # 7 days


def _session_key(app_name: str, user_id: str, session_id: str) -> str:
    return f"fury:session:{app_name}:{user_id}:{session_id}"


def _sessions_index_key(app_name: str, user_id: str) -> str:
    return f"fury:sessions:{app_name}:{user_id}"


class RedisSessionService(BaseSessionService):
    """ADK session service that persists sessions in Redis.

    Drop-in replacement for InMemorySessionService. Uses the same
    RedisClient already configured in the app (no extra connection overhead).

    Args:
        redis_url: Redis URL, e.g. ``redis://redis:6379/0``.
        ttl_seconds: TTL for session keys. Default 7 days.
    """

    def __init__(self, redis_url: str, ttl_seconds: int = _DEFAULT_TTL) -> None:
        import redis as redis_lib
        self._redis = redis_lib.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def _serialize(self, session: Session) -> str:
        """Serialise a Session to a JSON string."""
        data = session.model_dump(by_alias=False)
        try:
            data["events"] = [e.model_dump(by_alias=False) for e in session.events]
        except Exception:
            data["events"] = []
        return json.dumps(data, default=str)

    def _deserialize(self, raw: str) -> Session:
        """Deserialise a Session from a JSON string.

        Events are stored but not reconstructed into Event objects to avoid
        complex dependency on internal ADK event deserialization. The runner
        only needs ``state`` across Celery task boundaries.
        """
        data = json.loads(raw)
        events_raw = data.pop("events", [])
        session = Session(**data)
        # Attempt to reconstruct events; silently skip on failure.
        for e in events_raw:
            try:
                session.events.append(Event(**e))
            except Exception:
                pass
        return session

    def _save(self, session: Session) -> None:
        key = _session_key(session.app_name, session.user_id, session.id)
        idx_key = _sessions_index_key(session.app_name, session.user_id)
        pipe = self._redis.pipeline()
        pipe.set(key, self._serialize(session), ex=self._ttl)
        pipe.sadd(idx_key, session.id)
        pipe.expire(idx_key, self._ttl)
        pipe.execute()

    # ------------------------------------------------------------------
    # BaseSessionService interface
    # ------------------------------------------------------------------

    @override
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        session_id = (
            session_id.strip()
            if session_id and session_id.strip()
            else str(uuid.uuid4())
        )
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
            last_update_time=time.time(),
        )
        self._save(session)
        logger.debug(f"[RedisSession] created session={session_id} user={user_id}")
        return copy.deepcopy(session)

    @override
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        key = _session_key(app_name, user_id, session_id)
        raw = self._redis.get(key)
        if raw is None:
            logger.debug(f"[RedisSession] session not found: {session_id}")
            return None

        session = self._deserialize(raw)

        if config:
            if config.num_recent_events:
                session.events = session.events[-config.num_recent_events:]
            if config.after_timestamp:
                session.events = [
                    e for e in session.events
                    if e.timestamp >= config.after_timestamp
                ]

        return session

    @override
    async def list_sessions(
        self, *, app_name: str, user_id: str
    ) -> ListSessionsResponse:
        idx_key = _sessions_index_key(app_name, user_id)
        session_ids = self._redis.smembers(idx_key)
        sessions = []
        for sid in session_ids:
            raw = self._redis.get(_session_key(app_name, user_id, sid))
            if raw:
                s = self._deserialize(raw)
                s.events = []
                sessions.append(s)
        return ListSessionsResponse(sessions=sessions)

    @override
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        key = _session_key(app_name, user_id, session_id)
        idx_key = _sessions_index_key(app_name, user_id)
        self._redis.delete(key)
        self._redis.srem(idx_key, session_id)
        logger.debug(f"[RedisSession] deleted session={session_id}")

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        """Append event in-memory then persist the updated session to Redis."""
        await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp

        if event.actions and event.actions.state_delta:
            for key, value in event.actions.state_delta.items():
                if not key.startswith(State.TEMP_PREFIX):
                    session.state[key] = value

        try:
            self._save(session)
        except Exception as exc:
            logger.warning(f"[RedisSession] Failed to persist session after event: {exc}")

        return event
