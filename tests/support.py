"""Deterministic test fixtures shared by the analytics/verification suites.

All fixtures are plain, hand-written canonical transactions with no dependence on
the synthetic dataset or any file, so the test expectations are exact and stable.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from personal_finance_agent.models import CategoryOrigin, Direction, Period, Transaction

AUG_START = _dt.date(2025, 8, 1)
AUG_END = _dt.date(2025, 8, 31)
SEP_END = _dt.date(2025, 9, 30)

AUGUST = Period(start=AUG_START, end=AUG_END, label="2025-08")
SEPTEMBER = Period(start=_dt.date(2025, 9, 1), end=SEP_END, label="2025-09")


def tx(
    transaction_id: str,
    day: int,
    amount: str,
    direction: str = "expense",
    *,
    month: int = 8,
    year: int = 2025,
    merchant: str | None = "Merchant X",
    category: str | None = "Category Y",
    currency: str = "USD",
    description: str | None = None,
) -> Transaction:
    """Build one canonical transaction with sensible defaults."""
    text = description if description is not None else f"Purchase {transaction_id}"
    return Transaction(
        transaction_id=transaction_id,
        date=_dt.date(year, month, day),
        amount=Decimal(amount),
        direction=Direction(direction),
        currency=currency,
        description=text,
        merchant=merchant,
        category=category,
        category_origin=CategoryOrigin.SOURCE if category is not None else CategoryOrigin.UNRESOLVED,
        original_description=text,
        normalized_description=text.lower(),
        source_reference=f"fixtures.csv:{transaction_id}",
    )


def standard_transactions() -> list[Transaction]:
    """A deterministic fixture covering both months and all directions.

    August expenses:          t1 100.00 + t2 250.00 + t3 50.00  = 400.00
    September expenses:       t6 60.00 + t7 700.00 + t9 20.00  = 780.00
    Non-spending in period:   t4 (income), t5 (refund)
    Boundary records:         t8 on Jul 31, t9 on Sep 30
    """
    return [
        tx("t1", 1, "100.00", merchant="FreshMart", category="Groceries"),
        tx("t2", 15, "250.00", merchant="Metro", category="Housing"),
        tx("t3", 31, "50.00", merchant="Cinema7", category="Entertainment"),
        tx("t4", 20, "500.00", "income", merchant="Acme", category="Salary"),
        tx("t5", 10, "30.00", "refund", merchant="Shop", category="Shopping"),
        tx("t6", 5, "60.00", month=9, merchant="FreshMart", category="Groceries"),
        tx("t7", 25, "700.00", month=9, merchant="OnlineShop", category="Shopping"),
        tx("t8", 31, "10.00", month=7, merchant="OldMerchant", category="Old"),
        tx("t9", 30, "20.00", month=9, merchant="MonthEnd", category="MonthEnd"),
    ]