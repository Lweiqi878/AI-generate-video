#!/usr/bin/env python3
"""Validate the V2 slate without generating outputs."""
from __future__ import annotations

from build_all import load_works, print_summary, validate_works


def main() -> int:
    works = load_works()
    errors = validate_works(works)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print_summary(works)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
