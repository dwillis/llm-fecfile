import json
import pathlib

import fecfile
import llm
import requests


def _cache_dir():
    path = llm.user_dir() / "fecfile"
    path.mkdir(exist_ok=True, parents=True)
    return path


def get_filing(filing_id):
    """Fetch a parsed FEC filing by numeric ID, using an on-disk cache.

    Filings are immutable once posted (an amendment gets its own filing ID),
    so a cache hit is valid forever. Returns None if the filing does not
    exist (matches fecfile.from_http's own not-found behavior).
    """
    cache_path = _cache_dir() / f"{filing_id}.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    try:
        filing_data = fecfile.from_http(int(filing_id))
    except requests.RequestException as e:
        raise ValueError(f"Network error fetching FEC filing {filing_id}: {e}") from e
    except Exception as e:
        raise ValueError(
            f"FEC filing {filing_id} could not be parsed. It may not exist, or the "
            f"server returned an unexpected response. ({e})"
        ) from e

    if filing_data is None:
        return None

    with open(cache_path, "w") as f:
        json.dump(filing_data, f, default=str)

    return filing_data
