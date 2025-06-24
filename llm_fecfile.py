import llm
import fecfile
import json
from typing import Optional
from tabulate import tabulate

@llm.hookimpl
def register_fragment_loaders(register):
    register("fec", fec_fragment_loader)

def fec_fragment_loader(filing_id: str):
    """Load FEC filing information as a fragment"""
    
    try:
        filing_id_int = int(filing_id)
        if filing_id_int <= 0:
            raise ValueError(f"Invalid filing ID '{filing_id}'. Must be a positive number.")
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Invalid filing ID '{filing_id}'. Must be a numeric FEC filing ID.")
        raise
    
    try:
        # Load the FEC filing
        filing_data = fecfile.from_http(filing_id_int)
        
        analysis = []

        analysis.append("=== RESPONSE STYLE INSTRUCTIONS ===")
        analysis.append("When responding about this FEC filing:")
        analysis.append("- Start with your best judgment about whether this filing has unusual aspects (no activity is not unusual)")
        analysis.append("- Avoid excessive use of asterisks or bold text")
        analysis.append("- Write in a simple, direct style")
        analysis.append("- Group related information together in coherent sections")
        analysis.append("- Don't provide a summary at the end")

        analysis.append("=== FEC FILING ANALYSIS INSTRUCTIONS ===")
        
        # Form type guidance
        form_type = filing_data.get('filing', {}).get('form_type', '').upper()
        analysis.append(f"FORM TYPE: {form_type}")
        
        if form_type in ['F1', 'F1A']:
            analysis.append("PURPOSE: Committee registration/organization details (not financial)")
            analysis.append("KEY FIELDS: committee_name, committee_type, treasurer_name, committee_email")
        elif form_type in ['F2', 'F2A']:
            analysis.append("PURPOSE: Candidate declaration (not financial)")
            analysis.append("KEY FIELDS: candidate_name, office, state, district, party, election_year")
        elif form_type == 'F99':
            analysis.append("PURPOSE: Miscellaneous text communications")
            analysis.append("KEY FOCUS: The 'text' field contains the substantive content")
        else:
            analysis.append("PURPOSE: Financial report showing money raised and spent")
            
        # Amendment instructions
        analysis.append("\n=== AMENDMENT DETECTION ===")
        analysis.append("CHECK: 'amendment_indicator' field")
        analysis.append("- 'A' = Standard Amendment")
        analysis.append("- 'T' = Termination Amendment") 
        analysis.append("- Empty/None = Original Filing")
        analysis.append("IF AMENDMENT: Look for 'previous_report_amendment_indicator' for original filing ID")
        
        # Coverage period instructions
        analysis.append("\n=== COVERAGE PERIODS ===")
        analysis.append("USE: 'coverage_from_date' and 'coverage_through_date' fields")
        analysis.append("FORMAT: Usually YYYY-MM-DD, may include time/timezone (ignore time portion)")
        analysis.append("CALCULATE: Days covered = (end_date - start_date) + 1")
        analysis.append("CONTEXT: Quarterly reports ~90 days, Monthly ~30 days, Pre-election varies")
        
        # Financial data instructions
        if not form_type.startswith(('F1', 'F2', 'F99')):
            analysis.append("\n=== FINANCIAL SUMMARY COLUMNS ===")
            analysis.append("RECEIPTS: Use 'col_a_total_receipts' (Column A totals)")
            analysis.append("DISBURSEMENTS: Use 'col_a_total_disbursements'")
            analysis.append("CASH ON HAND: Use 'col_a_cash_on_hand_close_of_period' (ending balance)")
            analysis.append("DEBTS: Use 'col_a_debts_to' and 'col_a_debts_by' if present")
            
            # Itemization instructions
            analysis.append("\n=== ITEMIZATION SCHEDULES ===")
            analysis.append("SCHEDULE A: Individual contributions received")
            analysis.append("- Contributor names: Use 'contributor_organization_name' OR 'contributor_last_name, contributor_first_name'")
            analysis.append("- Amount: 'contribution_amount'")
            analysis.append("- Location: 'contributor_city, contributor_state'")
            analysis.append("- Date: 'contribution_date'")
            analysis.append("If asked for top contributions, use 'contribution_amount' to sort")
            analysis.append("If asked for contributions from a state (or not from a state), use exact matching on 'contributor_state'")
            
            analysis.append("SCHEDULE B: Disbursements/expenditures made")
            analysis.append("- Payee names: Use 'payee_organization_name' OR 'payee_last_name, payee_first_name'")
            analysis.append("- Amount: 'expenditure_amount'")
            analysis.append("- Purpose: 'expenditure_purpose_descrip'")
            analysis.append("- Date: 'expenditure_date'")
            
            analysis.append("SCHEDULE C: Loans received")
            analysis.append("SCHEDULE D: Debts and obligations")
            analysis.append("SCHEDULE E: Independent expenditures")
        
        # Data quality notes
        analysis.append("\n=== DATA QUALITY NOTES ===")
        analysis.append("THRESHOLDS: Contributions/expenditures $200+ must be itemized with details")
        analysis.append("SMALL AMOUNTS: May appear in summary totals but not itemized")
        analysis.append("MISSING DATA: Some fields may be empty - use 'Not Available' or 'Unknown'")
        analysis.append("COMMITTEES: FEC ID format is usually C########")
        
        # Add the raw data
        analysis.append("\n" + "="*60)
        analysis.append("RAW FILING DATA")
        analysis.append("="*60)
        analysis.append(json.dumps(filing_data, indent=2, default=str))
        
        source = f"fec:{filing_id}"
        return llm.Fragment('\n'.join(analysis), source)
        
    except Exception as e:
        raise ValueError(f"Error loading FEC filing {filing_id}: {str(e)}")

