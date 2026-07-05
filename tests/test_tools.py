import json

import pytest

from llm_fecfile import tools


@pytest.fixture(autouse=True)
def patch_get_filing(monkeypatch):
    store = {}
    monkeypatch.setattr(tools, "get_filing", lambda filing_id: store.get(filing_id))
    return store


def test_filing_summary(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.filing_summary("1234567"))
    assert result["committee_id"] == "C00089482"
    assert result["status"] == "Original Filing"
    assert result["total_receipts"] == 42655.80


def test_filing_summary_not_found_raises(patch_get_filing):
    fec = tools.FEC()
    with pytest.raises(ValueError, match="was not found"):
        fec.filing_summary("9999999")


def test_top_contributions_sorted_by_amount(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.top_contributions("1234567", n=1))
    assert len(result) == 1
    assert result[0]["contributor"] == "Utah State Tax Check Off"
    assert result[0]["amount"] == 11729.0


def test_top_disbursements_sorted_by_amount(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.top_disbursements("1234567", n=1))
    assert result[0]["recipient"] == "Trump National Doral Hotel"


def test_contributions_from_state(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.contributions_from_state("1234567", "va"))
    assert result["count"] == 1
    assert result["contributions"][0]["contributor"] == "Adams, Gregory"


def test_contributions_over_amount(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.contributions_over("1234567", 2000))
    assert len(result) == 1
    assert result[0]["contributor"] == "Utah State Tax Check Off"


def test_disbursements_by_purpose(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.disbursements_by_purpose("1234567", "training"))
    assert result["count"] == 1
    assert result["disbursements"][0]["recipient"] == "Trump National Doral Hotel"


def test_schedule_counts(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    fec = tools.FEC()
    result = json.loads(fec.schedule_counts("1234567"))
    assert result == {"Schedule A": 2, "Schedule B": 2}


def test_search_committees_delegates_to_fec_api(monkeypatch):
    monkeypatch.setattr(
        tools.fec_api,
        "search_committees",
        lambda query, limit: [{"committee_id": "C00089482", "name": query}],
    )
    fec = tools.FEC()
    result = json.loads(fec.search_committees("utah gop"))
    assert result[0]["committee_id"] == "C00089482"


def test_committee_filings_delegates_to_fec_api(monkeypatch):
    captured = {}

    def fake_committee_filings(committee_id, form_type=None, limit=10):
        captured["args"] = (committee_id, form_type, limit)
        return [{"file_number": 123}]

    monkeypatch.setattr(tools.fec_api, "committee_filings", fake_committee_filings)
    fec = tools.FEC()
    result = json.loads(fec.committee_filings("C00089482", form_type="F3X"))
    assert result == [{"file_number": 123}]
    assert captured["args"] == ("C00089482", "F3X", 10)
