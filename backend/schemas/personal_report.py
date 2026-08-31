"""RF-30: feedback sul report di analisi personale."""

from typing import Optional

from pydantic import BaseModel, Field


class PersonalReportFeedbackIn(BaseModel):
    valutazione_stelle: int = Field(ge=1, le=5)
    commento_libero: Optional[str] = None
