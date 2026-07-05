import json

import llm

from . import analysis, fec_api
from .cache import get_filing

MAX_ITEMS_PER_SCHEDULE = 200
SCHEDULE_ALIASES = {"sa": "Schedule A", "sb": "Schedule B", "se": "Schedule E"}
VALID_VARIANTS = {"summary", "full", *SCHEDULE_ALIASES}


def parse_argument(argument):
    """Split a fragment loader argument like '1896830/summary' into
    (filing_id, variant). variant is None for the default (capped raw data)
    behavior."""
    if "/" in argument:
        filing_id, variant = argument.split("/", 1)
    else:
        filing_id, variant = argument, None

    if not filing_id.isdigit() or int(filing_id) <= 0:
        raise ValueError(
            f"Invalid filing ID '{filing_id}'. Must be a positive numeric FEC filing ID."
        )

    if variant is not None and variant not in VALID_VARIANTS:
        raise ValueError(
            f"Invalid fragment variant '{variant}'. Use one of: "
            f"{', '.join(sorted(VALID_VARIANTS))}, or omit it for the default."
        )

    return filing_id, variant


def _sorted_by_amount(items, amount_key):
    return sorted(items, key=lambda x: x.get(amount_key, 0) or 0, reverse=True)


def _cap_itemizations(itemizations, limit):
    """Cap each schedule's itemizations to its highest-amount entries,
    returning (capped_itemizations, notes_about_what_was_dropped)."""
    amount_keys = {
        "Schedule A": "contribution_amount",
        "Schedule B": "expenditure_amount",
        "Schedule E": "expenditure_amount",
    }
    capped = {}
    notes = []
    for schedule, items in itemizations.items():
        if len(items) <= limit:
            capped[schedule] = items
            continue
        amount_key = amount_keys.get(schedule)
        ordered = _sorted_by_amount(items, amount_key) if amount_key else items
        capped[schedule] = ordered[:limit]
        notes.append(
            f"{schedule}: showing {limit} of {len(items):,} itemizations "
            f"(sorted by amount, highest first). Aggregate totals above cover ALL "
            f"{len(items):,} items - use fec:{{id}}/full or a schedule-specific "
            f"fragment (e.g. fec:{{id}}/sa) if you need every record."
        )
    return capped, notes


def _build_raw_payload(filing_data, variant):
    """Return (payload_dict_or_None, truncation_notes) for the raw data section."""
    if variant == "summary":
        return None, []

    if variant in SCHEDULE_ALIASES:
        schedule = SCHEDULE_ALIASES[variant]
        items = filing_data.get("itemizations", {}).get(schedule, [])
        return {"itemizations": {schedule: items}}, []

    if variant == "full":
        return filing_data, []

    itemizations = filing_data.get("itemizations")
    if not itemizations:
        return filing_data, []

    capped, notes = _cap_itemizations(itemizations, MAX_ITEMS_PER_SCHEDULE)
    payload = dict(filing_data)
    payload["itemizations"] = capped
    return payload, notes


def _form_specific_guidance(base_form, filing_info):
    if base_form in ("F1", "F1M"):
        return [
            "PURPOSE: Statement of Organization - registers a committee with the FEC (not financial)",
            "KEY FIELDS: committee_name, committee_type, committee_url, committee_email",
            "TREASURER: treasurer_first_name / treasurer_last_name (no single combined name field)",
            "CUSTODIAN OF RECORDS: custodian_first_name / custodian_last_name",
            "ADDRESS: street_1, street_2, city, state, zip_code",
        ]
    if base_form == "F2":
        return [
            "PURPOSE: Statement of Candidacy - declares candidacy for federal office (not financial)",
            "CANDIDATE NAME: candidate_first_name / candidate_last_name (no single combined field)",
            "OFFICE/STATE/DISTRICT: candidate_office ('H'/'S'/'P'), candidate_state, candidate_district",
            "PARTY: candidate_party_code",
            "AUTHORIZED COMMITTEE: authorized_committee_id_number, authorized_committee_name",
        ]
    if base_form == "F99":
        return [
            "PURPOSE: Miscellaneous text communication (not financial)",
            "KEY FIELD: 'text' at the top level of the filing data contains the substantive content",
            "text_code may categorize the type of communication",
        ]
    return None


