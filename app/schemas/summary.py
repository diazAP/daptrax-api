from datetime import date
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID

class SummaryTotals(BaseModel):
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal
    transaction_count: int


class DailySummaryResponse(BaseModel):
    date: date
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal
    transaction_count: int


class PeriodSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal
    transaction_count: int


class CategoryAmountItem(BaseModel):
    category_id: str
    category_name: str
    amount: Decimal


class AccountAmountItem(BaseModel):
    account_id: str
    account_name: str
    amount: Decimal


class DailySeriesItem(BaseModel):
    date: date
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal


class MonthlySeriesItem(BaseModel):
    month: int
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal


class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal
    transaction_count: int
    top_categories: list[CategoryAmountItem]
    top_accounts: list[AccountAmountItem]
    daily_series: list[DailySeriesItem]


class YearlySummaryResponse(BaseModel):
    year: int
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal
    transaction_count: int
    monthly_series: list[MonthlySeriesItem]


class CalendarDayItem(BaseModel):
    date: date
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal


class CalendarSummaryResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDayItem]


class ChartSeriesItem(BaseModel):
    label: str
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal


class ChartSummaryResponse(BaseModel):
    range_type: str
    series: list[ChartSeriesItem]

class AccountBalanceItem(BaseModel):
    account_id: UUID
    account_name: str
    initial_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    total_transfer_in: Decimal
    total_transfer_out: Decimal
    current_balance: Decimal
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int


class AccountBalanceSummaryResponse(BaseModel):
    as_of_date: date
    total_current_balance: Decimal
    accounts: list[AccountBalanceItem]


class AccountBalancePeriodItem(BaseModel):
    account_id: UUID
    account_name: str
    opening_balance: Decimal
    income_total: Decimal
    expense_total: Decimal
    transfer_in_total: Decimal
    transfer_out_total: Decimal
    net_change: Decimal
    closing_balance: Decimal
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int


class AccountBalancePeriodResponse(BaseModel):
    start_date: date
    end_date: date
    total_opening_balance: Decimal
    total_closing_balance: Decimal
    accounts: list[AccountBalancePeriodItem]