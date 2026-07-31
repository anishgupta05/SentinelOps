from sentinelops.connectors.base import SourceConnector
from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle, SourceEvidence
from sentinelops.contracts.root_cause import RootCauseAnalysis
from sentinelops.reasoning.pipeshift import TriageModel


def gather_evidence(
    candidate: ComplaintCandidate, connectors: list[SourceConnector]
) -> EvidenceBundle:
    """Pull related events from every connector. A disabled connector contributes
    an empty, `available=False` entry rather than being omitted, so the trace
    shows which sources were consulted and which were unreachable."""
    sources = [
        SourceEvidence(
            source=connector.source,
            available=connector.enabled,
            events=connector.fetch_events(event_ids=candidate.source_event_ids),
        )
        for connector in connectors
    ]
    return EvidenceBundle(complaint_id=candidate.id, sources=sources)


def analyze(
    candidate: ComplaintCandidate, evidence: EvidenceBundle, model: TriageModel
) -> RootCauseAnalysis:
    return model.assess(candidate, evidence)
