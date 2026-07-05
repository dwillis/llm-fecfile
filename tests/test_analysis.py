from llm_fecfile import analysis


def test_parse_form_type_new():
    assert analysis.parse_form_type("F3XN") == ("F3X", "N")


def test_parse_form_type_amendment():
    assert analysis.parse_form_type("F3A") == ("F3", "A")


def test_parse_form_type_termination():
    assert analysis.parse_form_type("F1T") == ("F1", "T")


def test_parse_form_type_no_suffix_scheme():
    assert analysis.parse_form_type("F99") == ("F99", None)


def test_parse_form_type_unrecognized_base():
    assert analysis.parse_form_type("XYZ") == ("XYZ", None)


def test_filing_status_label_amendment():
    assert analysis.filing_status_label("F3A") == "Amendment"


def test_filing_status_label_termination():
    assert analysis.filing_status_label("F1T") == "Termination"


def test_filing_status_label_original():
    assert analysis.filing_status_label("F3XN") == "Original Filing"


def test_filing_status_label_f99_defaults_original():
    assert analysis.filing_status_label("F99") == "Original Filing"


def test_committee_id_uses_filer_committee_id_number():
    assert analysis.committee_id({"filer_committee_id_number": "C00089482"}) == "C00089482"


def test_committee_id_falls_back_to_committee_id_number():
    assert analysis.committee_id({"committee_id_number": "C00919111"}) == "C00919111"


def test_contributor_name_prefers_organization():
    contrib = {"contributor_organization_name": "Acme Corp", "contributor_last_name": "Doe"}
    assert analysis.contributor_name(contrib) == "Acme Corp"


def test_contributor_name_falls_back_to_person():
    contrib = {"contributor_last_name": "Doe", "contributor_first_name": "Jane"}
    assert analysis.contributor_name(contrib) == "Doe, Jane"


def test_payee_name_prefers_organization():
    item = {"payee_organization_name": "Ad Agency"}
    assert analysis.payee_name(item) == "Ad Agency"


def test_format_date_strips_time_portion():
    assert analysis.format_date("2025-05-01 00:00:00-04:00") == "2025-05-01"


def test_format_date_handles_plain_date_string():
    assert analysis.format_date("2025-05-01") == "2025-05-01"


def test_format_date_none_returns_none():
    assert analysis.format_date(None) is None


def test_calculate_coverage_days():
    assert analysis.calculate_coverage_days("2025-05-01", "2025-05-31") == 31


def test_calculate_coverage_days_missing_returns_none():
    assert analysis.calculate_coverage_days(None, "2025-05-31") is None


def test_build_aggregate_tables_includes_summary(f3x_filing):
    output = analysis.build_aggregate_tables(
        f3x_filing["filing"], f3x_filing["itemizations"]
    )
    assert "UTAH REPUBLICAN PARTY" in output
    assert "C00089482" in output
    assert "TOP 20 CONTRIBUTIONS" in output
    assert "TOP 20 DISBURSEMENTS" in output
    assert "CONTRIBUTION TOTALS BY STATE" in output


def test_build_aggregate_tables_schedule_e(f24_filing):
    output = analysis.build_aggregate_tables(f24_filing["filing"], f24_filing["itemizations"])
    assert "INDEPENDENT EXPENDITURES" in output
    assert "TKO Buying LLC" in output
