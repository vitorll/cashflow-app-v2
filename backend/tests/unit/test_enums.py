"""Phase A2 — Domain enum tests.

These tests are intentionally RED. The module app.domain.enums does not exist yet.
The import below will raise ModuleNotFoundError, which pytest will report as a
collection error — the canonical RED state before any implementation code is written.

It is our way.
"""

# This import will fail until app/domain/enums.py is created.
from app.domain.enums import (
    Phase,
    SectionType,
    SeriesType,
    ImportStatus,
    VersionType,
    SourceType,
    PHASES,
)


def test_phase_enum_values():
    """Phase must have exactly the values: p1, p2, p3, p4, p5, total."""
    expected = {"p1", "p2", "p3", "p4", "p5", "total"}
    actual = {m.value for m in Phase}
    assert actual == expected, f"Phase values mismatch: {actual} != {expected}"


def test_phases_constant_excludes_total():
    """PHASES constant must be exactly [Phase.p1 … Phase.p5] — 5 items, no total."""
    assert len(PHASES) == 5, f"Expected 5 phases, got {len(PHASES)}"
    assert Phase.total not in PHASES, "PHASES must not include Phase.total"
    assert list(PHASES) == [Phase.p1, Phase.p2, Phase.p3, Phase.p4, Phase.p5]


def test_section_type_values():
    """SectionType must have exactly: revenue, direct_costs, overheads, capex, contingency."""
    expected = {"revenue", "direct_costs", "overheads", "capex", "contingency"}
    actual = {m.value for m in SectionType}
    assert actual == expected, f"SectionType values mismatch: {actual} != {expected}"


def test_series_type_values():
    """SeriesType must have exactly: cumulative, periodic."""
    expected = {"cumulative", "periodic"}
    actual = {m.value for m in SeriesType}
    assert actual == expected, f"SeriesType values mismatch: {actual} != {expected}"


def test_import_status_values():
    """ImportStatus must have exactly: pending, processing, complete, failed."""
    expected = {"pending", "processing", "complete", "failed"}
    actual = {m.value for m in ImportStatus}
    assert actual == expected, f"ImportStatus values mismatch: {actual} != {expected}"


def test_version_type_values():
    """VersionType must have exactly: budget, current, forecast."""
    expected = {"budget", "current", "forecast"}
    actual = {m.value for m in VersionType}
    assert actual == expected, f"VersionType values mismatch: {actual} != {expected}"


def test_source_type_values():
    """SourceType must have exactly: excel, manual, api."""
    expected = {"excel", "manual", "api"}
    actual = {m.value for m in SourceType}
    assert actual == expected, f"SourceType values mismatch: {actual} != {expected}"


def test_phase_enum_values_are_strings():
    """Every Phase member's .value must be a plain string."""
    for member in Phase:
        assert isinstance(member.value, str), (
            f"Phase.{member.name}.value is {type(member.value)}, expected str"
        )
