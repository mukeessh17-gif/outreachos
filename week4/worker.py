"""Command-line PostgreSQL job worker; use one worker process per org."""

import argparse
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

from week2.db import get_engine
from week4.email_writer import create_and_save_sequence
from week4.job_queue import process_one
from week4.research import research_lead
from week4.scheduler import process_due_sends

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_handlers(engine: Any) -> dict[str, Any]:
    return {
        "research": lambda job: research_lead(
            job["org_id"],
            job["lead_id"],
            engine=engine,
        ),
        "write": lambda job: create_and_save_sequence(
            job["org_id"],
            job["lead_id"],
            engine=engine,
            prompt_version=job["payload"].get("prompt_version", "v2"),
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process jobs for one organization.")
    parser.add_argument("--org-id", type=int, required=True)
    parser.add_argument("--once", action="store_true", help="Process at most one job.")
    args = parser.parse_args()
    engine = get_engine()
    handlers = build_handlers(engine)
    while True:
        scheduled = process_due_sends(args.org_id, engine=engine)
        if scheduled["processed"] or scheduled["failed"]:
            logging.info("scheduled sends processed=%s", scheduled)
        result = process_one(args.org_id, handlers, engine=engine)
        if args.once:
            print(result)
            return
        if result == "idle":
            time.sleep(2)


if __name__ == "__main__":
    main()
