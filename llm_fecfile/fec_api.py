import llm
import requests
from tabulate import tabulate

API_BASE = "https://api.open.fec.gov/v1"


def get_api_key():
    return llm.get_key(alias="fec", env="FEC_API_KEY") or "DEMO_KEY"


def _get(path, params):
    params = dict(params)
    params["api_key"] = get_api_key()
    response = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
    if response.status_code == 429:
        raise ValueError(
            "FEC API rate limit exceeded. Set a personal key with "
            "'llm keys set fec' (get one at https://api.data.gov/signup/) - "
            "the shared DEMO_KEY has a low limit."
        )
    response.raise_for_status()
    return response.json()


def search_committees(query, limit=10):
    """Search for committees by name. Returns a list of dicts with
    committee_id, name, committee_type_full, and state."""
    data = _get("/committees/", {"q": query, "per_page": limit})
    return [
        {
            "committee_id": r.get("committee_id"),
            "name": r.get("name"),
            "committee_type_full": r.get("committee_type_full"),
            "state": r.get("state"),
        }
        for r in data.get("results", [])
    ]


def committee_filings(committee_id, form_type=None, limit=10):
    """List recent filings for a committee. Returns a list of dicts with
    file_number, form_type, coverage_start_date, coverage_end_date,
    total_receipts, total_disbursements."""
    params = {"per_page": limit, "sort": "-receipt_date"}
    if form_type:
        params["form_type"] = form_type
    data = _get(f"/committee/{committee_id}/filings/", params)
    return [
        {
            "file_number": r.get("file_number"),
            "form_type": r.get("form_type"),
            "coverage_start_date": r.get("coverage_start_date"),
            "coverage_end_date": r.get("coverage_end_date"),
            "total_receipts": r.get("total_receipts"),
            "total_disbursements": r.get("total_disbursements"),
        }
        for r in data.get("results", [])
    ]


def committee_fragment_text(committee_id):
    """Build fragment text listing a committee's recent filings, so a model
    can help pick which filing_id to load in full."""
    filings = committee_filings(committee_id, limit=20)
    lines = [
        f"=== RECENT FILINGS FOR COMMITTEE {committee_id} ===",
        "This lists filing metadata only, not itemized transactions. To analyze "
        "a specific filing's contributions/disbursements, load it with "
        "fec:<file_number>.",
        "",
    ]
    if not filings:
        lines.append("No filings found for this committee ID.")
        return "\n".join(lines)

    rows = [
        [
            f.get("file_number"),
            f.get("form_type"),
            f.get("coverage_start_date") or "",
            f.get("coverage_end_date") or "",
            f"${f.get('total_receipts'):,.2f}" if f.get("total_receipts") is not None else "",
            f"${f.get('total_disbursements'):,.2f}"
            if f.get("total_disbursements") is not None
            else "",
        ]
        for f in filings
    ]
    headers = ["File #", "Form", "Coverage Start", "Coverage End", "Receipts", "Disbursements"]
    lines.append(tabulate(rows, headers=headers, tablefmt="simple", numalign="right"))
    return "\n".join(lines)


def register_cli_commands(cli):
    import click

    @cli.group()
    def fec():
        "Commands for searching FEC committees and filings"

    @fec.command(name="search")
    @click.argument("query")
    @click.option("--limit", default=10, help="Number of results to return")
    def search(query, limit):
        "Search for FEC committees by name"
        try:
            results = search_committees(query, limit=limit)
        except ValueError as e:
            raise click.ClickException(str(e))
        if not results:
            click.echo("No committees found.")
            return
        rows = [[r["committee_id"], r["name"], r["committee_type_full"], r["state"]] for r in results]
        click.echo(tabulate(rows, headers=["Committee ID", "Name", "Type", "State"], tablefmt="simple"))

    @fec.command(name="filings")
    @click.argument("committee_id")
    @click.option("--form", "form_type", default=None, help="Filter by form type, e.g. F3X")
    @click.option("--limit", default=10, help="Number of results to return")
    def filings(committee_id, form_type, limit):
        "List recent filings for a committee ID"
        try:
            results = committee_filings(committee_id, form_type=form_type, limit=limit)
        except ValueError as e:
            raise click.ClickException(str(e))
        if not results:
            click.echo("No filings found.")
            return
        rows = [
            [
                r["file_number"],
                r["form_type"],
                r["coverage_start_date"] or "",
                r["coverage_end_date"] or "",
                r["total_receipts"],
                r["total_disbursements"],
            ]
            for r in results
        ]
        click.echo(
            tabulate(
                rows,
                headers=["File #", "Form", "Coverage Start", "Coverage End", "Receipts", "Disbursements"],
                tablefmt="simple",
                numalign="right",
            )
        )
