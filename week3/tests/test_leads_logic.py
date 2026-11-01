# Week 3 Day 2: tests for leads_logic.py
# Run with: pytest -v week3/tests/test_leads_logic.py

import pytest
from leads_logic import is_good_lead, score_lead, clean_company_name


# ------------------------------------------------------------
# is_good_lead tests (normal + boundary)
# ------------------------------------------------------------
@pytest.mark.parametrize(
    "employees, expected",
    [
        (4, False),   # below 5
        (5, True),    # boundary: exactly 5
        (10, True),   # normal good
        (20, True),   # boundary: exactly 20
        (21, False),  # above 20
        (0, False),   # zero employees
        (100, False), # very large
    ],
)
def test_is_good_lead(employees: int, expected: bool) -> None:
    assert is_good_lead(employees) is expected


# ------------------------------------------------------------
# score_lead tests
# ------------------------------------------------------------
def test_score_lead_good_size_and_website() -> None:
    assert score_lead(10, True) == 10


def test_score_lead_good_size_no_website() -> None:
    assert score_lead(10, False) == 5


def test_score_lead_bad_size_with_website() -> None:
    assert score_lead(30, True) == 5


def test_score_lead_bad_size_no_website() -> None:
    assert score_lead(30, False) == 0


# ------------------------------------------------------------
# clean_company_name tests
# ------------------------------------------------------------
def test_clean_company_name_strip_edges() -> None:
    assert clean_company_name("  acme  ") == "Acme"


def test_clean_company_name_collapse_spaces() -> None:
    assert clean_company_name("Kovai   Textiles") == "Kovai Textiles"


def test_clean_company_name_title_case() -> None:
    assert clean_company_name("RS PURAM stores") == "Rs Puram Stores"


def test_clean_company_name_empty_string() -> None:
    assert clean_company_name("") == ""


def test_clean_company_name_only_spaces() -> None:
    assert clean_company_name("   ") == ""