from unittest.mock import patch

import pytest
import requests

from llm_fecfile import cache


@pytest.fixture
def isolated_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_cache_dir", lambda: tmp_path)
    return tmp_path


def test_get_filing_returns_none_when_not_found(isolated_cache_dir):
    with patch("fecfile.from_http", return_value=None) as mock_from_http:
        assert cache.get_filing("1234567") is None
        mock_from_http.assert_called_once_with(1234567)


def test_get_filing_writes_and_reads_cache(isolated_cache_dir):
    filing_data = {"filing": {"committee_name": "Test"}}
    with patch("fecfile.from_http", return_value=filing_data) as mock_from_http:
        result = cache.get_filing("1234567")
        assert result == filing_data
        assert (isolated_cache_dir / "1234567.json").exists()

    # second call must not hit the network again
    with patch("fecfile.from_http") as mock_from_http2:
        result2 = cache.get_filing("1234567")
        assert result2 == filing_data
        mock_from_http2.assert_not_called()


def test_get_filing_wraps_network_errors(isolated_cache_dir):
    with patch("fecfile.from_http", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(ValueError, match="Network error"):
            cache.get_filing("1234567")


def test_get_filing_wraps_parse_errors(isolated_cache_dir):
    with patch("fecfile.from_http", side_effect=IndexError("list index out of range")):
        with pytest.raises(ValueError, match="could not be parsed"):
            cache.get_filing("1234567")
