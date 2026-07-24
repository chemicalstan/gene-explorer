from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from gene_explorer.repository import GeneRepository

# Canonical cancer vocabulary. A startup check (see asgi.build_app) asserts this
# equals the set of cancer_indication values in the dataset, so the two cannot drift.
CANCER_TYPES: tuple[str, ...] = (
    "breast",
    "colorectal",
    "gastric",
    "glioblastoma",
    "lung",
    "melanoma",
    "ovarian",
    "pancreatic",
    "prostate",
    "renal",
)

CancerName = Literal[CANCER_TYPES]  # type: ignore[valid-type]


class GeneExplorerError(Exception):
    """Base class for domain errors."""


class DataValidationError(GeneExplorerError):
    """The dataset does not match the code's expectations."""


@dataclass
class GeneContext:
    """Per-request state passed to tools through the Agents SDK run context."""

    repo: GeneRepository
    tool_calls: list[str] = field(default_factory=list)
