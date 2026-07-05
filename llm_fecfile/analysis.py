from datetime import datetime

from tabulate import tabulate

# Base FEC form codes. The .fec header's form_type is one of these with a
# trailing N (new/original), A (amendment), or T (termination) - e.g. "F3XN",
# "F3A", "F24N". F99 (misc. text) doesn't use the suffix scheme.
BASE_FORMS = {
    "F1", "F1M", "F2", "F3", "F3P", "F3X", "F3L",
    "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F13", "F24",
}


def parse_form_type(form_type):
    """Split a form_type like 'F3XN' into its base form ('F3X') and status
    suffix ('N'/'A'/'T'), or (form_type, None) if it doesn't use the suffix
    scheme (e.g. 'F99') or isn't a recognized base form."""
    form_type = (form_type or "").upper()
    if len(form_type) > 1 and form_type[:-1] in BASE_FORMS and form_type[-1] in "NAT":
        return form_type[:-1], form_type[-1]
    return form_type, None


def filing_status_label(form_type):
    _, suffix = parse_form_type(form_type)
    return {"A": "Amendment", "T": "Termination"}.get(suffix, "Original Filing")


def committee_id(filing_info):
    return filing_info.get("filer_committee_id_number") or filing_info.get(
        "committee_id_number", "Not Available"
    )


def person_name(info, prefix):
    """Build a display name from split first/last name fields, e.g. prefix='treasurer'
    reads treasurer_first_name/treasurer_last_name."""
    last = (info.get(f"{prefix}_last_name") or "").strip()
    first = (info.get(f"{prefix}_first_name") or "").strip()
    if last and first:
        return f"{last}, {first}"
    return last or first or "Not Available"


def format_date(date_obj):
    """Format a date value (string or datetime) to just its YYYY-MM-DD part."""
    if not date_obj:
        return None
    try:
        if isinstance(date_obj, str):
            return date_obj.split(" ")[0]
        if hasattr(date_obj, "date"):
            return str(date_obj.date())
        if hasattr(date_obj, "strftime"):
            return date_obj.strftime("%Y-%m-%d")
        return str(date_obj)
    except (ValueError, TypeError, AttributeError):
        return None


def calculate_coverage_days(from_date, through_date):
    if not from_date or not through_date:
        return None
    try:
        start_str = format_date(from_date)
        end_str = format_date(through_date)
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        return (end_date - start_date).days + 1
    except (ValueError, TypeError, AttributeError):
        return None


def contributor_name(contrib):
    name = (contrib.get("contributor_organization_name") or "").strip()
    if name:
        return name
    last = (contrib.get("contributor_last_name") or "").strip()
    first = (contrib.get("contributor_first_name") or "").strip()
    if last and first:
        return f"{last}, {first}"
    return last or first or "Not Available"


def payee_name(item):
    name = (item.get("payee_organization_name") or "").strip()
    if name:
        return name
    last = (item.get("payee_last_name") or "").strip()
    first = (item.get("payee_first_name") or "").strip()
    if last and first:
        return f"{last}, {first}"
    return last or first or "Not Available"


def _truncate(value, length):
    value = value or "Not Available"
    return value if len(value) <= length else value[: length - 3] + "..."


def format_summary_table(filing_info):
    coverage_from = filing_info.get("coverage_from_date", "")
    coverage_through = filing_info.get("coverage_through_date", "")
    formatted_from = format_date(coverage_from)
    formatted_through = format_date(coverage_through)
    coverage_days = calculate_coverage_days(coverage_from, coverage_through)

    if coverage_days and formatted_from and formatted_through:
        coverage_text = f"{formatted_from} to {formatted_through} ({coverage_days} days)"
    elif formatted_from and formatted_through:
        coverage_text = f"{formatted_from} to {formatted_through}"
    else:
        coverage_text = "Not Available"

    form_type = filing_info.get("form_type", "").upper()

    data = [
        ["FEC Committee ID", committee_id(filing_info)],
        ["Committee", filing_info.get("committee_name", "Not Available")],
        ["Form Type", form_type],
        ["Coverage Period", coverage_text],
        ["Total Receipts", f"${filing_info.get('col_a_total_receipts', 0):,.2f}"],
        ["Total Disbursements", f"${filing_info.get('col_a_total_disbursements', 0):,.2f}"],
        [
            "Ending Cash on Hand",
            f"${filing_info.get('col_a_cash_on_hand_close_of_period', 0):,.2f}",
        ],
        ["Filing Status", filing_status_label(form_type)],
    ]
    return tabulate(data, tablefmt="simple", colalign=("left", "right"))


def format_contributions_table(contributions, limit=10):
    if not contributions:
        return "No contributions found."

    sorted_contribs = sorted(
        contributions, key=lambda x: x.get("contribution_amount", 0) or 0, reverse=True
    )[:limit]

    data = []
    for i, contrib in enumerate(sorted_contribs, 1):
        name = _truncate(contributor_name(contrib), 35)
        amount = f"${contrib.get('contribution_amount', 0) or 0:,.2f}"
        city = contrib.get("contributor_city", "")
        state = contrib.get("contributor_state", "")
        location = f"{city}, {state}" if city and state else state or city or "Not Available"
        location = _truncate(location, 25)
        data.append([i, name, amount, location])

    headers = ["#", "Contributor Name", "Amount", "Location"]
    return tabulate(data, headers=headers, tablefmt="simple", numalign="right")


