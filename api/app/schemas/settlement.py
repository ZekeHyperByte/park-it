"""Settlement schemas."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SettlementListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    batch_date: date
    batch_number: int
    total_transactions: int
    total_amount: int
    status: str
    bank_response_code: str | None
    created_at: datetime


class SettlementDetailResponse(SettlementListItem):
    file_path: str | None
    bank_response_file: str | None
    bank_response_at: datetime | None
    bank_response_message: str | None
    file_content_hash: str | None


class SettlementTriggerResponse(BaseModel):
    status: str
    files_generated: int
    total_transactions: int