def _generate_filing_analysis(filing_data):
    """Generate a comprehensive analysis of the FEC filing"""
    
    if 'filing' not in filing_data:
        return "Error: No filing information found in the data."
    
    filing_info = filing_data['filing']
    form_type = filing_info.get('form_type', '').upper()
    
    output = []
    output.append("=" * 80)
    output.append("                          FEC FILING ANALYSIS")
    output.append("=" * 80)
    output.append("")
    
    # Handle different form types differently
    if form_type in ['F1', 'F1A']:
        output.extend(_analyze_f1_filing(filing_info, filing_data))
    elif form_type in ['F2', 'F2A']:
        output.extend(_analyze_f2_filing(filing_info, filing_data))
    elif form_type == 'F99':
        output.extend(_analyze_f99_filing(filing_info, filing_data))
    else:
        # Default to financial report analysis (F3, F3P, F3X, etc.)
        output.extend(_analyze_financial_filing(filing_info, filing_data))
    
    return '\n'.join(output)

def _analyze_f1_filing(filing_info, filing_data):
    """Analyze F1/F1A - Statement of Organization for committees"""
    form_type = filing_info.get('form_type', '').upper()
    is_amendment = form_type == 'F1A'
    
    output = []
    
    if is_amendment:
        output.append("AMENDED STATEMENT OF ORGANIZATION (Form F1A)")
    else:
        output.append("STATEMENT OF ORGANIZATION (Form F1)")
    output.append("-" * 50)
    output.append("")
    
    # Committee information table
    committee_data = [
        ["FEC Committee ID", filing_info.get('fec_committee_id_number', 'Not Available')],
        ["Committee Name", filing_info.get('committee_name', 'Not Available')],
        ["Committee Type", filing_info.get('committee_type', 'Not Available')],
        ["Committee Designation", filing_info.get('committee_designation', 'Not Available')],
        ["Filing Frequency", filing_info.get('filing_frequency', 'Not Available')],
    ]
    
    # Show amendment status prominently
    if is_amendment:
        original_filing_id = filing_info.get('previous_report_amendment_indicator', '')
        if original_filing_id:
            committee_data.append(["Original Filing ID", original_filing_id])
        committee_data.append(["Filing Status", "Amendment"])
    else:
        committee_data.append(["Filing Status", "Original Filing"])
    
    # Add address information if available
    if filing_info.get('street_1'):
        address_parts = [filing_info.get('street_1', '')]
        if filing_info.get('street_2'):
            address_parts.append(filing_info.get('street_2'))
        committee_data.append(["Address", ', '.join(address_parts)])
        
        city_state_zip = []
        if filing_info.get('city'):
            city_state_zip.append(filing_info.get('city'))
        if filing_info.get('state'):
            city_state_zip.append(filing_info.get('state'))
        if filing_info.get('zip_code'):
            city_state_zip.append(filing_info.get('zip_code'))
        if city_state_zip:
            committee_data.append(["City, State, ZIP", ', '.join(city_state_zip)])
    
    # Committee contact information
    if filing_info.get('committee_email'):
        committee_data.append(["Committee Email", filing_info.get('committee_email')])
    else:
        committee_data.append(["Committee Email", "Not Available"])
        
    if filing_info.get('committee_url') or filing_info.get('committee_website'):
        url = filing_info.get('committee_url') or filing_info.get('committee_website')
        committee_data.append(["Committee Website", url])
    else:
        committee_data.append(["Committee Website", "Not Available"])
    
    # Treasurer information
    if filing_info.get('treasurer_name'):
        committee_data.append(["Treasurer", filing_info.get('treasurer_name')])
        
        # Treasurer contact information
        if filing_info.get('treasurer_email'):
            committee_data.append(["Treasurer Email", filing_info.get('treasurer_email')])
        else:
            committee_data.append(["Treasurer Email", "Not Available"])
    else:
        committee_data.append(["Treasurer", "Not Available"])
        committee_data.append(["Treasurer Email", "Not Available"])
    
    # Custodian of records
    if filing_info.get('custodian_name'):
        committee_data.append(["Custodian of Records", filing_info.get('custodian_name')])
        
        # Custodian contact information
        if filing_info.get('custodian_email'):
            committee_data.append(["Custodian Email", filing_info.get('custodian_email')])
        else:
            committee_data.append(["Custodian Email", "Not Available"])
    else:
        committee_data.append(["Custodian of Records", "Not Available"])
        committee_data.append(["Custodian Email", "Not Available"])
    
    committee_table = tabulate(committee_data, tablefmt="simple", colalign=("left", "right"))
    output.append(committee_table)
    output.append("")
    
    output.append("-" * 50)
    if is_amendment:
        output.append("ABOUT F1A FILINGS")
        output.append("-" * 50)
        output.append("• Amended Statement of Organization - updates committee information")
        output.append("• Filed when committee details change (address, treasurer, etc.)")
        output.append("• Amends the original F1 filing")
        output.append("• Contains updated organizational details, not financial information")
        output.append("• Must be filed within 10 days of changes")
    else:
        output.append("ABOUT F1 FILINGS")
        output.append("-" * 50)
        output.append("• Statement of Organization - establishes a political committee")
        output.append("• Filed when a committee first registers with the FEC")
        output.append("• Contains organizational details, not financial information")
        output.append("• Must be filed before a committee can raise or spend money")
        output.append("• Amendments (F1A) update committee information")
    
    return output

