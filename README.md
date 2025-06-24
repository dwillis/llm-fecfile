
<div align="center">
  <img src="https://github.com/dwillis/llm-fecfile/raw/main/logo.svg" alt="" width=240>
  <p><strong>A plugin for the Python llm library that assists in analyzing federal campaign finance filings.</strong></p>

[![PyPI](https://img.shields.io/pypi/v/llm-fecfile.svg)](https://pypi.org/project/llm-fecfile/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/user/llm-fecfile/blob/main/LICENSE)

</div>

llm-fecfile is an [LLM](https://llm.datasette.io/) plugin for analyzing FEC (Federal Election Commission) campaign finance filings. This plugin allows you to load FEC filings as fragments and analyze them using natural language through the LLM command-line tool.

## Installation

Install this plugin in the same environment as LLM:

```bash
llm install llm-fecfile
```

## Usage

The plugin provides a fragment loader with the `fec:` prefix that loads FEC campaign finance filings and provides structured analysis instructions to help you understand the data.

### Basic Usage

```bash
# Load and analyze a specific FEC filing by ID
llm -f fec:1896830 "What are the key financial aspects of this filing?"

# Ask about specific aspects of the filing
llm -f fec:1896830 "Who are the largest contributors?"

# Get an overview of spending patterns
llm -f fec:1896830 "What are the biggest expenditures and what were they for?"
```

### What the Fragment Provides

When you use `-f fec:FILING_ID`, the plugin:

1. **Loads the complete FEC filing** using the `fecfile` library
2. **Provides response style instructions** to ensure clear, readable analysis
3. **Includes form-specific guidance** based on the filing type (F1, F2, F3, F99, etc.)
4. **Offers detailed field mapping** for contributions, disbursements, and other itemizations
5. **Includes the complete raw filing data** in JSON format for comprehensive analysis

The fragment includes specialized instructions for different form types:

- **F1/F1A**: Committee registration and organizational details
- **F2/F2A**: Candidate declarations and information
- **F3/F3P/F3X**: Financial reports with receipts, disbursements, and itemizations
- **F99**: Miscellaneous text filings

### Example Queries

Once you've loaded a filing as a fragment, you can ask various questions:

#### Financial Analysis
```bash
llm -f fec:1896830 "What's the total amount raised and spent in this reporting period?"
llm -f fec:1896830 "What's the cash on hand at the end of this period?"
llm -f fec:1896830 "Is this an amendment? If so, what filing does it amend?"
```

#### Contribution Analysis
```bash
llm -f fec:1896830 "Who are the top 10 individual contributors?"
llm -f fec:1896830 "What contributions came from California?"
llm -f fec:1896830 "Show me all contributions over $2,000"
```

#### Expenditure Analysis
```bash
llm -f fec:1896830 "What are the largest expenditures?"
llm -f fec:1896830 "How much was spent on advertising?"
llm -f fec:1896830 "Who received the most money from this committee?"
llm -f fec:1896830 "What types of expenses are listed?"
```

#### Time-based Analysis
```bash
llm -f fec:1896830 "How many days does this filing cover?"
llm -f fec:1896830 "What was the average daily fundraising rate?"
```

## Understanding FEC Filings

The plugin provides guidance for understanding different schedules in FEC filings:

- **Schedule A**: Individual contributions received (itemized contributions $200+)
- **Schedule B**: Disbursements and expenditures (itemized expenditures $200+)
- **Schedule C**: Loans received
- **Schedule D**: Debts and obligations
- **Schedule E**: Independent expenditures

## Finding Filing IDs

You can find FEC filing IDs in several ways:

1. **FEC Website**: Visit [fec.gov](https://www.fec.gov) and search for a committee
2. **Direct URLs**: Filing IDs appear in URLs like `https://docquery.fec.gov/dcdev/posted/1690664.fec`
3. **FEC API**: Use the [FEC API](https://api.open.fec.gov/developers/) to search for filings

## Multi-Filing Analysis

You can load multiple filings to compare them:

```bash
# Compare two different filings
llm -f fec:1896830 -f fec:1893645 "Compare the fundraising performance between these two filings"
```

## Limitations

- **Filing Availability**: Not all filings may be immediately available through the FEC's API
- **Network Dependency**: Requires internet connection to fetch filing data
- **Large Filings**: Very large filings may take time to load and process

## Development

To develop this plugin:

```bash
git clone https://github.com/dwillis/llm-fecfile
cd llm-fecfile
pip install -e .
```

### Running Tests

```bash
python test_plugin.py
```

The test suite includes:
- Filing ID validation tests
- Form type instruction tests
- Fragment creation tests
- Error handling tests
- Manual integration tests with real filings

## Dependencies

This plugin requires Python 3.9 or greater. 

This plugin depends on:
- [llm](https://llm.datasette.io/): The LLM command-line tool and fragment system
- [fecfile](https://github.com/esonderegger/fecfile): Python library for parsing FEC filings

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

When contributing:
1. Ensure tests pass with `python test_plugin.py`
2. Follow the existing code style
3. Update documentation for any new features

## Acknowledgments

- Built on the excellent [fecfile](https://github.com/esonderegger/fecfile) library by Evan Sonderegger
- Inspired by the [LLM](https://llm.datasette.io/) tool and fragments system by Simon Willison
- Uses data from the Federal Election Commission