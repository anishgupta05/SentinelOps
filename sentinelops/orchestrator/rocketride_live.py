"""Real RocketRide-backed publishing of a finished pipeline result, for
`pip install rocketride`.

Confirmed against the live API (wss://api.rocketride.ai) rather than guessed:
a minimal `.pipe` pipeline (webhook source -> response node) is started on
RocketRide's real hosted engine, the finished PipelineResult is sent through
it as JSON, and the engine's own TASK_STATUS - including real resource and
billing metrics - is read back.

This does NOT run SentinelOps' triage/root-cause/fix-proposal/notify
reasoning on RocketRide. Their `tool_python` node runs in a RestrictedPython
sandbox with no filesystem or local-package access, so this repo's own code
can't execute there - a full "port the pipeline into RocketRide" integration
isn't feasible without rewriting the four nodes as native RocketRide
components. What's real here is the "production hosting and observability"
half of RocketRide's role: the finished result is genuinely published to and
tracked by RocketRide's engine, not the reasoning that produced it.
"""

import asyncio
import json
import os

_ECHO_PIPELINE = {
    "source": "in",
    "components": [
        {"id": "in", "provider": "webhook", "config": {}},
        {
            "id": "out",
            "provider": "response",
            "config": {"laneName": "text"},
            "input": [{"lane": "text", "from": "in"}],
        },
    ],
}


async def _publish(uri: str, auth: str, payload: dict) -> dict:
    from rocketride import RocketRideClient

    async with RocketRideClient(uri=uri, auth=auth) as client:
        result = await client.use(pipeline=_ECHO_PIPELINE, pipelineTraceLevel="summary")
        token = result["token"]
        try:
            await client.send(
                token,
                json.dumps(payload),
                objinfo={"name": "sentinelops-result.json"},
                mimetype="application/json",
            )
            return await client.get_task_status(token)
        finally:
            await client.terminate(token)


def publish_result(payload: dict, *, uri: str | None = None, auth: str | None = None) -> dict:
    """Send a finished PipelineResult summary through a real RocketRide-hosted
    pipeline and return the engine's live task status."""
    try:
        import rocketride  # noqa: F401
    except ImportError as exc:
        raise ImportError("publish_result requires the real SDK: pip install rocketride") from exc

    uri = uri or os.environ.get("ROCKETRIDE_URI", "https://api.rocketride.ai")
    auth = auth or os.environ.get("ROCKETRIDE_APIKEY") or os.environ.get("ROCKETRIDE_AUTH")
    if not auth:
        raise RuntimeError(
            "publish_result needs a token: set ROCKETRIDE_APIKEY or pass auth=..."
        )
    return asyncio.run(_publish(uri, auth, payload))