def _analyze_f2_filing(filing_info, filing_data):
    """Analyze F2/F2A - Statement of Candidacy"""
    form_type = filing_info.get('form_type', '').upper()
    is_amendment = form_type == 'F2A'
    
    output = []
    
    if is_amendment:
        output.append("AMENDED STATEMENT OF CANDIDACY (Form F2A)")
    else:
        output.append("STATEMENT OF CANDIDACY (Form F2)")
    output.append("-" * 50)
    output.append("")
    
    # Candidate information table
    candidate_data = [
        ["FEC Committee ID", filing_info.get('fec_committee_id_number', 'Not Available')],
        ["Candidate Name", filing_info.get('candidate_name', filing_info.get('committee_name', 'Not Available'))],
        ["Office Sought", filing_info.get('office', 'Not Available')],
        ["State", filing_info.get('state', 'Not Available')],
        ["District", filing_info.get('district', 'N/A')],
        ["Election Year", filing_info.get('election_year', 'Not Available')],
        ["Election Type", filing_info.get('election_type', 'Not Available')],
    ]
    
    # Show amendment status prominently
    if is_amendment:
        original_filing_id = filing_info.get('previous_report_amendment_indicator', '')
        if original_filing_id:
            candidate_data.append(["Original Filing ID", original_filing_id])
        candidate_data.append(["Filing Status", "Amendment"])
    else:
        candidate_data.append(["Filing Status", "Original Filing"])
    
    # Add party affiliation if available
    if filing_info.get('party'):
        candidate_data.append(["Party", filing_info.get('party')])
    else:
        candidate_data.append(["Party", "Not Available"])
    
    # Add contact information
    if filing_info.get('candidate_email') or filing_info.get('email'):
        email = filing_info.get('candidate_email') or filing_info.get('email')
        candidate_data.append(["Email", email])
    else:
        candidate_data.append(["Email", "Not Available"])
        
    if filing_info.get('candidate_url') or filing_info.get('candidate_website') or filing_info.get('website'):
        url = filing_info.get('candidate_url') or filing_info.get('candidate_website') or filing_info.get('website')
        candidate_data.append(["Website", url])
    else:
        candidate_data.append(["Website", "Not Available"])
    
    # Add address information if available
    if filing_info.get('street_1'):
        address_parts = [filing_info.get('street_1', '')]
        if filing_info.get('street_2'):
            address_parts.append(filing_info.get('street_2'))
        candidate_data.append(["Address", ', '.join(address_parts)])
        
        city_state_zip = []
        if filing_info.get('city'):
            city_state_zip.append(filing_info.get('city'))
        if filing_info.get('candidate_state'):
            city_state_zip.append(filing_info.get('candidate_state'))
        elif filing_info.get('state'):
            city_state_zip.append(filing_info.get('state'))
        if filing_info.get('zip_code'):
            city_state_zip.append(filing_info.get('zip_code'))
        if city_state_zip:
            candidate_data.append(["City, State, ZIP", ', '.join(city_state_zip)])
    
    candidate_table = tabulate(candidate_data, tablefmt="simple", colalign=("left", "right"))
    output.append(candidate_table)
    output.append("")
    
    output.append("-" * 50)
    if is_amendment:
        output.append("ABOUT F2A FILINGS")
        output.append("-" * 50)
        output.append("• Amended Statement of Candidacy - updates candidate information")
        output.append("• Filed when candidate details change (address, office sought, etc.)")
        output.append("• Amends the original F2 filing")
        output.append("• Contains updated candidate information, not financial data")
        output.append("• Must be filed within 15 days of changes")
    else:
        output.append("ABOUT F2 FILINGS")
        output.append("-" * 50)
        output.append("• Statement of Candidacy - declares intent to run for federal office")
        output.append("• Filed by individuals seeking House, Senate, or Presidential office")
        output.append("• Must be filed within 15 days of becoming a candidate")
        output.append("• Contains candidate information, not financial data")
        output.append("• Amendments (F2A) update candidate information")
    
    return output

