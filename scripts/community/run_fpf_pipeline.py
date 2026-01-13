#!/usr/bin/env python3
"""Run the complete FPF data pipeline: fetch -> parse -> embed.

This script orchestrates the full FPF data pipeline:
1. Fetch emails from Gmail (requires credentials.json)
2. Parse emails and import posts to database
3. Generate embeddings for semantic search

Usage:
    # Run full pipeline
    uv run python scripts/community/run_fpf_pipeline.py

    # Skip fetch step (if you already have the emails)
    uv run python scripts/community/run_fpf_pipeline.py --skip-fetch

    # Only run embedding step
    uv run python scripts/community/run_fpf_pipeline.py --embed-only

    # Limit embeddings (for testing)
    uv run python scripts/community/run_fpf_pipeline.py --embed-only --limit 100
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(name: str, cmd: list[str], cwd: Path | None = None) -> bool:
    """Run a pipeline step and return success status."""
    print()
    print("=" * 60)
    print(f"STEP: {name}")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0:
        print(f"\nFailed with exit code {result.returncode}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run the complete FPF data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip the fetch step (use existing emails)",
    )
    parser.add_argument(
        "--embed-only",
        action="store_true",
        help="Only run the embedding step",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of posts to embed (useful for testing)",
    )
    parser.add_argument(
        "--force-embed",
        action="store_true",
        help="Re-embed posts that already have embeddings",
    )

    args = parser.parse_args()

    # Get the scripts directory
    scripts_dir = Path(__file__).parent
    api_dir = scripts_dir.parent.parent

    print("=" * 60)
    print("FPF DATA PIPELINE")
    print("=" * 60)

    steps_to_run = []

    if args.embed_only:
        steps_to_run = ["embed"]
    elif args.skip_fetch:
        steps_to_run = ["parse", "embed"]
    else:
        steps_to_run = ["fetch", "parse", "embed"]

    # Build step commands
    steps = {
        "fetch": (
            "Fetch FPF emails from Gmail",
            [sys.executable, str(scripts_dir / "fetch_fpf_emails.py")],
        ),
        "parse": (
            "Parse emails into database",
            [sys.executable, str(scripts_dir / "parse_fpf_emails.py")],
        ),
        "embed": (
            "Generate embeddings for posts",
            [sys.executable, str(scripts_dir / "embed_fpf_posts.py")]
            + (["--force"] if args.force_embed else [])
            + (["--limit", str(args.limit)] if args.limit else []),
        ),
    }

    print(f"\nSteps to run: {', '.join(steps_to_run)}")

    for step_name in steps_to_run:
        name, cmd = steps[step_name]
        if not run_step(name, cmd, cwd=api_dir):
            print(f"\nPipeline failed at step: {step_name}")
            sys.exit(1)

    print()
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Start the API: uv run uvicorn src.main:app --reload")
    print("  2. Start the frontend: cd ../web && npm run dev")
    print("  3. Try searching: 'Find posts about lost dogs in Warren'")
    print()


if __name__ == "__main__":
    main()
