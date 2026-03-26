from __future__ import annotations

from typing import Any


def render_process_summary(payload: dict[str, Any]) -> str:
    process_type = payload["process_type"]
    if process_type == "invoice":
        total_net = sum(item["quantity"] * item["unit_price"] for item in payload["items"])
        total_tax = sum(
            item["quantity"] * item["unit_price"] * (item["tax_rate"] / 100.0)
            for item in payload["items"]
        )
        total_gross = total_net + total_tax
        return (
            f"Rechnung {payload['request_id']} fuer {payload['customer']['name']}: "
            f"netto={total_net:.2f} {payload['currency']}, "
            f"steuer={total_tax:.2f} {payload['currency']}, "
            f"brutto={total_gross:.2f} {payload['currency']}, "
            f"status={payload['status']}"
        )

    if process_type == "bookkeeping":
        debit = sum(line["amount"] for line in payload["lines"] if line["direction"] == "debit")
        credit = sum(line["amount"] for line in payload["lines"] if line["direction"] == "credit")
        return (
            f"Buchung {payload['request_id']}: soll={debit:.2f} {payload['currency']}, "
            f"haben={credit:.2f} {payload['currency']}, status={payload['status']}"
        )

    if process_type == "tax":
        totals = payload.get("totals", {})
        return (
            f"Steuerfall {payload['request_id']} fuer {payload['period']}: "
            f"netto={totals.get('net_amount', 0):.2f}, "
            f"steuer={totals.get('tax_amount', 0):.2f}, "
            f"status={payload['status']}"
        )

    if process_type == "formation":
        total_steps = len(payload["steps"])
        completed = sum(1 for step in payload["steps"] if step.get("status") == "done")
        return (
            f"Gruendung {payload['venture_name']}: "
            f"schritte={completed}/{total_steps}, status={payload['status']}"
        )

    if process_type == "team":
        team = payload["team"]
        return (
            f"Team {team['id']} in {team['org_unit']}: "
            f"zielgroesse={team['members_target']}, access_profile={team['access_profile']}, "
            f"status={payload['status']}"
        )

    if process_type == "role_change":
        change = payload["role_change"]
        return (
            f"Rollenwechsel {change['subject_kind']} {change['subject_id']}: "
            f"{change['current_role']} -> {change['target_role']}, status={payload['status']}"
        )

    if process_type == "joiner_mover":
        pos = payload["person_position"]
        return (
            f"{pos['action']} fuer {pos['person_ref']} in Team {pos['target_team']}: "
            f"access_profile={pos['access_profile']}, status={payload['status']}"
        )

    return f"Unbekannter Prozess {payload['request_id']}"
