"""Real HydraDB-backed ContextGraph, for `pip install 'hydradb-sdk>=2,<3'`.

Confirmed against the live API (base URL https://api.hydradb.com, docs at
docs.hydradb.com) rather than guessed: this ingests events as HydraDB
"knowledge" sources via `app_knowledge`, declaring explicit forceful
`relations.ids` between events that share a `_link_key` - the same grouping
`InMemoryHydraGraph` does locally, but now genuinely computed as graph edges
in HydraDB's own backend.

Entity resolution for pipeline logic (`resolve_entities`/`events_for_entity`)
still delegates to an internal `InMemoryHydraGraph`, not HydraDB's emergent
NLP-extracted entity graph from `/context/relations`. That endpoint returns
semantic entities/predicates (people, concepts, relationships it infers from
text), which doesn't map cleanly onto our `NormalizedEntity.source_ids`
contract - our nodes need deterministic, exact-id groupings, not an emergent
graph that can vary run to run. The real relations response is still fetched
and kept on `last_relations` as proof of a live round trip and for
observability, just not used to drive node decisions.
"""

import json
import os
import time

from sentinelops.contracts.entities import NormalizedEntity
from sentinelops.contracts.events import SourceEvent
from sentinelops.graph.hydra import InMemoryHydraGraph, _link_key

_INDEXING_TERMINAL_OK = {"graph_creation", "completed"}
_INDEXING_TERMINAL_FAILED = {"errored", "failed"}


class HydraDBClient:
    """Drop-in replacement for `InMemoryHydraGraph` backed by the real HydraDB API."""

    def __init__(
        self,
        database: str,
        token: str | None = None,
        collection: str = "sentinelops",
        ready_timeout_s: float = 60.0,
        index_timeout_s: float = 60.0,
    ) -> None:
        try:
            from hydra_db import ConflictError, HydraDB
            from hydra_db.core.api_error import ApiError
        except ImportError as exc:
            raise ImportError(
                "HydraDBClient requires the real SDK: pip install 'hydradb-sdk>=2,<3'"
            ) from exc

        token = token or os.environ.get("HYDRA_DB_API_KEY")
        if not token:
            raise RuntimeError(
                "HydraDBClient needs a token: set HYDRA_DB_API_KEY or pass token=..."
            )
        self._client = HydraDB(token=token)
        self._conflict_error = ConflictError
        self._api_error = ApiError
        self.database = database
        self.collection = collection
        self._ready_timeout_s = ready_timeout_s
        self._index_timeout_s = index_timeout_s
        self._local = InMemoryHydraGraph()
        self.last_relations = None

        self._ensure_database()

    def _ensure_database(self) -> None:
        try:
            self._client.databases.create(database=self.database)
        except self._conflict_error:
            pass  # database already exists - fine, we just need it ready

        deadline = time.monotonic() + self._ready_timeout_s
        while time.monotonic() < deadline:
            status = self._client.databases.status(database=self.database).data
            if status.infra.ready_for_ingestion:
                return
            time.sleep(2)
        raise TimeoutError(f"HydraDB database {self.database!r} never became ready for ingestion")

    def ingest(self, events: list[SourceEvent]) -> None:
        self._local.ingest(events)
        if not events:
            return

        groups: dict[str, list[str]] = {}
        for event in events:
            groups.setdefault(_link_key(event), []).append(event.id)

        payload = []
        for event in events:
            item: dict = {
                "id": event.id,
                "title": f"{event.source}:{event.event_type}",
                "type": event.source,
                "content": {"text": event.text},
                "timestamp": event.occurred_at.isoformat(),
                "additional_metadata": {
                    "author": event.author,
                    "event_type": event.event_type,
                    **event.metadata,
                },
            }
            if event.url:
                item["url"] = event.url
            related = [eid for eid in groups[_link_key(event)] if eid != event.id]
            if related:
                item["relations"] = {"ids": related}
            payload.append(item)

        self._ingest_with_retry(payload)
        self._wait_for_indexing([e.id for e in events])

    def _ingest_with_retry(self, payload: list[dict], timeout_s: float = 45.0) -> None:
        """`databases.status().infra.ready_for_ingestion` isn't sufficient proof
        on its own - confirmed live: a database that just reported ready can
        still 404 on ingest with "vectorstore collection has not been
        provisioned yet" for tens of seconds after. Retry the ingest itself
        rather than trust one ready flag flip. The SDK only raises its typed
        `NotFoundError` for a handful of endpoints; `ingest` falls through to
        the generic `ApiError`, so this checks `status_code` directly instead
        of catching a specific exception type."""
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                self._client.context.ingest(
                    type="knowledge",
                    database=self.database,
                    collection=self.collection,
                    app_knowledge=json.dumps(payload),
                )
                return
            except self._api_error as exc:
                if exc.status_code != 404 or time.monotonic() >= deadline:
                    raise
                time.sleep(2)

    def _wait_for_indexing(self, ids: list[str]) -> None:
        deadline = time.monotonic() + self._index_timeout_s
        while time.monotonic() < deadline:
            statuses = self._client.context.status(
                database=self.database, collection=self.collection, ids=ids
            ).data.statuses
            failed = [s for s in statuses if s.indexing_status in _INDEXING_TERMINAL_FAILED]
            if failed:
                raise RuntimeError(f"HydraDB indexing failed: {failed[0].error_message}")
            if all(s.indexing_status in _INDEXING_TERMINAL_OK for s in statuses):
                return
            time.sleep(2)
        raise TimeoutError(f"HydraDB indexing of {ids} did not complete in time")

    def resolve_entities(self) -> list[NormalizedEntity]:
        self.last_relations = self._client.context.relations(
            database=self.database, collection=self.collection, type="knowledge"
        ).data
        return self._local.resolve_entities()

    def events_for_entity(self, entity_id: str) -> list[SourceEvent]:
        return self._local.events_for_entity(entity_id)

    def all_events(self) -> list[SourceEvent]:
        return self._local.all_events()
