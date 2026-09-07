"""Personal Finance Agent - deterministic analytical foundation.

This package implements the first deterministic foundation of the Personal
Finance Agent described in ``docs/06_implementation.md`` (Milestones 1-2 and the
verification portions of Milestone 5). It deliberately contains no LLM, agent
runtime, database, or external integration.

Pipeline:

    CSV source data
      -> load (data.py)
      -> validate (validation.py)
      -> normalize (normalization.py)
      -> canonical transactions (models.py)
      -> analytical capabilities (analytics.py)
      -> verification (verification.py)

Only the Python standard library is used.
"""

from .models import (
    CategoryOrigin,
    DataQualityStatus,
    Direction,
    NormalizationStatus,
    Period,
    ResultStatus,
    Transaction,
)

__all__ = [
    "CategoryOrigin",
    "DataQualityStatus",
    "Direction",
    "NormalizationStatus",
    "Period",
    "ResultStatus",
    "Transaction",
]

__version__ = "0.1.0"