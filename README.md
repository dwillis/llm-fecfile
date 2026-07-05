
<div align="center">
  <img src="https://github.com/dwillis/llm-fecfile/raw/main/logo.svg" alt="" width=240>
  <p><strong>A plugin for the Python llm library that assists in analyzing federal campaign finance filings.</strong></p>

[![PyPI](https://img.shields.io/pypi/v/llm-fecfile.svg)](https://pypi.org/project/llm-fecfile/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/dwillis/llm-fecfile/blob/main/LICENSE)

</div>

llm-fecfile is an [LLM](https://llm.datasette.io/) plugin for analyzing FEC (Federal Election Commission) campaign finance filings. It gives you three ways to work with FEC data from the `llm` command-line tool:

- **Fragments** (`-f fec:...`) load a whole filing - or a scoped slice of one - into the prompt, along with instructions and precomputed aggregate tables to help the model reason about it accurately.
- **Tools** (`--tool FEC`) let the model fetch specific facts (top donors, contributions from a state, a committee's recent filings) on demand, without loading an entire filing into context.
- **CLI commands** (`llm fec search`, `llm fec filings`) help you find committee IDs and filing IDs from the FEC's public API.

## Installation

Install this plugin in the same environment as LLM:

```bash
llm install llm-fecfile
```

## Fragments

The plugin registers a fragment loader with the `fec:` prefix.

```bash
# Load and analyze a specific FEC filing by ID
llm -f fec:1896830 "What are the key financial aspects of this filing?"

llm -f fec:1896830 "Who are the largest contributors?"

llm -f fec:1896830 "What are the biggest expenditures and what were they for?"
```

### What the fragment contains

For a filing ID like `fec:1896830`, the fragment includes:

1. Response style and form-type-specific analysis instructions
2. **Precomputed aggregate tables** - filing summary, top 20 contributions/disbursements, contribution totals by state, and disbursement totals by purpose, all computed over the *entire* filing (not just whatever subset is included in the raw dump below)
3. The raw filing data as JSON, for record-level lookups

Different form types get different guidance:

- **F1/F1M**: Statement of Organization (committee registration)
- **F2**: Statement of Candidacy
- **F99**: Miscellaneous text filings
- **Everything else** (F3/F3P/F3X periodic reports, F24/F5/F6/F7/F9 specialized notices, etc.): financial/itemization guidance, based on what fields and schedules are actually present in that specific filing

Amendment status (Original / Amendment / Termination) is derived from the trailing letter on the filing's `form_type` (e.g. `F3XN`, `F3A`, `F1T`). The parsed filing data itself has no field linking an amendment back to the filing it amends - for that, use `fec:committee:<id>` below or check FEC.gov.

### Fragment variants

Large filings (a national party committee's monthly report can have tens of thousands of itemized transactions) can blow past a model's context window. By default, the raw data section caps each schedule to its 200 highest-amount itemizations and says so explicitly - the aggregate tables above it are still computed over the complete dataset. You can control this with a suffix on the filing ID:

```bash
# Default: instructions + full aggregates + up to 200 raw itemizations per schedule
llm -f fec:1896830 "..."

# Instructions + aggregates only, no raw itemizations at all (smallest fragment)
llm -f fec:1896830/summary "What's the overall financial picture?"

# One schedule's itemizations, uncapped
llm -f fec:1896830/sa "List every contribution over $2,000"
llm -f fec:1896830/sb "..."
llm -f fec:1896830/se "..."

# Everything, uncapped - only for filings you know are small
llm -f fec:1896830/full "..."
```

### Committee fragments

```bash
llm -f fec:committee:C00089482 "Which of this committee's recent filings had the most spending?"
```

This loads a table of the committee's recent filings (form type, coverage dates, receipts/disbursements) without loading any itemized transactions, so a model can help you pick which specific filing ID to load next.

### Multi-filing analysis

```bash
llm -f fec:1896830 -f fec:1893645 "Compare the fundraising performance between these two filings"
```

## Tools

For large filings, or when you just need one specific fact, use the `FEC` toolbox instead of loading a whole fragment:

```bash
llm --tool FEC "Who are the top 5 donors in FEC filing 1896830?"
llm --tool FEC "How much did filing 1896830 raise from California?"
llm --tool FEC "Find the FEC committee ID for Emily's List and show its recent filings"
```

Available tools: `filing_summary`, `top_contributions`, `top_disbursements`, `contributions_from_state`, `contributions_over`, `disbursements_by_purpose`, `schedule_counts`, `search_committees`, `committee_filings`.

**Fragments vs. tools:** use a fragment when you want the model to reason over the whole filing (or a whole schedule) in context. Use tools when the filing is huge, you only need a targeted answer, or you're comparing/searching across multiple filings or committees.

## CLI commands

Find committee and filing IDs without leaving the terminal:

```bash
llm fec search "harris for president"
llm fec filings C00703975 --limit 10
llm fec filings C00703975 --form F3X
```

These use the [FEC API](https://api.open.fec.gov/developers/). By default they use the shared `DEMO_KEY`, which has a low rate limit. For regular use, get a free key at <https://api.data.gov/signup/> and set it with:

```bash
llm keys set fec
```

(or set the `FEC_API_KEY` environment variable).

## Caching

Filings are immutable once posted - an amendment gets its own filing ID - so once a filing is fetched it's cached on disk (under `llm`'s user directory) and never re-downloaded.

## Finding filing IDs

1. **FEC Website**: Visit [fec.gov](https://www.fec.gov) and search for a committee
2. **`llm fec search`** / **`llm fec filings`**: see CLI commands above
3. **Direct URLs**: Filing IDs appear in URLs like `https://docquery.fec.gov/dcdev/posted/1690664.fec`

## Understanding FEC filings

- **Schedule A**: Individual contributions received (itemized contributions $200+)
- **Schedule B**: Disbursements and expenditures (itemized expenditures $200+)
- **Schedule C**: Loans received
- **Schedule D**: Debts and obligations
- **Schedule E**: Independent expenditures

## Limitations

- **Filing Availability**: Not all filings may be immediately available through the FEC's API
- **Network Dependency**: Requires an internet connection to fetch filing and committee data (first fetch of a given filing only - see Caching above)
- **Large Filings**: Very large filings are capped by default in fragments (see Fragment variants above) - use `/full` or the tools/CLI interfaces if you need everything

## Development

```bash
git clone https://github.com/dwillis/llm-fecfile
cd llm-fecfile
pip install -e '.[test]'
```

### Running tests

```bash
pytest
```

## Dependencies

This plugin requires Python 3.9 or greater, and depends on:

- [llm](https://llm.datasette.io/): The LLM command-line tool, fragments, and tools system
- [fecfile](https://github.com/esonderegger/fecfile): Python library for parsing FEC filings
- [tabulate](https://github.com/astanin/python-tabulate): table formatting
- [requests](https://requests.readthedocs.io/): HTTP client, used for the FEC API commands/tools

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

When contributing:
1. Ensure tests pass with `pytest`
2. Follow the existing code style
3. Update documentation for any new features

## Acknowledgments

- Built on the excellent [fecfile](https://github.com/esonderegger/fecfile) library by Evan Sonderegger
- Inspired by the [LLM](https://llm.datasette.io/) tool by Simon Willison
- Uses data from the Federal Election Commission
