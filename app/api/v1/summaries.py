from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.summary import (
    AccountAmountItem,
    CalendarDayItem,
    CalendarSummaryResponse,
    CategoryAmountItem,
    ChartSeriesItem,
    ChartSummaryResponse,
    DailySeriesItem,
    DailySummaryResponse,
    MonthlySeriesItem,
    MonthlySummaryResponse,
    PeriodSummaryResponse,
    YearlySummaryResponse,
)
from app.utils.enums import TRANSACTION_TYPE_EXPENSE, TRANSACTION_TYPE_INCOME

router = APIRouter(prefix="/summaries", tags=["summaries"])


def _validate_year_month(year: int, month: int):
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must be between 1 and 12",
        )
    if year < 2000 or year > 2100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year is out of allowed range",
        )


def _period_bounds_for_month(year: int, month: int) -> tuple[date, date]:
    _validate_year_month(year, month)
    start_date = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    return start_date, end_date


def _period_bounds_for_year(year: int) -> tuple[date, date]:
    if year < 2000 or year > 2100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year is out of allowed range",
        )
    return date(year, 1, 1), date(year, 12, 31)


def _period_bounds_for_week(anchor_date: date) -> tuple[date, date]:
    start_date = anchor_date - timedelta(days=anchor_date.weekday())
    end_date = start_date + timedelta(days=6)
    return start_date, end_date


