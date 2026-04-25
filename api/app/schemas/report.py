"""Report Pydantic schemas."""

from pydantic import BaseModel


class SummaryReport(BaseModel):
    """Parking summary report for a date range."""

    total_transactions: int
    total_revenue: int
    cash_revenue: int
    emoney_revenue: int
    rfid_revenue: int
    total_vehicles: int
    average_fee: float
    active_transactions: int
    completed_transactions: int


class EmoneyReport(BaseModel):
    """E-money report for a date range."""

    total_emoney_transactions: int
    total_deducted: int
    success_count: int
    failed_count: int
    lost_contact_count: int
    average_deduct_amount: float
    unsettled_count: int
    settled_count: int
