from pydantic import BaseModel


class NotificationPayload(BaseModel):
    """What the notify node posts back to the original Slack thread."""

    id: str
    complaint_id: str
    channel_ref: str
    ticket_id: str | None = None
    ticket_url: str | None = None
    message: str
    rationale: str
    sent: bool
