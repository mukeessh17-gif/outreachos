"""Run the 100-case synthetic reply-classification evaluation."""

import json

from week4.replies import evaluate_fake_replies


def main() -> None:
    report = evaluate_fake_replies()
    print(f"Accuracy: {report['accuracy']:.1%} ({report['cases']} fictional replies)")
    print("Confusion matrix (rows=expected, columns=predicted):")
    print(json.dumps(report["confusion"], indent=2))


if __name__ == "__main__":
    main()
