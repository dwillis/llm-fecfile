from unittest.mock import MagicMock, patch

import pytest

from llm_fecfile import fec_api


def _mock_response(json_data, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return response


def test_get_api_key_defaults_to_demo_key(monkeypatch):
    monkeypatch.setattr("llm.get_key", lambda **kwargs: None)
    assert fec_api.get_api_key() == "DEMO_KEY"


def test_get_api_key_uses_llm_key_when_set(monkeypatch):
    monkeypatch.setattr("llm.get_key", lambda **kwargs: "my-real-key")
    assert fec_api.get_api_key() == "my-real-key"


def test_search_committees(monkeypatch):
    monkeypatch.setattr(fec_api, "get_api_key", lambda: "DEMO_KEY")
    response = _mock_response(
        {
            "results": [
                {
                    "committee_id": "C00089482",
                    "name": "UTAH REPUBLICAN PARTY",
                    "committee_type_full": "Party - Qualified",
                    "state": "UT",
                }
            ]
        }
    )
    with patch("requests.get", return_value=response) as mock_get:
        results = fec_api.search_committees("utah republican", limit=5)
        assert results == [
            {
                "committee_id": "C00089482",
                "name": "UTAH REPUBLICAN PARTY",
                "committee_type_full": "Party - Qualified",
                "state": "UT",
            }
        ]
        assert mock_get.call_args.kwargs["params"]["q"] == "utah republican"
        assert mock_get.call_args.kwargs["params"]["per_page"] == 5


def test_committee_filings(monkeypatch):
    monkeypatch.setattr(fec_api, "get_api_key", lambda: "DEMO_KEY")
    response = _mock_response(
        {
            "results": [
                {
                    "file_number": 1896830,
                    "form_type": "F3X",
                    "coverage_start_date": "2025-05-01",
                    "coverage_end_date": "2025-05-31",
                    "total_receipts": 42655.80,
                    "total_disbursements": 21283.49,
                }
            ]
        }
    )
    with patch("requests.get", return_value=response):
        results = fec_api.committee_filings("C00089482", form_type="F3X")
        assert results[0]["file_number"] == 1896830


def test_rate_limit_raises_clear_error(monkeypatch):
    monkeypatch.setattr(fec_api, "get_api_key", lambda: "DEMO_KEY")
    response = _mock_response({}, status_code=429)
    with patch("requests.get", return_value=response):
        with pytest.raises(ValueError, match="rate limit"):
            fec_api.search_committees("anything")


def test_committee_fragment_text_lists_filings(monkeypatch):
    monkeypatch.setattr(
        fec_api,
        "committee_filings",
        lambda committee_id, limit=20: [
            {
                "file_number": 1896830,
                "form_type": "F3X",
                "coverage_start_date": "2025-05-01",
                "coverage_end_date": "2025-05-31",
                "total_receipts": 42655.80,
                "total_disbursements": 21283.49,
            }
        ],
    )
    text = fec_api.committee_fragment_text("C00089482")
    assert "C00089482" in text
    assert "1896830" in text


def test_committee_fragment_text_handles_no_filings(monkeypatch):
    monkeypatch.setattr(fec_api, "committee_filings", lambda committee_id, limit=20: [])
    text = fec_api.committee_fragment_text("C00000000")
    assert "No filings found" in text
