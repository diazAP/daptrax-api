from datetime import date
from decimal import Decimal
from pydantic import BaseModel


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