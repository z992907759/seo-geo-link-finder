#!/usr/bin/env python3
"""Compute deterministic rolling-campaign progress and stop conditions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


POSITIVE_STATUSES = {"quoted", "replied"}


def is_handoff_ready(row: dict[str, Any], max_price_usd: float) -> tuple[bool, str]:
    if row.get("risk_flags") or row.get("status") not in POSITIVE_STATUSES:
        return False, "not_positive_or_risk_held"
    quote = row.get("quote") or {}
    if quote:
        amount = quote.get("amount_max")
        if amount is not None and float(amount) <= max_price_usd:
            return True, "quoted_within_budget"
        return False, "quote_over_budget_or_missing_amount"
    terms = row.get("placement_terms") or {}
    if terms.get("price_status") == "free_editorial_route":
        return True, "free_editorial_route"
    return False, "positive_but_terms_incomplete"


def calculate(outreach_state: dict[str, Any], rolling_state: dict[str, Any]) -> dict[str, Any]:
    maximum = float(rolling_state.get("max_price_usd", 155))
    ready, pending = [], []
    for row in outreach_state.get("prospects", []):
        ok, reason = is_handoff_ready(row, maximum)
        item = {"domain": row.get("domain"), "status": row.get("status"), "reason": reason}
        (ready if ok else pending).append(item)
    target = int(rolling_state.get("positive_target", 20))
    return {
        "handoff_ready_count": len(ready),
        "positive_target": target,
        "remaining_to_target": max(0, target - len(ready)),
        "prospecting_complete": len(ready) >= target,
        "handoff_ready": ready,
        "not_ready": pending,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outreach-state", required=True)
    parser.add_argument("--rolling-state", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    outreach = json.loads(Path(args.outreach_state).read_text(encoding="utf-8"))
    rolling_path = Path(args.rolling_state)
    rolling = json.loads(rolling_path.read_text(encoding="utf-8"))
    result = calculate(outreach, rolling)
    if args.write:
        rolling.update(result)
        rolling_path.write_text(json.dumps(rolling, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