def fec_fragment_loader(argument):
    """Load FEC filing information as a fragment.

    Argument forms: '<filing_id>' (default), '<filing_id>/summary' (no raw
    itemizations), '<filing_id>/sa' or '/sb' or '/se' (one schedule's full
    itemizations, uncapped), '<filing_id>/full' (everything, uncapped), or
    'committee:<committee_id>' for a committee's recent filing history.
    """
    if argument.startswith("committee:"):
        committee_id = argument[len("committee:"):]
        text = fec_api.committee_fragment_text(committee_id)
        return llm.Fragment(text, f"fec:committee:{committee_id}")

    filing_id, variant = parse_argument(argument)

    filing_data = get_filing(filing_id)
    if filing_data is None:
        raise ValueError(
            f"FEC filing {filing_id} was not found. It may not exist, or may "
            f"not yet be posted to docquery.fec.gov."
        )

    filing_info = filing_data.get("filing", {})
    form_type = filing_info.get("form_type", "")
    base_form, _ = analysis.parse_form_type(form_type)
    has_financial_summary = any(k.startswith("col_a_") for k in filing_info)
    itemizations = filing_data.get("itemizations") or {}

    analysis_text = []

    analysis_text.append("=== RESPONSE STYLE INSTRUCTIONS ===")
    analysis_text.append("When responding about this FEC filing:")
    analysis_text.append(
        "- Start with your best judgment about whether this filing has unusual aspects "
        "(no activity is not unusual)"
    )
    analysis_text.append("- Avoid excessive use of asterisks or bold text")
    analysis_text.append("- Write in a simple, direct style")
    analysis_text.append("- Group related information together in coherent sections")
    analysis_text.append("- Don't provide a summary at the end")

    analysis_text.append("\n=== FEC FILING ANALYSIS INSTRUCTIONS ===")
    analysis_text.append(f"FORM TYPE: {form_type} (base form: {base_form})")

    guidance = _form_specific_guidance(base_form, filing_info)
    if guidance:
        analysis_text.extend(guidance)
    else:
        analysis_text.append(
            "PURPOSE: Financial or specialized disclosure report. Field availability varies - "
            "check the raw data below for what this specific filing includes."
        )

    analysis_text.append("\n=== AMENDMENT/TERMINATION STATUS ===")
    analysis_text.append(f"STATUS: {analysis.filing_status_label(form_type)}")
    analysis_text.append(
        "NOTE: This determination comes from the trailing letter on form_type "
        "('N'=original, 'A'=amendment, 'T'=termination). The parsed filing data has "
        "no field pointing back to the filing it amends - that linkage is only "
        "available on FEC.gov or via the FEC API's committee filing history."
    )

    if filing_info.get("coverage_from_date") or filing_info.get("coverage_through_date"):
        analysis_text.append("\n=== COVERAGE PERIOD ===")
        analysis_text.append("FIELDS: 'coverage_from_date' and 'coverage_through_date'")
        analysis_text.append(
            "FORMAT: Usually YYYY-MM-DD, may include time/timezone (ignore the time portion)"
        )

    if has_financial_summary:
        analysis_text.append("\n=== FINANCIAL SUMMARY COLUMNS ===")
        analysis_text.append("RECEIPTS: 'col_a_total_receipts'")
        analysis_text.append("DISBURSEMENTS: 'col_a_total_disbursements'")
        analysis_text.append("CASH ON HAND: 'col_a_cash_on_hand_close_of_period'")
        analysis_text.append(
            "These are this filing's own totals for its coverage period - use the aggregate "
            "tables below (or the raw itemizations) for a breakdown of what makes them up."
        )

    if itemizations:
        analysis_text.append("\n=== ITEMIZATION SCHEDULES IN THIS FILING ===")
        analysis_text.append(f"SCHEDULES PRESENT: {', '.join(sorted(itemizations.keys()))}")
        analysis_text.append("THRESHOLD: contributions/expenditures $200+ must be itemized")
        if "Schedule A" in itemizations:
            analysis_text.append(
                "Schedule A (contributions received) - contributor_organization_name OR "
                "contributor_last_name/contributor_first_name; contribution_amount; "
                "contributor_city/contributor_state; contribution_date"
            )
        if "Schedule B" in itemizations:
            analysis_text.append(
                "Schedule B (disbursements made) - payee_organization_name OR "
                "payee_last_name/payee_first_name; expenditure_amount; "
                "expenditure_purpose_descrip; expenditure_date"
            )
        if "Schedule E" in itemizations:
            analysis_text.append(
                "Schedule E (independent expenditures) - payee_organization_name; "
                "expenditure_amount; support_oppose_code ('S'=support/'O'=oppose); "
                "candidate_last_name/candidate_first_name; disbursement_date"
            )
        if "Schedule C" in itemizations:
            analysis_text.append("Schedule C (loans received)")
        if "Schedule D" in itemizations:
            analysis_text.append("Schedule D (debts and obligations)")
        analysis_text.append(
            "For exact-match filters (e.g. 'contributions from California'), match "
            "contributor_state/candidate_state exactly."
        )

    analysis_text.append("\n=== DATA QUALITY NOTES ===")
    analysis_text.append("MISSING DATA: fields may be empty/absent - treat as 'Not Available'")
    analysis_text.append("COMMITTEE ID FORMAT: usually C followed by 8 digits")

    raw_payload, truncation_notes = _build_raw_payload(filing_data, variant)

    if has_financial_summary or itemizations:
        analysis_text.append("\n" + "=" * 60)
        analysis_text.append("AGGREGATE TABLES (computed over the complete filing)")
        analysis_text.append("=" * 60)
        analysis_text.append(analysis.build_aggregate_tables(filing_info, itemizations))

    if truncation_notes:
        analysis_text.append("=== RAW DATA TRUNCATION NOTES ===")
        analysis_text.extend(truncation_notes)
        analysis_text.append("")

    if raw_payload is not None:
        analysis_text.append("=" * 60)
        analysis_text.append("RAW FILING DATA")
        analysis_text.append("=" * 60)
        analysis_text.append(json.dumps(raw_payload, default=str, separators=(",", ":")))

    source = f"https://docquery.fec.gov/dcdev/posted/{filing_id}.fec"
    return llm.Fragment("\n".join(analysis_text), source)
