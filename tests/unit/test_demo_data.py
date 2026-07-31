import pytest

from sentinelops.demo_data import INCIDENTS, load_events


def test_all_registered_incidents_load() -> None:
    for incident in INCIDENTS:
        events = load_events(incident)
        assert events, f"{incident} fixture has no events"


def test_unknown_incident_raises() -> None:
    with pytest.raises(ValueError, match="unknown incident"):
        load_events("does-not-exist")
