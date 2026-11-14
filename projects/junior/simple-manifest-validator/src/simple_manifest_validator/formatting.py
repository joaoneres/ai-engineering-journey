"""Render a validation report as plain text."""


def format_report(report: dict) -> str:
    """Render the validation report. The same text is printed and, optionally, saved."""
    lines = [
        "===== Validation report =====",
        f"Records: {report['total_records']}",
        f"Errors: {report['total_errors']}",
        "Problems:",
    ]
    problems = report["problems"]
    if problems:
        lines.extend(f"- record {item['record']}: {item['message']}" for item in problems)
    else:
        lines.append("- none")
    lines.append(f"Final status: {report['status']}")
    return "\n".join(lines) + "\n"
