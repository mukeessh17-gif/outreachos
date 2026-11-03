from week4.evals.golden_set import build_golden_set
from week4.evals.run import run_evaluation


def test_golden_set_has_thirty_fake_leads() -> None:
    leads = build_golden_set()
    assert len(leads) == 30
    assert all(str(lead["name"]).startswith("Fictional ") for lead in leads)


def test_offline_prompt_comparison_scores_improvement() -> None:
    report = run_evaluation()
    assert report["golden_leads"] == 30
    assert report["winner"] == "v2"
    improved = report["weakest_case_improved_once"]
    assert improved["before"]["personalization"] == 1
    assert improved["after"]["personalization"] == 5
