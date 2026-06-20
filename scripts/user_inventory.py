#!/usr/bin/env python3
"""Build a self-contained user/subscription inventory HTML page.

Read-only ops tool. Reads tab-separated query output (header row + data rows)
from a file or stdin and renders ./user_inventory.html.

Generate the input on the box that can reach the DB, e.g.:

    psql "$DATABASE_URL" -A -F $'\t' --pset=footer=off -c "
        SELECT u.email,
               u.display_name              AS name,
               COALESCE(u.plan,'free')     AS plan,
               u.is_admin,
               u.email_verified,
               (u.provisioned_at IS NOT NULL) AS onboarded,
               u.created_at::date          AS created,
               u.last_active_at::date      AS last_active,
               pl.content_generation_enabled AS content_gen
        FROM users u
        LEFT JOIN plan_limits pl ON pl.plan = u.plan
        ORDER BY u.created_at;
    " | python3 scripts/user_inventory.py

The HTML contains PII (emails) — keep it local, do NOT commit it.
"""
import csv
import html
import sys
from collections import Counter
from datetime import datetime, timezone

PLAN_COLORS = {"free": "#6b7280", "pro": "#5B5BD6", "max": "#E8A444"}


def main() -> None:
    src = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
    rows = [r for r in csv.reader(src) if any(c.strip() for c in r)]
    if not rows:
        sys.exit("no input rows")
    header, data = rows[0], rows[1:]

    plan_idx = header.index("plan") if "plan" in header else None
    plan_counts = Counter(r[plan_idx] for r in data) if plan_idx is not None else {}
    chips = "".join(
        f'<span class="chip" style="--c:{PLAN_COLORS.get(p, "#888")}">{html.escape(p)}: {n}</span>'
        for p, n in sorted(plan_counts.items())
    )

    thead = "".join(f"<th>{html.escape(h)}</th>" for h in header)
    body_rows = []
    for r in data:
        cells = []
        for i, val in enumerate(r):
            v = html.escape(val)
            if plan_idx is not None and i == plan_idx:
                c = PLAN_COLORS.get(val, "#888")
                v = f'<span class="plan" style="--c:{c}">{v}</span>'
            cells.append(f"<td>{v}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Private Internet — User Inventory</title>
<style>
  :root{{color-scheme:dark}}
  body{{font:14px/1.5 -apple-system,Inter,Segoe UI,sans-serif;margin:0;background:#0d0e12;color:#e6e7ea}}
  .wrap{{max-width:1100px;margin:0 auto;padding:32px 24px}}
  h1{{font-size:20px;margin:0 0 4px}}
  .meta{{color:#9aa0aa;font-size:13px;margin-bottom:18px}}
  .chips{{margin-bottom:18px;display:flex;gap:8px;flex-wrap:wrap}}
  .chip{{padding:4px 10px;border-radius:999px;border:1px solid var(--c);color:var(--c);font-size:12px}}
  table{{border-collapse:collapse;width:100%;font-size:13px}}
  th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid #1f2229;white-space:nowrap}}
  th{{color:#9aa0aa;font-weight:600;border-bottom:1px solid #2b2f38;position:sticky;top:0;background:#0d0e12}}
  tr:hover td{{background:#14161b}}
  .plan{{padding:2px 8px;border-radius:6px;border:1px solid var(--c);color:var(--c);font-size:12px}}
</style></head><body><div class="wrap">
<h1>User &amp; Subscription Inventory</h1>
<div class="meta">{len(data)} users · generated {generated}</div>
<div class="chips">{chips}</div>
<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>
</div></body></html>"""
    with open("user_inventory.html", "w") as f:
        f.write(out)
    print(f"Wrote user_inventory.html ({len(data)} users).")


if __name__ == "__main__":
    main()
