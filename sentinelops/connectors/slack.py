from sentinelops.connectors.base import FixtureConnector
from sentinelops.contracts.events import SourceEvent


class SlackConnector(FixtureConnector):
    def __init__(self, events: list[SourceEvent], enabled: bool = True) -> None:
        super().__init__(source="slack", events=events, enabled=enabled)
