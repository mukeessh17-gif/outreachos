# Week 3 Day 2: pure lead logic functions
# OutreachOS - AI sales outreach tool
# These functions take input and return output without touching files, databases, or networks.


def is_good_lead(employees: int) -> bool:
    """Return True if employees is between 5 and 20 (inclusive)."""
    # A good lead is neither too small nor too big.
    return 5 <= employees <= 20


def score_lead(employees: int, has_website: bool) -> int:
    """Score a lead: 10 for good size + website, 5 for only one, 0 otherwise."""
    good_size = is_good_lead(employees)

    if good_size and has_website:
        return 10
    if good_size or has_website:
        return 5
    return 0


def clean_company_name(name: str) -> str:
    """Strip edges, collapse internal spaces, and title-case the name."""
    # split() with no arguments splits on any whitespace and drops empties.
    # " ".join(...) puts single spaces back between words.
    collapsed = " ".join(name.split())
    return collapsed.title()