def _totals_query(user_id: UUID, start_date: date, end_date: date):
    income_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_INCOME, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_EXPENSE, Transaction.amount),
        else_=0,
    )

    return (
        select(
            func.coalesce(func.sum(income_case), 0).label("income_total"),
            func.coalesce(func.sum(expense_case), 0).label("expense_total"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
    )


def _get_totals(db: Session, user_id: UUID, start_date: date, end_date: date):
    row = db.execute(_totals_query(user_id, start_date, end_date)).one()
    income_total = Decimal(row.income_total or 0)
    expense_total = Decimal(row.expense_total or 0)
    transaction_count = int(row.transaction_count or 0)
    net_total = income_total - expense_total
    return income_total, expense_total, net_total, transaction_count


@router.get("/daily", response_model=DailySummaryResponse)
def get_daily_summary(
    date_value: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    income_total, expense_total, net_total, transaction_count = _get_totals(
        db, current_user.id, date_value, date_value
    )

    return DailySummaryResponse(
        date=date_value,
        income_total=income_total,
        expense_total=expense_total,
        net_total=net_total,
        transaction_count=transaction_count,
    )


@router.get("/weekly", response_model=PeriodSummaryResponse)
def get_weekly_summary(
    date_value: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_date, end_date = _period_bounds_for_week(date_value)
    income_total, expense_total, net_total, transaction_count = _get_totals(
        db, current_user.id, start_date, end_date
    )

    return PeriodSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        income_total=income_total,
        expense_total=expense_total,
        net_total=net_total,
        transaction_count=transaction_count,
    )


@router.get("/monthly", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_date, end_date = _period_bounds_for_month(year, month)
    income_total, expense_total, net_total, transaction_count = _get_totals(
        db, current_user.id, start_date, end_date
    )

    category_rows = db.execute(
        select(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("amount"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    ).all()

    account_rows = db.execute(
        select(
            Account.id,
            Account.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("amount"),
        )
        .join(Account, Account.id == Transaction.account_id)
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .group_by(Account.id, Account.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    ).all()

    income_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_INCOME, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_EXPENSE, Transaction.amount),
        else_=0,
    )

    daily_rows = db.execute(
        select(
            Transaction.transaction_date.label("tx_date"),
            func.coalesce(func.sum(income_case), 0).label("income_total"),
            func.coalesce(func.sum(expense_case), 0).label("expense_total"),
        )
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date.asc())
    ).all()

    top_categories = [
        CategoryAmountItem(
            category_id=str(row.id),
            category_name=row.name,
            amount=Decimal(row.amount or 0),
        )
        for row in category_rows
    ]

    top_accounts = [
        AccountAmountItem(
            account_id=str(row.id),
            account_name=row.name,
            amount=Decimal(row.amount or 0),
        )
        for row in account_rows
    ]

    daily_series = [
        DailySeriesItem(
            date=row.tx_date,
            income_total=Decimal(row.income_total or 0),
            expense_total=Decimal(row.expense_total or 0),
            net_total=Decimal(row.income_total or 0) - Decimal(row.expense_total or 0),
        )
        for row in daily_rows
    ]

    return MonthlySummaryResponse(
        year=year,
        month=month,
        income_total=income_total,
        expense_total=expense_total,
        net_total=net_total,
        transaction_count=transaction_count,
        top_categories=top_categories,
        top_accounts=top_accounts,
        daily_series=daily_series,
    )


@router.get("/yearly", response_model=YearlySummaryResponse)
def get_yearly_summary(
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_date, end_date = _period_bounds_for_year(year)
    income_total, expense_total, net_total, transaction_count = _get_totals(
        db, current_user.id, start_date, end_date
    )

    income_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_INCOME, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_EXPENSE, Transaction.amount),
        else_=0,
    )

    rows = db.execute(
        select(
            extract("month", Transaction.transaction_date).label("month_num"),
            func.coalesce(func.sum(income_case), 0).label("income_total"),
            func.coalesce(func.sum(expense_case), 0).label("expense_total"),
        )
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .group_by(extract("month", Transaction.transaction_date))
        .order_by(extract("month", Transaction.transaction_date).asc())
    ).all()

    monthly_series = [
        MonthlySeriesItem(
            month=int(row.month_num),
            income_total=Decimal(row.income_total or 0),
            expense_total=Decimal(row.expense_total or 0),
            net_total=Decimal(row.income_total or 0) - Decimal(row.expense_total or 0),
        )
        for row in rows
    ]

    return YearlySummaryResponse(
        year=year,
        income_total=income_total,
        expense_total=expense_total,
        net_total=net_total,
        transaction_count=transaction_count,
        monthly_series=monthly_series,
    )


@router.get("/calendar", response_model=CalendarSummaryResponse)
def get_calendar_summary(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_date, end_date = _period_bounds_for_month(year, month)

    income_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_INCOME, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_EXPENSE, Transaction.amount),
        else_=0,
    )

    rows = db.execute(
        select(
            Transaction.transaction_date.label("tx_date"),
            func.coalesce(func.sum(income_case), 0).label("income_total"),
            func.coalesce(func.sum(expense_case), 0).label("expense_total"),
        )
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date.asc())
    ).all()

    days = [
        CalendarDayItem(
            date=row.tx_date,
            income_total=Decimal(row.income_total or 0),
            expense_total=Decimal(row.expense_total or 0),
            net_total=Decimal(row.income_total or 0) - Decimal(row.expense_total or 0),
        )
        for row in rows
    ]

    return CalendarSummaryResponse(
        year=year,
        month=month,
        days=days,
    )


@router.get("/chart", response_model=ChartSummaryResponse)
def get_chart_summary(
    range_type: str = Query(..., pattern="^(weekly|monthly|yearly)$"),
    date_value: date | None = Query(default=None, alias="date"),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    income_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_INCOME, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_EXPENSE, Transaction.amount),
        else_=0,
    )

    if range_type == "weekly":
        if not date_value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date is required for weekly chart",
            )
        start_date, end_date = _period_bounds_for_week(date_value)

        rows = db.execute(
            select(
                Transaction.transaction_date.label("label_date"),
                func.coalesce(func.sum(income_case), 0).label("income_total"),
                func.coalesce(func.sum(expense_case), 0).label("expense_total"),
            )
            .where(Transaction.user_id == current_user.id)
            .where(Transaction.transaction_date >= start_date)
            .where(Transaction.transaction_date <= end_date)
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date.asc())
        ).all()

        series = [
            ChartSeriesItem(
                label=row.label_date.isoformat(),
                income_total=Decimal(row.income_total or 0),
                expense_total=Decimal(row.expense_total or 0),
                net_total=Decimal(row.income_total or 0) - Decimal(row.expense_total or 0),
            )
            for row in rows
        ]

        return ChartSummaryResponse(range_type=range_type, series=series)

    if range_type == "monthly":
        if not year or not month:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="year and month are required for monthly chart",
            )
        start_date, end_date = _period_bounds_for_month(year, month)

        rows = db.execute(
            select(
                Transaction.transaction_date.label("label_date"),
                func.coalesce(func.sum(income_case), 0).label("income_total"),
                func.coalesce(func.sum(expense_case), 0).label("expense_total"),
            )
            .where(Transaction.user_id == current_user.id)
            .where(Transaction.transaction_date >= start_date)
            .where(Transaction.transaction_date <= end_date)
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date.asc())
        ).all()

        series = [
            ChartSeriesItem(
                label=row.label_date.isoformat(),
                income_total=Decimal(row.income_total or 0),
                expense_total=Decimal(row.expense_total or 0),
                net_total=Decimal(row.income_total or 0) - Decimal(row.expense_total or 0),
            )
            for row in rows
        ]

        return ChartSummaryResponse(range_type=range_type, series=series)

    if not year:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year is required for yearly chart",
        )

    start_date, end_date = _period_bounds_for_year(year)

    rows = db.execute(
        select(
            extract("month", Transaction.transaction_date).label("month_num"),
            func.coalesce(func.sum(income_case), 0).label("income_total"),
            func.coalesce(func.sum(expense_case), 0).label("expense_total"),
        )
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .group_by(extract("month", Transaction.transaction_date))
        .order_by(extract("month", Transaction.transaction_date).asc())
    ).all()

    series = [
        ChartSeriesItem(
            label=str(int(row.month_num)),
            income_total=Decimal(row.income_total or 0),
            expense_total=Decimal(row.expense_total or 0),
            net_total=Decimal(row.income_total or 0) - Decimal(row.expense_total or 0),
        )
        for row in rows
    ]

    return ChartSummaryResponse(range_type=range_type, series=series)