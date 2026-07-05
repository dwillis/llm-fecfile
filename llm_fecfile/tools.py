import json

import llm

from . import analysis, fec_api
from .cache import get_filing


def _load(filing_id):
    filing_data = get_filing(filing_id)
    if filing_data is None:
        raise ValueError(f"FEC filing {filing_id} was not found.")
    return filing_data


class FEC(llm.Toolbox):
    "Tools for looking up and analyzing FEC campaign finance filings"

    def filing_summary(self, filing_id: str) -> str:
        "Get the summary (committee, form type, coverage period, totals, amendment status) for an FEC filing"
        filing_data = _load(filing_id)
        filing_info = filing_data.get("filing", {})
        form_type = filing_info.get("form_type", "")
        return json.dumps(
            {
                "filing_id": filing_id,
                "form_type": form_type,
                "status": analysis.filing_status_label(form_type),
                "committee_id": analysis.committee_id(filing_info),
                "committee_name": filing_info.get("committee_name"),
                "coverage_from_date": analysis.format_date(filing_info.get("coverage_from_date")),
                "coverage_through_date": analysis.format_date(
                    filing_info.get("coverage_through_date")
                ),
                "total_receipts": filing_info.get("col_a_total_receipts"),
                "total_disbursements": filing_info.get("col_a_total_disbursements"),
                "cash_on_hand_close": filing_info.get("col_a_cash_on_hand_close_of_period"),
            }
        )

    def top_contributions(self, filing_id: str, n: int = 10) -> str:
        "Get the top N individual contributions (Schedule A) from an FEC filing, sorted by amount"
        filing_data = _load(filing_id)
        contributions = filing_data.get("itemizations", {}).get("Schedule A", [])
        sorted_contribs = sorted(
            contributions, key=lambda x: x.get("contribution_amount", 0) or 0, reverse=True
        )[:n]
        return json.dumps(
            [
                {
                    "contributor": analysis.contributor_name(c),
                    "amount": c.get("contribution_amount"),
                    "city": c.get("contributor_city"),
                    "state": c.get("contributor_state"),
                    "date": analysis.format_date(c.get("contribution_date")),
                }
                for c in sorted_contribs
            ]
        )

    def top_disbursements(self, filing_id: str, n: int = 10) -> str:
        "Get the top N disbursements (Schedule B) from an FEC filing, sorted by amount"
        filing_data = _load(filing_id)
        disbursements = filing_data.get("itemizations", {}).get("Schedule B", [])
        sorted_disb = sorted(
            disbursements, key=lambda x: x.get("expenditure_amount", 0) or 0, reverse=True
        )[:n]
        return json.dumps(
            [
                {
                    "recipient": analysis.payee_name(d),
                    "amount": d.get("expenditure_amount"),
                    "purpose": d.get("expenditure_purpose_descrip"),
                    "date": analysis.format_date(d.get("expenditure_date")),
                }
                for d in sorted_disb
            ]
        )

    def contributions_from_state(self, filing_id: str, state: str) -> str:
        "Get all Schedule A contributions from a specific two-letter state code in an FEC filing"
        filing_data = _load(filing_id)
        contributions = filing_data.get("itemizations", {}).get("Schedule A", [])
        matches = [c for c in contributions if (c.get("contributor_state") or "").upper() == state.upper()]
        return json.dumps(
            {
                "state": state.upper(),
                "count": len(matches),
                "total": sum(c.get("contribution_amount", 0) or 0 for c in matches),
                "contributions": [
                    {
                        "contributor": analysis.contributor_name(c),
                        "amount": c.get("contribution_amount"),
                        "city": c.get("contributor_city"),
                        "date": analysis.format_date(c.get("contribution_date")),
                    }
                    for c in matches
                ],
            }
        )

    def contributions_over(self, filing_id: str, amount: float) -> str:
        "Get all Schedule A contributions over a given dollar amount in an FEC filing"
        filing_data = _load(filing_id)
        contributions = filing_data.get("itemizations", {}).get("Schedule A", [])
        matches = [c for c in contributions if (c.get("contribution_amount", 0) or 0) > amount]
        return json.dumps(
            [
                {
                    "contributor": analysis.contributor_name(c),
                    "amount": c.get("contribution_amount"),
                    "state": c.get("contributor_state"),
                    "date": analysis.format_date(c.get("contribution_date")),
                }
                for c in sorted(matches, key=lambda x: x.get("contribution_amount", 0) or 0, reverse=True)
            ]
        )

    def disbursements_by_purpose(self, filing_id: str, keyword: str) -> str:
        "Get all Schedule B disbursements whose purpose description contains a keyword (case-insensitive)"
        filing_data = _load(filing_id)
        disbursements = filing_data.get("itemizations", {}).get("Schedule B", [])
        keyword_lower = keyword.lower()
        matches = [
            d
            for d in disbursements
            if keyword_lower in (d.get("expenditure_purpose_descrip") or "").lower()
        ]
        return json.dumps(
            {
                "keyword": keyword,
                "count": len(matches),
                "total": sum(d.get("expenditure_amount", 0) or 0 for d in matches),
                "disbursements": [
                    {
                        "recipient": analysis.payee_name(d),
                        "amount": d.get("expenditure_amount"),
                        "purpose": d.get("expenditure_purpose_descrip"),
                        "date": analysis.format_date(d.get("expenditure_date")),
                    }
                    for d in matches
                ],
            }
        )

    def schedule_counts(self, filing_id: str) -> str:
        "Get the number of itemizations per schedule (A, B, C, D, E, etc.) in an FEC filing"
        filing_data = _load(filing_id)
        itemizations = filing_data.get("itemizations", {})
        return json.dumps({schedule: len(items) for schedule, items in itemizations.items()})

    def search_committees(self, query: str, limit: int = 10) -> str:
        "Search for FEC committees by name and return their committee IDs"
        return json.dumps(fec_api.search_committees(query, limit=limit))

    def committee_filings(self, committee_id: str, form_type: str = "", limit: int = 10) -> str:
        "List recent filings for a committee ID, optionally filtered by form type (e.g. F3X). Pass an empty string for form_type to see all forms"
        return json.dumps(
            fec_api.committee_filings(committee_id, form_type=form_type or None, limit=limit)
        )
