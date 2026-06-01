"""
Analysis Tools Module
Timeline reconstruction, keyword search, and artifact analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from database.db_manager import get_case

def render_analysis_tools(case_id):
    """Render the analysis tools interface"""
    st.header("Analysis & Investigation Tools")
    
    case = get_case(case_id)
    is_logical = False
    profile_path = ""
    if case and case[4] and str(case[4]).endswith('.json'):
        is_logical = True
        profile_path = case[4]
        
    if is_logical:
        tabs = st.tabs(["Timeline Reconstruction", "Keyword Search", "Statistics", "System Logs (Logcat)"])
    else:
        tabs = st.tabs(["Timeline Reconstruction", "Keyword Search", "Statistics"])
    
    with tabs[0]:
        render_timeline_reconstruction()
    
    with tabs[1]:
        render_keyword_search()
    
    with tabs[2]:
        render_statistics(case_id)
        
    if is_logical:
        with tabs[3]:
            render_logcat_viewer(profile_path)

def render_timeline_reconstruction():
    """Create a timeline from all extracted artifacts"""
    st.subheader("Timeline Reconstruction")
    
    st.info("Combine all artifacts into a chronological timeline for investigation")
    
    if st.button("Generate Timeline", type="primary"):
        timeline_data = build_timeline()
        st.session_state['timeline'] = timeline_data
        st.success(f"Generated timeline with {len(timeline_data)} events")
    
    if 'timeline' in st.session_state:
        timeline = st.session_state['timeline']
        
        # Convert timestamps to datetime objects to avoid TypeError with floats
        timeline['Timestamp'] = pd.to_datetime(timeline['Timestamp'], errors='coerce')
        
        min_ts = timeline['Timestamp'].min()
        max_ts = timeline['Timestamp'].max()
        
        min_date = min_ts.strftime('%Y-%m-%d') if pd.notnull(min_ts) else "N/A"
        max_date = max_ts.strftime('%Y-%m-%d') if pd.notnull(max_ts) else "N/A"
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Events", len(timeline))
        col2.metric("Date Range", f"{min_date} to {max_date}")
        col3.metric("Event Types", timeline['Type'].nunique())
        
        st.divider()
        
        event_filter = st.multiselect(
            "Filter by Event Type",
            options=timeline['Type'].unique().tolist(),
            default=timeline['Type'].unique().tolist()
        )
        
        filtered_timeline = timeline[timeline['Type'].isin(event_filter)]
        
        st.dataframe(
            filtered_timeline.sort_values('Timestamp', ascending=False),
            width='stretch',
            height=400
        )
        
        if st.button("Export Timeline (CSV)"):
            csv = filtered_timeline.to_csv(index=False)
            st.download_button("Download Timeline CSV", csv, "timeline.csv", "text/csv")

def render_keyword_search():
    """Search for keywords across all artifacts"""
    st.subheader("Keyword Search")
    
    st.write("Search for keywords across SMS, chats, browser history, and other text artifacts")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        keyword = st.text_input("Enter keyword or phrase", placeholder="e.g., password, confidential, meeting")
    
    with col2:
        case_sensitive = st.checkbox("Case sensitive")
    
    if keyword and st.button("Search", type="primary"):
        results = perform_keyword_search(keyword, case_sensitive)
        st.session_state['search_results'] = results
        
        if len(results) > 0:
            st.success(f"Found {len(results)} matches")
        else:
            st.warning("No matches found")
    
    if 'search_results' in st.session_state and len(st.session_state['search_results']) > 0:
        st.dataframe(st.session_state['search_results'], width='stretch')

def render_statistics(case_id):
    """Display statistics about extracted data"""
    st.subheader("Case Statistics")
    
    from database.db_manager import get_case_evidence
    evidence = get_case_evidence(case_id)
    
    if evidence:
        st.write(f"**Total Evidence Items:** {len(evidence)}")
        
        evidence_types = {}
        for item in evidence:
            artifact_type = item[2]
            evidence_types[artifact_type] = evidence_types.get(artifact_type, 0) + 1
        
        st.write("**Evidence by Type:**")
        for etype, count in evidence_types.items():
            st.write(f"- {etype}: {count}")
    else:
        st.info("No evidence extracted yet")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'call_logs' in st.session_state:
            st.metric("Call Records", len(st.session_state['call_logs']))
    
    with col2:
        if 'sms_data' in st.session_state:
            st.metric("SMS Messages", len(st.session_state['sms_data']))
    
    with col3:
        if 'contacts' in st.session_state:
            st.metric("Contacts", len(st.session_state['contacts']))

def build_timeline():
    """Build a unified timeline from all available data"""
    timeline_events = []
    
    if 'call_logs' in st.session_state:
        for _, row in st.session_state['call_logs'].iterrows():
            timeline_events.append({
                'Timestamp': row['Timestamp'],
                'Type': 'Call',
                'Description': f"{row['Type']} call with {row['Contact']} ({row['Duration (s)']}s)",
                'Source': 'Call Logs'
            })
    
    if 'sms_data' in st.session_state:
        for _, row in st.session_state['sms_data'].iterrows():
            timeline_events.append({
                'Timestamp': row['Timestamp'],
                'Type': 'SMS',
                'Description': f"{row['Type']} SMS to/from {row['Contact']}: {row['Message'][:50]}...",
                'Source': 'SMS Database'
            })
    
    if 'chat_data' in st.session_state:
        for _, row in st.session_state['chat_data'].iterrows():
            timeline_events.append({
                'Timestamp': row['Timestamp'],
                'Type': 'Chat',
                'Description': f"{row['App']} message in {row['Chat']}: {row['Message'][:50]}",
                'Source': row['App']
            })
    
    if 'browser_history' in st.session_state:
        for _, row in st.session_state['browser_history'].iterrows():
            timeline_events.append({
                'Timestamp': row['Last Visit'],
                'Type': 'Browser',
                'Description': f"Visited {row['Title']} - {row['URL']}",
                'Source': f"{row['Browser']} History"
            })
    
    if timeline_events:
        return pd.DataFrame(timeline_events).sort_values('Timestamp', ascending=False)
    else:
        return pd.DataFrame(columns=['Timestamp', 'Type', 'Description', 'Source'])

def perform_keyword_search(keyword, case_sensitive=False):
    """Search for keyword across all text data"""
    results = []
    
    if not case_sensitive:
        keyword = keyword.lower()
    
    if 'sms_data' in st.session_state:
        for _, row in st.session_state['sms_data'].iterrows():
            message = row['Message'] if case_sensitive else row['Message'].lower()
            if keyword in message:
                results.append({
                    'Source': 'SMS',
                    'Match': row['Message'],
                    'Context': f"Conversation with {row['Contact']}",
                    'Timestamp': row['Timestamp']
                })
    
    if 'chat_data' in st.session_state:
        for _, row in st.session_state['chat_data'].iterrows():
            message = row['Message'] if case_sensitive else row['Message'].lower()
            if keyword in message:
                results.append({
                    'Source': row['App'],
                    'Match': row['Message'],
                    'Context': f"Chat: {row['Chat']}",
                    'Timestamp': row['Timestamp']
                })
    
    if 'browser_history' in st.session_state:
        for _, row in st.session_state['browser_history'].iterrows():
            url = row['URL'] if case_sensitive else row['URL'].lower()
            title = row['Title'] if case_sensitive else row['Title'].lower()
            if keyword in url or keyword in title:
                results.append({
                    'Source': 'Browser History',
                    'Match': row['URL'],
                    'Context': row['Title'],
                    'Timestamp': row['Last Visit']
                })
    
    return pd.DataFrame(results) if results else pd.DataFrame(columns=['Source', 'Match', 'Context', 'Timestamp'])

def render_logcat_viewer(profile_path):
    st.subheader("📋 System Logcat Viewer")
    st.info("Explore and search through system logs captured from the device")
    
    if not profile_path or not os.path.exists(profile_path):
        st.warning("Log profile not found on disk.")
        return
        
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
    except Exception as e:
        st.error(f"Failed to load profile logs: {str(e)}")
        return
        
    logs = profile.get("logcat", [])
    if not logs:
        st.warning("No logcat logs found in this profile.")
        return
        
    df_logs = pd.DataFrame(logs)
    
    search_log = st.text_input("Search Logs", placeholder="e.g. fatal, error, system")
    if search_log:
        df_logs = df_logs[df_logs['Log Entry'].str.contains(search_log, case=False, na=False)]
        
    st.dataframe(df_logs, use_container_width=True, height=450, hide_index=True)
    
    txt_content = "\n".join([item.get("Log Entry", "") for item in logs])
    st.download_button("Download Full Logcat (TXT)", txt_content, "logcat.txt", "text/plain")
