"""Domain-neutrality guard for the Core Platform (ADR-010 / AP-01).

`src/platform/` must carry no industry vocabulary. Modules still awaiting
generalization are listed in PENDING_GENERALIZATION; that list is a ratchet and
is only ever allowed to shrink.

The banned list deliberately excludes generic business words such as "invoice",
"document" and "weight" — ADR-010 records `validate_invoice` as a known
false-positive class.
"""

from pathlib import Path
import re

import pytest

PLATFORM_ROOT = Path(__file__).resolve().parents[2] / "src" / "platform"

BANNED_VOCABULARY = (
    # Food safety
    "halal",
    "zubaidi",
    "slaughter",
    "poultry",
    "shrimp",
    "foodstuff",
    # Customs / trade
    "importer",
    "exporter",
    "consignee",
    "packing_list",
    "stretching_list",
    "packinglist",
    "stretchinglist",
    "bayan",
    "hs_code",
    "hscode",
    "tariff",
    "customs",
    "shipment",
    "netunitwgt",
    "countryoforigin",
    "country_of_origin",
    # Healthcare
    "physician",
    "diagnosis",
    "icd10",
    # Insurance
    "claimant",
    "policyholder",
    # KYC / AML
    "sanctions",
)

# Modules still carrying domain vocabulary, scheduled for generalization.
# Remove entries as they are cleaned up; never add new ones.
PENDING_GENERALIZATION: frozenset[str] = frozenset()


def _platform_modules() -> list[Path]:
    return sorted(p for p in PLATFORM_ROOT.rglob("*.py") if p.name != "__init__.py")


def _relative(path: Path) -> str:
    return path.relative_to(PLATFORM_ROOT).as_posix()


def _violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8").lower()
    # Word-boundary matching keeps `ImportError` from tripping the "importer" ban.
    return [term for term in BANNED_VOCABULARY if re.search(rf"\b{term}\b", text)]


CLEAN_MODULES = [p for p in _platform_modules() if _relative(p) not in PENDING_GENERALIZATION]


@pytest.mark.parametrize("module", CLEAN_MODULES, ids=_relative)
def test_module_contains_no_domain_vocabulary(module: Path):
    found = _violations(module)
    assert not found, (
        f"{_relative(module)} contains industry vocabulary {found}. "
        "Core Platform code must be domain-neutral — move this to a template artifact."
    )


def test_pending_list_contains_only_real_files():
    missing = sorted(p for p in PENDING_GENERALIZATION if not (PLATFORM_ROOT / p).exists())
    assert missing == [], f"PENDING_GENERALIZATION references files that no longer exist: {missing}"


def test_pending_list_does_not_grow():
    still_dirty = {
        _relative(p) for p in _platform_modules() if _violations(p)
    }
    unexpected = sorted(still_dirty - PENDING_GENERALIZATION)
    assert unexpected == [], (
        f"New domain vocabulary appeared in {unexpected}. "
        "PENDING_GENERALIZATION is a ratchet and must not grow."
    )


def test_pending_entries_are_still_dirty():
    """A cleaned module must be removed from the pending list."""
    now_clean = sorted(
        p for p in PENDING_GENERALIZATION if not _violations(PLATFORM_ROOT / p)
    )
    assert now_clean == [], (
        f"{now_clean} no longer contain domain vocabulary — "
        "remove them from PENDING_GENERALIZATION."
    )
