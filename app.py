"""
CORTEX - Mobile Device Forensics Analyzer
Complete forensic analysis platform for mobile device images

Author: Digital Forensics Lab
Version: 1.0.0
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import get_all_cases, create_case, delete_case, get_case
from modules.image_input import render_image_input
from modules.file_parser import render_file_parser
from modules.data_extractor import render_data_extractor
from modules.analysis_tools import render_analysis_tools
from modules.visualization import render_visualization
from modules.report_generator import render_report_generator

st.set_page_config(
    page_title="CORTEX - Mobile Forensics Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize session state variables"""
    if 'current_case' not in st.session_state:
        st.session_state['current_case'] = None
    if 'investigator' not in st.session_state:
        st.session_state['investigator'] = "Lead Investigator"

def render_home():
    """Render the home/dashboard page"""
    st.title("CORTEX - Mobile Device Forensics Analyzer")
    st.markdown("### Professional Forensic Analysis Platform")
    
    st.info("Analyze mobile device images • Extract digital evidence • Generate forensic reports")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Cases", len(get_all_cases()))
    with col2:
        st.metric("Platform Status", "Ready")
    with col3:
        st.metric("Version", "1.0.0")
    with col4:
        st.metric("Database", "SQLite")
    
    st.divider()
    
    st.subheader("Case Management")
    
    cases = get_all_cases()
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        with st.form("new_case_form"):
            st.write("**Create New Case**")
            
            case_id = st.text_input("Case ID", placeholder="CASE-2025-001")
            case_name = st.text_input("Case Name", placeholder="Device Seizure - Smith Investigation")
            investigator = st.text_input("Investigator", value=st.session_state.get('investigator', ''))
            device_info = st.text_input("Device Info", placeholder="Samsung Galaxy S21")
            notes = st.text_area("Case Notes", placeholder="Brief description...")
            
            submit = st.form_submit_button("Create Case", type="primary")
            
            if submit:
                if case_id and case_name and investigator:
                    success = create_case(case_id, case_name, investigator, device_info, notes)
                    if success:
                        st.session_state['investigator'] = investigator
                        st.success(f"Case {case_id} created successfully!")
                        st.rerun()
                    else:
                        st.error("Case ID already exists")
                else:
                    st.warning("Please fill in all required fields")
    
    with col1:
        if cases:
            st.write("**Existing Cases:**")
            
            for case in cases:
                with st.expander(f"{case[0]} - {case[1]} ({case[7]})"):
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        st.write(f"**Investigator:** {case[2]}")
                        st.write(f"**Created:** {case[6][:10]}")
                        st.write(f"**Device:** {case[3] or 'Not specified'}")
                        st.write(f"**Image:** {case[4] or 'Not uploaded'}")
                        if case[8]:
                            st.write(f"**Notes:** {case[8]}")
                    
                    with col_b:
                        if st.button("Open Case", key=f"open_{case[0]}"):
                            st.session_state['current_case'] = case[0]
                            st.rerun()
                        
                        if st.button("Delete", key=f"del_{case[0]}", type="secondary"):
                            delete_case(case[0])
                            st.success(f"Case {case[0]} deleted")
                            st.rerun()
        else:
            st.info("No cases yet. Create a new case to get started.")
    
    st.divider()
    
    with st.expander("ℹAbout CORTEX"):
        st.markdown("""
        **CORTEX** (Comprehensive Offline Retrieval and Tracking Evidence eXtractor) 
        is a professional mobile device forensics analysis platform.
        
        **Key Features:**
        - 📱 Process mobile device images (.img, .bin, .dd)
        - 🔍 Extract SMS, calls, WhatsApp, and other artifacts
        - 📊 Timeline reconstruction and analysis
        - 🗺️ Location tracking and visualization
        - 🔐 SHA-256 hash verification & chain of custody
        - 📄 Professional PDF forensic reports
        
        **Supported Evidence Types:**
        - Call logs and SMS messages
        - Messaging apps (WhatsApp, Telegram, Signal)
        - Contacts and calendar entries
        - Browser history and bookmarks
        - Location data (GPS, cell towers, WiFi)
        - Photos and videos with EXIF data
        - Deleted and hidden data recovery
        
        **Built with:** Python • Streamlit • SQLite • Plotly
        """)

def render_case_view(case_id):
    """Render the case analysis view"""
    case = get_case(case_id)
    
    if not case:
        st.error("Case not found")
        if st.button("← Back to Dashboard"):
            st.session_state['current_case'] = None
            st.rerun()
        return
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title(f"{case[0]}")
        st.caption(f"{case[1]} • Investigator: {case[2]} • Status: {case[7]}")
    
    with col2:
        st.write("")
    
    with col3:
        if st.button("← Back to Dashboard", type="secondary"):
            st.session_state['current_case'] = None
            st.rerun()
    
    st.divider()
    
    tabs = st.tabs([
        "Image Input", 
        "File System", 
        "Data Extraction", 
        "Analysis", 
        "Visualization", 
        "Reports"
    ])
    
    image_info = None
    if case[4]:
        image_info = {
            'filename': case[4],
            'sha256': case[5]
        }
    
    with tabs[0]:
        result = render_image_input(case_id)
        if result:
            image_info = result
    
    with tabs[1]:
        render_file_parser(case_id, image_info)
    
    with tabs[2]:
        render_data_extractor(case_id, image_info)
    
    with tabs[3]:
        render_analysis_tools(case_id)
    
    with tabs[4]:
        render_visualization(case_id)
    
    with tabs[5]:
        render_report_generator(case_id)

def main():
    """Main application entry point"""
    init_session_state()
    
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=CORTEX", use_container_width=True)
        
        st.markdown("###  Forensics Platform")
        
        if st.session_state.get('current_case'):
            case = get_case(st.session_state['current_case'])
            if case:
                st.success(f"**Active Case:**\n{case[0]}")
                
                from database.db_manager import get_case_evidence
                evidence_count = len(get_case_evidence(case[0]))
                st.metric("Evidence Items", evidence_count)
                
                st.divider()
        
        st.markdown("### Quick Actions")
        
        if st.button("Home", use_container_width=True):
            st.session_state['current_case'] = None
            st.rerun()
        
        st.divider()
        
        with st.expander("System Info"):
            st.write("**Version:** 1.0.0")
            st.write("**Database:** SQLite")
            st.write("**Status:** Ready")
        
        st.divider()
        st.caption("© 2025 CORTEX Platform")
    
    if st.session_state.get('current_case'):
        render_case_view(st.session_state['current_case'])
    else:
        render_home()

if __name__ == "__main__":
    main()
 