def _analyze_f99_filing(filing_info, filing_data):
    """Analyze F99 - Miscellaneous Text filings"""
    output = []
    
    output.append("MISCELLANEOUS TEXT FILING (Form F99)")
    output.append("-" * 50)
    output.append("")
    
    # Basic filing information
    basic_data = [
        ["FEC Committee ID", filing_info.get('fec_committee_id_number', 'Not Available')],
        ["Committee", filing_info.get('committee_name', 'Not Available')],
        ["Filing Date", _format_date(filing_info.get('date_signed', '')) or 'Not Available'],
        ["Text", filing_info.get('text', 'Not Available')],
    ]
    
    # Add amendment information if applicable
    amendment_indicator = filing_info.get('amendment_indicator', '')
    if amendment_indicator in ['A', 'T']:
        amendment_type = 'Termination Amendment' if amendment_indicator == 'T' else 'Amendment'
        basic_data.append(["Filing Status", amendment_type])
    else:
        basic_data.append(["Filing Status", "Original Filing"])
    
    basic_table = tabulate(basic_data, tablefmt="simple", colalign=("left", "right"))
    output.append(basic_table)
    output.append("")
    
    # Show the text content - this is the most important part of F99 filings
    if 'text' in filing_data and filing_data['text']:
        output.append("-" * 50)
        output.append("FILING TEXT CONTENT")
        output.append("-" * 50)
        
        # F99 text can be quite long, so we'll show it in a readable format
        text_content = filing_data['text']
        if isinstance(text_content, list):
            for i, text_item in enumerate(text_content, 1):
                if isinstance(text_item, dict) and 'text' in text_item:
                    output.append(f"Text Block {i}:")
                    output.append(text_item['text'])
                    output.append("")
                elif isinstance(text_item, str):
                    output.append(f"Text Block {i}:")
                    output.append(text_item)
                    output.append("")
        elif isinstance(text_content, str):
            output.append(text_content)
            output.append("")
    else:
        output.append("No text content found in this F99 filing.")
        output.append("")
    
    output.append("-" * 50)
    output.append("ABOUT F99 FILINGS")
    output.append("-" * 50)
    output.append("• Miscellaneous text filings for various purposes")
    output.append("• Used for notifications, explanations, and other communications")
    output.append("• Common uses: debt settlements, schedule changes, explanations")
    output.append("• The text content above contains the substantive information")
    output.append("• No financial data - focus on the written explanation")
    
    return output

