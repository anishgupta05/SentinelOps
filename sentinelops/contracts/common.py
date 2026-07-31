from typing import Annotated, Literal

from pydantic import Field

SourceName = Literal["slack", "github", "linear", "gmail"]
Severity = Literal["low", "medium", "high", "critical"]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