def format_disbursements_table(disbursements, limit=10):
    if not disbursements:
        return "No disbursements found."

    sorted_disb = sorted(
        disbursements, key=lambda x: x.get("expenditure_amount", 0) or 0, reverse=True
    )[:limit]

    data = []
    for i, disb in enumerate(sorted_disb, 1):
        recipient = _truncate(payee_name(disb), 30)
        amount = f"${disb.get('expenditure_amount', 0) or 0:,.2f}"
        exp_date = disb.get("expenditure_date") or disb.get("disbursement_date", "")
        formatted_date = format_date(exp_date) if exp_date else "Not Available"
        purpose = _truncate(disb.get("expenditure_purpose_descrip", "Not Available"), 20)
        data.append([i, recipient, amount, formatted_date, purpose])

    headers = ["#", "Recipient Name", "Amount", "Date", "Purpose"]
    return tabulate(data, headers=headers, tablefmt="simple", numalign="right")


def format_state_totals_table(contributions, limit=15):
    """Aggregate contribution totals by contributor_state."""
    totals = {}
    for c in contributions:
        state = (c.get("contributor_state") or "Unknown").strip() or "Unknown"
        amount = c.get("contribution_amount", 0) or 0
        entry = totals.setdefault(state, [0.0, 0])
        entry[0] += amount
        entry[1] += 1

    rows = sorted(totals.items(), key=lambda kv: kv[1][0], reverse=True)[:limit]
    data = [[state, count, f"${total:,.2f}"] for state, (total, count) in rows]
    headers = ["State", "# Contributions", "Total"]
    return tabulate(data, headers=headers, tablefmt="simple", numalign="right")


def format_purpose_totals_table(disbursements, limit=15):
    """Aggregate disbursement totals by expenditure_purpose_descrip."""
    totals = {}
    for d in disbursements:
        purpose = (d.get("expenditure_purpose_descrip") or "Unspecified").strip() or "Unspecified"
        amount = d.get("expenditure_amount", 0) or 0
        entry = totals.setdefault(purpose, [0.0, 0])
        entry[0] += amount
        entry[1] += 1

    rows = sorted(totals.items(), key=lambda kv: kv[1][0], reverse=True)[:limit]
    data = [[_truncate(purpose, 40), count, f"${total:,.2f}"] for purpose, (total, count) in rows]
    headers = ["Purpose", "# Disbursements", "Total"]
    return tabulate(data, headers=headers, tablefmt="simple", numalign="right")


def format_itemization_counts_table(itemizations):
    data = [[schedule, f"{len(items):,}"] for schedule, items in itemizations.items()]
    return tabulate(data, headers=["Schedule", "Item Count"], tablefmt="simple", numalign="right")


def build_aggregate_tables(filing_info, itemizations):
    """Build the full set of precomputed aggregate tables for a financial filing.

    These are the authoritative numbers - they're computed over ALL itemizations,
    not just whatever capped/truncated subset ends up in the raw JSON dump.
    """
    sections = []

    sections.append("SUMMARY")
    sections.append("-" * 50)
    sections.append(format_summary_table(filing_info))
    sections.append("")

    if itemizations:
        sections.append("ITEMIZATION COUNTS (all schedules, full totals)")
        sections.append("-" * 50)
        sections.append(format_itemization_counts_table(itemizations))
        sections.append("")

        contributions = itemizations.get("Schedule A", [])
        if contributions:
            sections.append("TOP 20 CONTRIBUTIONS (Schedule A, by amount, full dataset)")
            sections.append("-" * 50)
            sections.append(format_contributions_table(contributions, limit=20))
            sections.append("")

            sections.append("CONTRIBUTION TOTALS BY STATE (full dataset)")
            sections.append("-" * 50)
            sections.append(format_state_totals_table(contributions))
            sections.append("")

        disbursements = itemizations.get("Schedule B", [])
        if disbursements:
            sections.append("TOP 20 DISBURSEMENTS (Schedule B, by amount, full dataset)")
            sections.append("-" * 50)
            sections.append(format_disbursements_table(disbursements, limit=20))
            sections.append("")

            sections.append("DISBURSEMENT TOTALS BY PURPOSE (full dataset)")
            sections.append("-" * 50)
            sections.append(format_purpose_totals_table(disbursements))
            sections.append("")

        independent_exp = itemizations.get("Schedule E", [])
        if independent_exp:
            sections.append("TOP 20 INDEPENDENT EXPENDITURES (Schedule E, by amount, full dataset)")
            sections.append("-" * 50)
            sections.append(format_disbursements_table(independent_exp, limit=20))
            sections.append("")

    return "\n".join(sections)
