"""generate_report.py

Render compliance report from template using Jinja2.
Supply JSON file with metrics OR CLI args.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path("docs/compliance")
TEMPLATE_FILE = "ComplianceReport_TEMPLATE.md"


def load_context(json_path: Path | None) -> dict[str, Any]:
    if json_path and json_path.exists():
        with open(json_path) as fh:
            return json.load(fh)
    # fallback demo context
    return {
        "model_name": "Value + Quality (Magic Formula)",
        "report_date": str(date.today()),
        "model_id": "VQ001",
        "version": "0.1.0",
        "owner": "quant_team@company.com",
        "purpose": "Equity long-only systematic value strategy",
        "total_return": "15.2%",
        "annualized_return": "15.2%",
        "annualized_vol": "12.5%",
        "sharpe": "1.22",
        "max_drawdown": "-8.4%",
        "alerts_section": "No breaches recorded.",
        "columns_tested": 5,
        "failed_expectations": 0,
        "changes_log": "Initial model deployment.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, help="JSON file with report context")
    parser.add_argument("--output", type=Path, default=Path("docs/compliance/ComplianceReport.md"))
    args = parser.parse_args()

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape()
    )
    template = env.get_template(TEMPLATE_FILE)
    context = load_context(args.context)
    rendered = template.render(**context)

    args.output.write_text(rendered)
    print(f"Wrote compliance report to {args.output}")


if __name__ == "__main__":
    main()