"""Deterministic synthetic transaction dataset (August-September).

This module generates a small, clearly synthetic dataset covering two complete
months. It contains no real personal financial information. Every value is
produced deterministically with a fixed random seed so regenerating the CSV is
bit-for-bit reproducible.

The generator is used to (re)create ``data/sample/transactions.csv`` from the
repository root::

    PYTHONPATH=src python -c "from personal_finance_agent.synthetic import write_synthetic_transactions_csv; write_synthetic_transactions_csv()"

Variation is designed to support monthly spending summaries, category analysis,
month-to-month comparison, merchant analysis and large-expense identification:
normal everyday transactions (groceries, dining, transport, utilities,
subscriptions, health, entertainment, shopping) plus a few larger/noteworthy
transactions (rent, travel in August, a laptop purchase and a refund in
September) and non-spending records (income, a savings transfer).
"""

from __future__ import annotations

import csv
import datetime as _dt
import random
from decimal import Decimal
from pathlib import Path

__all__ = [
    "MONTHS",
    "SEED",
    "SYNTHETIC_CSV_PATH",
    "YEAR",
    "build_synthetic_transactions",
    "write_synthetic_transactions_csv",
]

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CSV_PATH = PACKAGE_ROOT / "data" / "sample" / "transactions.csv"

YEAR = 2025
MONTHS: tuple[int, ...] = (8, 9)
SEED = 20250801

HEADER: tuple[str, ...] = (
    "transaction_id",
    "date",
    "description",
    "merchant",
    "amount",
    "direction",
    "category",
    "currency",
)


def build_synthetic_transactions(year: int = YEAR) -> list[dict]:
    """Build the deterministic synthetic transaction rows for ``year``."""
    rng = random.Random(SEED)
    records: list[dict] = []
    counter = 0

    def add(
        day: int,
        month: int,
        description: str,
        merchant: str,
        amount: Decimal,
        direction: str,
        category: str,
    ) -> None:
        nonlocal counter
        counter += 1
        date = _dt.date(year, month, day)
        records.append(
            {
                "transaction_id": f"T{date:%Y%m}-{counter:03d}",
                "date": date.isoformat(),
                "description": description,
                "merchant": merchant,
                "amount": f"{amount:.2f}",
                "direction": direction,
                "category": category,
                "currency": "USD",
            }
        )

    def amount_cents(lo: int, hi: int) -> Decimal:
        return Decimal(rng.randint(lo, hi)) / Decimal(100)

    for month in MONTHS:
        _add_recurring(add, month)
        _add_everyday(add, month, amount_cents)
        _add_month_variation(add, month)

    records.sort(key=lambda record: (record["date"], record["transaction_id"]))
    return records


def _add_recurring(add, month: int) -> None:
    add(1, month, "Monthly apartment rent", "Metro Apartments", Decimal("1450.00"), "expense", "Housing")
    add(2, month, "Monthly salary deposit", "Acme Corp", Decimal("5200.00"), "income", "Salary")
    add(3, month, "Electricity bill", "City Power", Decimal("88.50"), "expense", "Utilities")
    add(3, month, "Water and sewer bill", "Water & Sewer", Decimal("41.20"), "expense", "Utilities")
    add(4, month, "Internet service", "Broadband Co", Decimal("64.99"), "expense", "Utilities")
    add(5, month, "Video streaming subscription", "StreamPlus", Decimal("15.99"), "expense", "Subscriptions")
    add(5, month, "Cloud storage subscription", "CloudVault", Decimal("9.99"), "expense", "Subscriptions")
    add(6, month, "Gym membership", "FitLife Gym", Decimal("39.00"), "expense", "Health")


def _add_everyday(add, month: int, amount_cents) -> None:
    for day in (6, 13, 20, 27):
        add(day, month, "Weekly grocery shopping", "FreshMart", amount_cents(4200, 8800), "expense", "Groceries")
    for day in (7, 14, 21):
        add(day, month, "Corner store groceries", "GreenGrocer", amount_cents(1100, 2500), "expense", "Groceries")

    add(8, month, "Coffee and pastry", "Cafe Luna", amount_cents(350, 650), "expense", "Dining")
    add(9, month, "Lunch", "Pizzeria Roma", amount_cents(1200, 2200), "expense", "Dining")
    add(16, month, "Dinner", "Sushi House", amount_cents(3800, 6200), "expense", "Dining")
    add(24, month, "Fast food", "Burger Joint", amount_cents(1200, 1900), "expense", "Dining")

    add(1, month, "Monthly transit pass", "City Transit", Decimal("45.00"), "expense", "Transport")
    for day in (11, 18, 28):
        add(day, month, "Fuel fill-up", "Corner Gas", amount_cents(3900, 5600), "expense", "Transport")
    add(22, month, "Ride share", "RideShare Co", amount_cents(1400, 3200), "expense", "Transport")
    add(29, month, "Parking", "Parking Garage", Decimal("9.00"), "expense", "Transport")

    add(12, month, "Pharmacy", "Wellness Pharmacy", amount_cents(1800, 4500), "expense", "Health")
    add(15, month, "Movie tickets", "Cinema 7", amount_cents(1200, 1600), "expense", "Entertainment")
    add(17, month, "Clothing", "Mall Outlet", amount_cents(3000, 9000), "expense", "Shopping")
    add(23, month, "Books", "Books & Co", amount_cents(1500, 4000), "expense", "Shopping")


def _add_month_variation(add, month: int) -> None:
    if month == 8:
        add(18, month, "Round-trip flight", "Skyline Air", Decimal("425.00"), "expense", "Travel")
        add(19, month, "Hotel stay", "Harbor Grand Hotel", Decimal("382.40"), "expense", "Travel")
        add(25, month, "Concert tickets", "Riverview Concert Hall", Decimal("120.00"), "expense", "Entertainment")
    else:
        add(20, month, "Laptop purchase", "TechMall Online", Decimal("649.00"), "expense", "Shopping")
        add(22, month, "Refund for returned item", "TechMall Online", Decimal("49.00"), "refund", "Shopping")
        add(25, month, "Transfer to savings", "Savings Account", Decimal("200.00"), "transfer", "Savings")


def write_synthetic_transactions_csv(
    path: str | Path | None = None, year: int = YEAR
) -> Path:
    """Write the deterministic synthetic CSV and return its path."""
    destination = Path(path) if path is not None else SYNTHETIC_CSV_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(build_synthetic_transactions(year))
    return destination
    return records