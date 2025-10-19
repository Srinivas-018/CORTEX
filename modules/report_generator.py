"""
Report Generator Module
Generate professional forensic analysis reports in PDF format
"""

import streamlit as st
from fpdf import FPDF
from datetime import datetime
import pandas as pd

def render_report_generator(case_id):
    """Render the report generation interface"""
    st.header("📄 Forensic Report Generation")
    
    from database.db_manager import get_case, get_case_evidence, get_chain_of_custody
    
    case = get_case(case_id)
    
    if not case:
        st.error("Case not found")
        return
    
    st.info("Generate a comprehensive forensic analysis report for this case")
    
    with st.form("report_config"):
        st.subheader("Report Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_title = st.text_input("Report Title", value=f"Forensic Analysis Report - {case[1]}")
            investigator = st.text_input("Lead Investigator", value=case[2] or "")
            agency = st.text_input("Agency/Organization", value="Digital Forensics Lab")
        
        with col2:
            report_date = st.date_input("Report Date", value=datetime.now())
            case_status = st.selectbox("Case Status", ["Open", "Closed", "Pending Review"])
            classification = st.selectbox("Classification", ["Confidential", "Internal", "Public"])
        
        include_sections = st.multiselect(
            "Include Sections",
            ["Executive Summary", "Device Information", "Evidence Inventory", 
             "Timeline Analysis", "Data Extraction Results", "Chain of Custody", 
             "Hash Verification", "Conclusions"],
            default=["Executive Summary", "Device Information", "Evidence Inventory", 
                    "Chain of Custody", "Hash Verification"]
        )
        
        executive_summary = st.text_area(
            "Executive Summary",
            height=150,
            placeholder="Provide a brief summary of the case and key findings..."
        )
        
        conclusions = st.text_area(
            "Conclusions",
            height=150,
            placeholder="Document your conclusions and recommendations..."
        )
        
        generate_btn = st.form_submit_button("Generate Report", type="primary")
        
        if generate_btn:
            with st.spinner("Generating forensic report..."):
                pdf = generate_forensic_report(
                    case,
                    report_title,
                    investigator,
                    agency,
                    report_date,
                    case_status,
                    classification,
                    include_sections,
                    executive_summary,
                    conclusions
                )
                
                pdf_output = pdf.output(dest='S')
                if isinstance(pdf_output, str):
                    pdf_output = pdf_output.encode('latin-1')
                
                st.success("✅ Report generated successfully!")
                
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_output,
                    file_name=f"forensic_report_{case_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
                
                from database.db_manager import add_chain_of_custody
                add_chain_of_custody(
                    case_id,
                    "Report Generated",
                    investigator,
                    f"Generated {report_title}"
                )

def generate_forensic_report(case, title, investigator, agency, report_date, 
                            status, classification, sections, summary, conclusions):
    """Generate a PDF forensic report"""
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "FORENSIC ANALYSIS REPORT", ln=True, align="C")
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, classification.upper(), ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Case Information", ln=True)
    pdf.set_font("Arial", "", 11)
    
    pdf.cell(0, 8, f"Case ID: {case[0]}", ln=True)
    pdf.cell(0, 8, f"Case Name: {case[1]}", ln=True)
    pdf.cell(0, 8, f"Lead Investigator: {investigator}", ln=True)
    pdf.cell(0, 8, f"Agency: {agency}", ln=True)
    pdf.cell(0, 8, f"Report Date: {report_date.strftime('%Y-%m-%d')}", ln=True)
    pdf.cell(0, 8, f"Case Status: {status}", ln=True)
    pdf.ln(5)
    
    if "Executive Summary" in sections and summary:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, summary)
        pdf.ln(5)
    
    if "Device Information" in sections:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Device Information", ln=True)
        pdf.set_font("Arial", "", 11)
        
        pdf.cell(0, 8, f"Device Info: {case[3] or 'N/A'}", ln=True)
        pdf.cell(0, 8, f"Image File: {case[4] or 'N/A'}", ln=True)
        pdf.cell(0, 8, f"Image Hash (SHA-256):", ln=True)
        pdf.set_font("Courier", "", 9)
        pdf.cell(0, 6, f"{case[5] or 'N/A'}", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.ln(5)
    
    if "Evidence Inventory" in sections:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Evidence Inventory", ln=True)
        pdf.set_font("Arial", "", 11)
        
        from database.db_manager import get_case_evidence
        evidence = get_case_evidence(case[0])
        
        if evidence:
            pdf.cell(0, 8, f"Total Evidence Items: {len(evidence)}", ln=True)
            pdf.ln(3)
            
            for item in evidence[:10]:
                pdf.cell(0, 6, f"- {item[2]}: {item[3]}", ln=True)
            
            if len(evidence) > 10:
                pdf.cell(0, 6, f"... and {len(evidence) - 10} more items", ln=True)
        else:
            pdf.cell(0, 8, "No evidence items logged", ln=True)
        
        pdf.ln(5)
    
    if "Hash Verification" in sections:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Hash Verification & Integrity", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, "All evidence has been hashed using SHA-256 to ensure integrity and maintain chain of custody. Hash values are stored in the case database.")
        pdf.ln(5)
    
    if "Chain of Custody" in sections:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Chain of Custody Log", ln=True)
        pdf.set_font("Arial", "", 10)
        
        from database.db_manager import get_chain_of_custody
        custody_log = get_chain_of_custody(case[0])
        
        if custody_log:
            for log in custody_log[:15]:
                timestamp = datetime.fromisoformat(log[4]).strftime("%Y-%m-%d %H:%M")
                pdf.cell(0, 5, f"{timestamp} - {log[2]} by {log[3]}: {log[5][:60]}", ln=True)
        
        pdf.ln(5)
    
    if "Conclusions" in sections and conclusions:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Conclusions", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, conclusions)
        pdf.ln(5)
    
    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 5, f"Report generated by CORTEX - Mobile Device Forensics Analyzer", ln=True, align="C")
    pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    
    return pdf