def _analyze_financial_filing(filing_info, filing_data):
    """Analyze financial filings (F3, F3P, F3X, etc.)"""
    output = []
    
    # Use tabulate for the summary
    try:
        summary_table = _format_summary_table(filing_info)
        output.append(summary_table)
        output.append("")
    except Exception as e:
        output.append(f"Error formatting summary table: {str(e)}")
        output.append("")

    # Itemizations summary
    if 'itemizations' in filing_data and filing_data['itemizations']:
        output.append("-" * 50)
        output.append("ITEMIZATIONS SUMMARY")
        output.append("-" * 50)
        
        try:
            # Create itemizations summary table
            itemization_data = []
            for schedule, items in filing_data['itemizations'].items():
                itemization_data.append([schedule, f"{len(items):,}"])
            
            itemization_table = tabulate(itemization_data, 
                                       headers=["Schedule", "Item Count"], 
                                       tablefmt="simple", 
                                       numalign="right")
            output.append(itemization_table)
            output.append("")
        except Exception as e:
            output.append(f"Error formatting itemizations table: {str(e)}")
            output.append("")

        # Analyze specific schedules
        try:
            schedule_output = _analyze_schedules(filing_data['itemizations'])
            output.extend(schedule_output)
        except Exception as e:
            output.append(f"Error analyzing schedules: {str(e)}")
            output.append("")

    # Additional context about what the user can ask
    output.append("-" * 50)
    output.append("WHAT YOU CAN ASK ABOUT")
    output.append("-" * 50)
    output.append("• Individual contributions or disbursements")
    output.append("• Top donors or recipients")
    output.append("• Spending by category")
    output.append("• Geographic analysis of contributions")
    output.append("• Time-based patterns")
    output.append("• Specific transactions or amounts")
    
    return output

