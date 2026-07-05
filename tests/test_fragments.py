import json

import pytest

from llm_fecfile import fragments


def test_parse_argument_plain_id():
    assert fragments.parse_argument("1234567") == ("1234567", None)


def test_parse_argument_with_variant():
    assert fragments.parse_argument("1234567/summary") == ("1234567", "summary")


def test_parse_argument_rejects_non_numeric():
    with pytest.raises(ValueError, match="Invalid filing ID"):
        fragments.parse_argument("invalid")


def test_parse_argument_rejects_negative():
    with pytest.raises(ValueError, match="Invalid filing ID"):
        fragments.parse_argument("-123")


def test_parse_argument_rejects_zero():
    with pytest.raises(ValueError, match="Invalid filing ID"):
        fragments.parse_argument("0")


def test_parse_argument_rejects_unknown_variant():
    with pytest.raises(ValueError, match="Invalid fragment variant"):
        fragments.parse_argument("1234567/bogus")


def _fragment_raw_payload(fragment_text):
    marker = "=" * 60 + "\nRAW FILING DATA\n" + "=" * 60 + "\n"
    idx = fragment_text.find(marker)
    assert idx != -1, "RAW FILING DATA section not found"
    return json.loads(fragment_text[idx + len(marker) :])


@pytest.fixture(autouse=True)
def patch_get_filing(monkeypatch):
    """Route fragments.get_filing to fixture data keyed by filing_id string."""
    store = {}

    def fake_get_filing(filing_id):
        return store.get(filing_id)

    monkeypatch.setattr(fragments, "get_filing", fake_get_filing)
    return store


def test_fragment_not_found_raises(patch_get_filing):
    with pytest.raises(ValueError, match="was not found"):
        fragments.fec_fragment_loader("9999999")


def test_fragment_source_is_docquery_url(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    frag = fragments.fec_fragment_loader("1234567")
    assert frag.source == "https://docquery.fec.gov/dcdev/posted/1234567.fec"


def test_financial_filing_includes_aggregates_and_raw_data(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    frag = str(fragments.fec_fragment_loader("1234567"))
    assert "FINANCIAL SUMMARY COLUMNS" in frag
    assert "AGGREGATE TABLES" in frag
    assert "RAW FILING DATA" in frag
    payload = _fragment_raw_payload(frag)
    assert len(payload["itemizations"]["Schedule A"]) == 2


def test_summary_variant_omits_raw_data(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    frag = str(fragments.fec_fragment_loader("1234567/summary"))
    assert "AGGREGATE TABLES" in frag
    assert "RAW FILING DATA" not in frag


def test_full_variant_is_uncapped(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    frag = str(fragments.fec_fragment_loader("1234567/full"))
    payload = _fragment_raw_payload(frag)
    assert len(payload["itemizations"]["Schedule A"]) == 2
    assert "header" in payload


def test_schedule_variant_returns_only_that_schedule(patch_get_filing, f3x_filing):
    patch_get_filing["1234567"] = f3x_filing
    frag = str(fragments.fec_fragment_loader("1234567/sa"))
    payload = _fragment_raw_payload(frag)
    assert list(payload["itemizations"].keys()) == ["Schedule A"]
    assert len(payload["itemizations"]["Schedule A"]) == 2


def test_default_raw_data_caps_large_schedules(patch_get_filing, f3x_filing):
    big_contribs = [
        {
            "contributor_last_name": f"Person{i}",
            "contribution_amount": float(i),
            "contributor_state": "MD",
        }
        for i in range(fragments.MAX_ITEMS_PER_SCHEDULE + 50)
    ]
    f3x_filing["itemizations"]["Schedule A"] = big_contribs
    patch_get_filing["1234567"] = f3x_filing

    frag = str(fragments.fec_fragment_loader("1234567"))
    payload = _fragment_raw_payload(frag)
    assert len(payload["itemizations"]["Schedule A"]) == fragments.MAX_ITEMS_PER_SCHEDULE
    assert "RAW DATA TRUNCATION NOTES" in frag
    assert f"showing {fragments.MAX_ITEMS_PER_SCHEDULE} of {len(big_contribs):,}" in frag
    # highest-amount items are kept
    kept_amounts = {c["contribution_amount"] for c in payload["itemizations"]["Schedule A"]}
    assert max(c["contribution_amount"] for c in big_contribs) in kept_amounts
    assert 0.0 not in kept_amounts


def test_f1_filing_gets_organization_guidance(patch_get_filing, f1_filing):
    patch_get_filing["1234567"] = f1_filing
    frag = str(fragments.fec_fragment_loader("1234567"))
    assert "Statement of Organization" in frag
    assert "treasurer_first_name / treasurer_last_name" in frag
    assert "FINANCIAL SUMMARY COLUMNS" not in frag


def test_f2_filing_gets_candidacy_guidance(patch_get_filing, f2_filing):
    patch_get_filing["1234567"] = f2_filing
    frag = str(fragments.fec_fragment_loader("1234567"))
    assert "Statement of Candidacy" in frag
    assert "candidate_office" in frag


def test_f99_filing_gets_misc_text_guidance(patch_get_filing, f99_filing):
    patch_get_filing["1234567"] = f99_filing
    frag = str(fragments.fec_fragment_loader("1234567"))
    assert "Miscellaneous text communication" in frag
    assert "FINANCIAL SUMMARY COLUMNS" not in frag


def test_f24_filing_gets_schedule_e_guidance(patch_get_filing, f24_filing):
    patch_get_filing["1234567"] = f24_filing
    frag = str(fragments.fec_fragment_loader("1234567"))
    assert "Schedule E (independent expenditures)" in frag
    assert "FINANCIAL SUMMARY COLUMNS" not in frag
    assert "AGGREGATE TABLES" in frag


def test_amendment_status_reflected_in_fragment(patch_get_filing, f2_filing):
    patch_get_filing["1234567"] = f2_filing
    frag = str(fragments.fec_fragment_loader("1234567"))
    assert "STATUS: Amendment" in frag


def test_committee_fragment_delegates_to_fec_api(monkeypatch, patch_get_filing):
    monkeypatch.setattr(
        fragments.fec_api, "committee_fragment_text", lambda cid: f"filings for {cid}"
    )
    frag = fragments.fec_fragment_loader("committee:C00089482")
    assert str(frag) == "filings for C00089482"
    assert frag.source == "fec:committee:C00089482"
