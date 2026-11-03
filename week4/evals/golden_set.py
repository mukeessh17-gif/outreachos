"""A reproducible, entirely fictional 30-company evaluation set."""

from week4.schemas import ResearchBrief

_industries = [
    "fabrication",
    "food packaging",
    "industrial maintenance",
    "warehouse operations",
    "specialty manufacturing",
]
_pain_points = [
    "Manual production scheduling",
    "Slow inventory reconciliation",
    "Disconnected maintenance records",
    "Repeated warehouse data entry",
    "Unclear supplier handoffs",
]
_angles = [
    "Workflow automation for production planning",
    "A simpler process for inventory updates",
    "Centralized maintenance information",
    "Reducing repeated data entry",
    "Clearer supplier coordination",
]


def build_golden_set() -> list[dict[str, object]]:
    """Return thirty fake leads with synthetic, public-style research briefs."""
    examples: list[dict[str, object]] = []
    for index in range(30):
        examples.append(
            {
                "id": index + 1,
                "name": f"Fictional {_industries[index % len(_industries)].title()} {index + 1:02}",
                "brief": ResearchBrief(
                    pain_points=[_pain_points[index % len(_pain_points)]],
                    trigger="unknown",
                    best_angle=_angles[index % len(_angles)],
                    confidence=0.5,
                    sources=[f"https://public.example/company/{index + 1}"],
                ),
            }
        )
    return examples