def _analyze_schedules(itemizations):
    """Analyze specific schedules based on what's available"""
    output = []
    
    # Analyze Schedule A (Contributions) if present
    if 'Schedule A' in itemizations:
        contributions = itemizations['Schedule A']
        if contributions:
            output.append("-" * 50)
            output.append("TOP INDIVIDUAL CONTRIBUTIONS (Schedule A)")
            output.append("-" * 50)
            
            try:
                contributions_table = _format_contributions_table(contributions, limit=10)
                output.append(contributions_table)
                output.append("")
            except Exception as e:
                output.append(f"Error formatting contributions table: {str(e)}")
                output.append("")

    # Analyze Schedule B (Disbursements) if present  
    if 'Schedule B' in itemizations:
        disbursements = itemizations['Schedule B']
        if disbursements:
            output.append("-" * 50)
            output.append("TOP DISBURSEMENTS (Schedule B)")
            output.append("-" * 50)
            
            try:
                disbursements_table = _format_disbursements_table(disbursements, limit=10)
                output.append(disbursements_table)
                output.append("")
            except Exception as e:
                output.append(f"Error formatting disbursements table: {str(e)}")
                output.append("")
    
    return output

def _format_contributions_table(contributions, limit=10):
    """Format contributions as a nice table using tabulate"""
    if not contributions:
        return "No contributions found."
    
    data = []
    sorted_contribs = sorted(contributions, 
                           key=lambda x: x.get('contribution_amount', 0), 
                           reverse=True)[:limit]
    
    for i, contrib in enumerate(sorted_contribs, 1):
        # Determine contributor name - organization takes precedence
        name = contrib.get('contributor_organization_name', '').strip()
        
        if not name:
            # If no organization name, use individual name
            last_name = contrib.get('contributor_last_name', '').strip()
            first_name = contrib.get('contributor_first_name', '').strip()
            
            if last_name and first_name:
                name = f"{last_name}, {first_name}"
            elif last_name:
                name = last_name
            elif first_name:
                name = first_name
            else:
                name = "Not Available"
        
        # Truncate long names but keep readable
        if len(name) > 35:
            name = name[:32] + "..."
        
        amount = f"${contrib.get('contribution_amount', 0):,.2f}"
        city = contrib.get('contributor_city', '')
        state = contrib.get('contributor_state', '')
        location = f"{city}, {state}" if city and state else state or city or 'Not Available'
        
        # Truncate location if too long
        if len(location) > 25:
            location = location[:22] + "..."
            
        data.append([i, name, amount, location])
    
    headers = ["#", "Contributor Name", "Amount", "Location"]
    return tabulate(data, headers=headers, tablefmt="simple", numalign="right")

def _format_disbursements_table(disbursements, limit=10):
    """Format disbursements as a nice table using tabulate"""
    if not disbursements:
        return "No disbursements found."
    
    data = []
    sorted_disb = sorted(disbursements,
                       key=lambda x: x.get('expenditure_amount', 0),
                       reverse=True)[:limit]
    
    for i, disb in enumerate(sorted_disb, 1):
        # Determine payee name - organization takes precedence
        recipient = disb.get('payee_organization_name', '').strip()
        
        if not recipient:
            # If no organization name, use individual name
            last_name = disb.get('payee_last_name', '').strip()
            first_name = disb.get('payee_first_name', '').strip()
            
            if last_name and first_name:
                recipient = f"{last_name}, {first_name}"
            elif last_name:
                recipient = last_name
            elif first_name:
                recipient = first_name
            else:
                recipient = "Not Available"
        
        # Truncate long names but keep readable
        if len(recipient) > 30:
            recipient = recipient[:27] + "..."
            
        amount = f"${disb.get('expenditure_amount', 0):,.2f}"
        
        # Format the expenditure date
        exp_date = disb.get('expenditure_date', '')
        formatted_date = _format_date(exp_date) if exp_date else 'Not Available'
        
        purpose = disb.get('expenditure_purpose_descrip', 'Not Available')
        
        # Truncate purpose if too long
        if len(purpose) > 20:
            purpose = purpose[:17] + "..."
            
        data.append([i, recipient, amount, formatted_date, purpose])
    
    headers = ["#", "Recipient Name", "Amount", "Date", "Purpose"]
    return tabulate(data, headers=headers, tablefmt="simple", numalign="right")

def _format_summary_table(filing_info):
    """Format the filing summary as a table"""
    # Calculate coverage period and days
    coverage_from = filing_info.get('coverage_from_date', '')
    coverage_through = filing_info.get('coverage_through_date', '')
    
    # Format dates to show only the date part
    formatted_from = _format_date(coverage_from)
    formatted_through = _format_date(coverage_through)
    
    coverage_days = _calculate_coverage_days(coverage_from, coverage_through)
    
    if coverage_days and formatted_from and formatted_through:
        coverage_text = f"{formatted_from} to {formatted_through} ({coverage_days} days)"
    elif formatted_from and formatted_through:
        coverage_text = f"{formatted_from} to {formatted_through}"
    else:
        coverage_text = "Not Available"
    
    data = [
        ["FEC Committee ID", filing_info.get('fec_committee_id_number', 'Not Available')],
        ["Committee", filing_info.get('committee_name', 'Not Available')],
        ["Form Type", filing_info.get('form_type', 'Not Available')],
        ["Coverage Period", coverage_text],
        ["Total Receipts", f"${filing_info.get('col_a_total_receipts', 0):,.2f}"],
        ["Total Disbursements", f"${filing_info.get('col_a_total_disbursements', 0):,.2f}"],
        ["Ending Cash on Hand", f"${filing_info.get('col_a_cash_on_hand_close_of_period', 0):,.2f}"]
    ]
    
    # Add amendment information
    amendment_indicator = filing_info.get('amendment_indicator', '')
    if amendment_indicator in ['A', 'T']:
        amendment_type = 'Termination Amendment' if amendment_indicator == 'T' else 'Amendment'
        data.append(["Filing Status", amendment_type])
        
        original_filing_id = filing_info.get('previous_report_amendment_indicator', '')
        if original_filing_id:
            data.append(["Original Filing ID", original_filing_id])
    else:
        data.append(["Filing Status", "Original Filing"])
    
    return tabulate(data, tablefmt="simple", colalign=("left", "right"))

def _format_date(date_obj):
    """Format a date object to show only the date part (YYYY-MM-DD)"""
    if not date_obj:
        return None
        
    try:
        # If it's already a string, try to extract just the date part
        if isinstance(date_obj, str):
            # If it looks like "2025-05-01 00:00:00-04:00", extract just the date part
            if ' ' in date_obj:
                return date_obj.split(' ')[0]
            return date_obj
        
        # If it's a datetime object, get just the date part
        if hasattr(date_obj, 'date'):
            return str(date_obj.date())
        
        # If it's already a date object
        if hasattr(date_obj, 'strftime'):
            return date_obj.strftime('%Y-%m-%d')
            
        return str(date_obj)
        
    except (ValueError, TypeError, AttributeError):
        return None

def _calculate_coverage_days(from_date, through_date):
    """Calculate the number of days in the coverage period"""
    if not from_date or not through_date:
        return None
        
    try:
        from datetime import datetime
        
        # Handle different date formats that might come from FEC data
        # FEC dates can be datetime objects or strings
        if hasattr(from_date, 'date'):
            # It's a datetime object
            start_date = from_date.date()
        elif isinstance(from_date, str):
            # Try to parse string date - handle various formats
            date_str = from_date.split(' ')[0]  # Take just the date part if it has time
            start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            start_date = from_date
            
        if hasattr(through_date, 'date'):
            # It's a datetime object  
            end_date = through_date.date()
        elif isinstance(through_date, str):
            # Try to parse string date - handle various formats
            date_str = through_date.split(' ')[0]  # Take just the date part if it has time
            end_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            end_date = through_date
        
        # Calculate the difference
        delta = end_date - start_date
        return delta.days + 1  # +1 to include both start and end dates
        
    except (ValueError, TypeError, AttributeError):
        # If we can't parse the dates, just return None
        return None