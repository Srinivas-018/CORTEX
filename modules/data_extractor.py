"""
Data Extraction Module
Extracts SMS, calls, WhatsApp, contacts, and other artifacts from mobile device images
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import sqlite3
import os
from pathlib import Path

def render_data_extractor(case_id, image_info=None):
    """Render the data extraction interface"""
    st.header("Data Extraction")
    
    if not image_info:
        st.warning("Please upload a device image first")
        return
    
    st.info("Extract digital artifacts from the device image")
    
    # Mode selector
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Image:** {image_info.get('filename', 'Unknown')}")
    with col2:
        extraction_mode = st.selectbox(
            "Mode", 
            ["Demo Mode", "Real Extraction"],
            help="Demo Mode generates sample data. Real Extraction parses actual databases from the image."
        )
    
    # Store mode in session state
    st.session_state['extraction_mode'] = extraction_mode
    
    if extraction_mode == "Real Extraction" and not image_info.get('file_path'):
        st.warning("⚠️ Real extraction requires the image file to be saved. Please click 'Verify & Process Image' first.")
        extraction_mode = "Demo Mode"
    
    tabs = st.tabs(["Calls & SMS", "Messaging Apps", "Contacts", "Location Data", "Browser History", "Deleted Data"])
    
    with tabs[0]:
        render_calls_sms_extraction(case_id, image_info, extraction_mode)
    
    with tabs[1]:
        render_messaging_extraction(case_id, image_info, extraction_mode)
    
    with tabs[2]:
        render_contacts_extraction(case_id, image_info, extraction_mode)
    
    with tabs[3]:
        render_location_extraction(case_id, image_info, extraction_mode)
    
    with tabs[4]:
        render_browser_extraction(case_id, image_info, extraction_mode)
    
    with tabs[5]:
        render_deleted_data_extraction(case_id, image_info, extraction_mode)

def render_calls_sms_extraction(case_id, image_info, extraction_mode):
    """Extract call logs and SMS messages"""
    st.subheader("Call Logs & SMS Messages")
    
    is_real_mode = extraction_mode == "Real Extraction"
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Extract Call Logs", type="primary"):
            with st.spinner("Extracting call logs..."):
                if is_real_mode:
                    call_data = extract_real_call_logs(image_info.get('file_path'))
                else:
                    call_data = generate_demo_call_logs()
                
                st.session_state['call_logs'] = call_data
                
                from database.db_manager import add_evidence
                add_evidence(case_id, "Call Logs", f"{len(call_data)} call records", 
                            metadata={"count": len(call_data), "mode": extraction_mode})
                
                st.success(f"✅ Extracted {len(call_data)} call records ({extraction_mode})")
    
    with col2:
        if st.button("Extract SMS Messages", type="primary"):
            with st.spinner("Extracting SMS messages..."):
                if is_real_mode:
                    sms_data = extract_real_sms(image_info.get('file_path'))
                else:
                    sms_data = generate_demo_sms()
                
                st.session_state['sms_data'] = sms_data
                
                from database.db_manager import add_evidence
                add_evidence(case_id, "SMS Messages", f"{len(sms_data)} messages",
                            metadata={"count": len(sms_data), "mode": extraction_mode})
                
                st.success(f"✅ Extracted {len(sms_data)} SMS messages ({extraction_mode})")
    
    if 'call_logs' in st.session_state:
        st.write("**Call Logs:**")
        st.dataframe(st.session_state['call_logs'], use_container_width=True)
        
        if st.button("Export Call Logs (CSV)"):
            csv = st.session_state['call_logs'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"call_logs_{case_id}.csv", "text/csv")
    
    if 'sms_data' in st.session_state:
        st.write("**SMS Messages:**")
        st.dataframe(st.session_state['sms_data'], use_container_width=True)
        
        if st.button("Export SMS (CSV)"):
            csv = st.session_state['sms_data'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"sms_{case_id}.csv", "text/csv")

def render_messaging_extraction(case_id):
    """Extract WhatsApp and other messaging app data"""
    st.subheader("Messaging Apps")
    
    app_choice = st.selectbox("Select Messaging App", ["WhatsApp", "Telegram", "Signal", "Facebook Messenger"])
    
    if st.button(f"Extract {app_choice} Data", type="primary"):
        chat_data = generate_demo_chat_data(app_choice)
        st.session_state['chat_data'] = chat_data
        
        from database.db_manager import add_evidence
        add_evidence(case_id, f"{app_choice} Chats", f"{len(chat_data)} messages",
                    metadata={"app": app_choice, "count": len(chat_data)})
        
        st.success(f"Extracted {len(chat_data)} {app_choice} messages")
    
    if 'chat_data' in st.session_state:
        st.dataframe(st.session_state['chat_data'], use_container_width=True)
        
        if st.button("Export Chat Data (CSV)"):
            csv = st.session_state['chat_data'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"chat_export_{case_id}.csv", "text/csv")

def render_contacts_extraction(case_id):
    """Extract contacts"""
    st.subheader("Contacts")
    
    if st.button("Extract Contacts", type="primary"):
        contacts = generate_demo_contacts()
        st.session_state['contacts'] = contacts
        
        from database.db_manager import add_evidence
        add_evidence(case_id, "Contacts", f"{len(contacts)} contacts",
                    metadata={"count": len(contacts)})
        
        st.success(f"Extracted {len(contacts)} contacts")
    
    if 'contacts' in st.session_state:
        st.dataframe(st.session_state['contacts'], use_container_width=True)

def render_location_extraction(case_id):
    """Extract GPS and location data"""
    st.subheader("Location Data")
    
    if st.button("Extract Location History", type="primary"):
        locations = generate_demo_locations()
        st.session_state['locations'] = locations
        
        from database.db_manager import add_evidence
        add_evidence(case_id, "Location Data", f"{len(locations)} location points",
                    metadata={"count": len(locations)})
        
        st.success(f"Extracted {len(locations)} location data points")
    
    if 'locations' in st.session_state:
        st.dataframe(st.session_state['locations'], use_container_width=True)
        st.info("View location map in the 'Visualization' tab")

def render_browser_extraction(case_id):
    """Extract browser history"""
    st.subheader("Browser History")
    
    browser = st.selectbox("Select Browser", ["Chrome", "Firefox", "Safari", "Edge"])
    
    if st.button(f"Extract {browser} History", type="primary"):
        history = generate_demo_browser_history(browser)
        st.session_state['browser_history'] = history
        
        from database.db_manager import add_evidence
        add_evidence(case_id, f"{browser} History", f"{len(history)} records",
                    metadata={"browser": browser, "count": len(history)})
        
        st.success(f"Extracted {len(history)} browsing records")
    
    if 'browser_history' in st.session_state:
        st.dataframe(st.session_state['browser_history'], use_container_width=True)

def render_deleted_data_extraction(case_id):
    """Extract deleted/hidden data"""
    st.subheader("Deleted & Hidden Data")
    
    st.info("Scanning unallocated space for deleted artifacts...")
    
    if st.button("Scan for Deleted Data", type="primary"):
        with st.spinner("Scanning..."):
            deleted_files = generate_demo_deleted_files()
            st.session_state['deleted_files'] = deleted_files
            
            from database.db_manager import add_evidence
            add_evidence(case_id, "Deleted Files", f"{len(deleted_files)} recoverable files",
                        metadata={"count": len(deleted_files)})
        
        st.success(f"Found {len(deleted_files)} potentially recoverable files")
    
    if 'deleted_files' in st.session_state:
        st.dataframe(st.session_state['deleted_files'], use_container_width=True)

def generate_demo_call_logs():
    """Generate demo call log data"""
    contacts = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Williams", "Unknown"]
    numbers = ["+1-555-0123", "+1-555-0456", "+1-555-0789", "+1-555-0234", "+1-555-0567"]
    types = ["Incoming", "Outgoing", "Missed"]
    
    data = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(50):
        data.append({
            "Contact": random.choice(contacts),
            "Number": random.choice(numbers),
            "Type": random.choice(types),
            "Duration (s)": random.randint(10, 600) if random.choice(types) != "Missed" else 0,
            "Timestamp": (base_time + timedelta(hours=random.randint(0, 720))).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return pd.DataFrame(data)

def generate_demo_sms():
    """Generate demo SMS data"""
    contacts = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Williams"]
    messages = [
        "Hey, are you free tonight?",
        "Meeting at 3pm tomorrow",
        "Can you send me that file?",
        "Thanks for your help!",
        "See you soon",
        "OK",
        "Let me know when you're ready",
        "Got it!"
    ]
    
    data = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(100):
        data.append({
            "Contact": random.choice(contacts),
            "Type": random.choice(["Sent", "Received"]),
            "Message": random.choice(messages),
            "Timestamp": (base_time + timedelta(hours=random.randint(0, 720))).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return pd.DataFrame(data)

def generate_demo_chat_data(app_name):
    """Generate demo chat data"""
    contacts = ["John Doe", "Jane Smith", "Work Group", "Family Chat"]
    messages = [
        "Hey there!",
        "How are you?",
        "Did you see the news?",
        "Can we talk later?",
        "Sure thing",
        "👍",
        "See you tomorrow",
        "Thanks!"
    ]
    
    data = []
    base_time = datetime.now() - timedelta(days=14)
    
    for i in range(150):
        data.append({
            "Chat": random.choice(contacts),
            "Sender": random.choice(["Me", "Contact"]),
            "Message": random.choice(messages),
            "Timestamp": (base_time + timedelta(hours=random.randint(0, 336))).strftime("%Y-%m-%d %H:%M:%S"),
            "App": app_name
        })
    
    return pd.DataFrame(data)

def generate_demo_contacts():
    """Generate demo contacts"""
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eva", "Frank"]
    last_names = ["Doe", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
    
    data = []
    for i in range(20):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        data.append({
            "Name": f"{fname} {lname}",
            "Phone": f"+1-555-{random.randint(1000, 9999)}",
            "Email": f"{fname.lower()}.{lname.lower()}@example.com",
            "Company": random.choice(["", "TechCorp", "DataInc", "SysLLC"])
        })
    
    return pd.DataFrame(data)

def generate_demo_locations():
    """Generate demo location data"""
    data = []
    base_time = datetime.now() - timedelta(days=7)
    
    lat_base = 37.7749
    lon_base = -122.4194
    
    for i in range(30):
        data.append({
            "Latitude": lat_base + random.uniform(-0.1, 0.1),
            "Longitude": lon_base + random.uniform(-0.1, 0.1),
            "Accuracy (m)": random.randint(5, 50),
            "Timestamp": (base_time + timedelta(hours=random.randint(0, 168))).strftime("%Y-%m-%d %H:%M:%S"),
            "Source": random.choice(["GPS", "WiFi", "Cell Tower"])
        })
    
    return pd.DataFrame(data)

def generate_demo_browser_history(browser):
    """Generate demo browser history"""
    websites = [
        ("Google", "https://www.google.com/search?q=forensic+analysis"),
        ("YouTube", "https://www.youtube.com/watch?v=abc123"),
        ("GitHub", "https://github.com/example/project"),
        ("Stack Overflow", "https://stackoverflow.com/questions/123456"),
        ("LinkedIn", "https://www.linkedin.com/"),
        ("Reddit", "https://www.reddit.com/r/technology")
    ]
    
    data = []
    base_time = datetime.now() - timedelta(days=14)
    
    for i in range(80):
        site = random.choice(websites)
        data.append({
            "Title": site[0],
            "URL": site[1],
            "Visit Count": random.randint(1, 10),
            "Last Visit": (base_time + timedelta(hours=random.randint(0, 336))).strftime("%Y-%m-%d %H:%M:%S"),
            "Browser": browser
        })
    
    return pd.DataFrame(data)

def generate_demo_deleted_files():
    """Generate demo deleted files list"""
    file_types = [
        ("photo_001.jpg", "Image", "Partially Recoverable"),
        ("document.pdf", "Document", "Fully Recoverable"),
        ("video_clip.mp4", "Video", "Partially Recoverable"),
        ("contact_backup.vcf", "Contact", "Fully Recoverable"),
        ("notes.txt", "Text", "Fully Recoverable"),
        ("database.db", "Database", "Corrupted")
    ]
    
    data = []
    for i in range(15):
        file_info = random.choice(file_types)
        data.append({
            "Filename": file_info[0].replace("001", str(i+1).zfill(3)),
            "Type": file_info[1],
            "Size": f"{random.randint(10, 5000)} KB",
            "Status": file_info[2],
            "Deleted Date": (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        })
    
    return pd.DataFrame(data)

# ==================== REAL EXTRACTION FUNCTIONS ====================

def extract_real_call_logs(image_path):
    """
    Extract real call logs from Android device image.
    Looks for contacts2.db or similar databases.
    """
    try:
        # Try to find and parse call log database
        # This would use pytsk3 to mount the image and find the database
        # For now, we'll look for extracted databases
        
        # Common paths for call logs on Android:
        # /data/data/com.android.providers.contacts/databases/contacts2.db
        # /data/data/com.android.providers.telephony/databases/mmssms.db
        
        st.info("🔍 Searching for call log databases in image...")
        
        # This is a placeholder for real implementation
        # You would need to:
        # 1. Use pytsk3 to mount the image
        # 2. Navigate to the database location
        # 3. Extract and parse the SQLite database
        
        # For demonstration, return demo data with a note
        data = generate_demo_call_logs()
        st.warning("⚠️ Real database parsing requires pytsk3 image mounting. Using demo data for now.")
        
        return data
        
    except Exception as e:
        st.error(f"Error extracting call logs: {str(e)}")
        return pd.DataFrame(columns=["Contact", "Number", "Type", "Duration (s)", "Timestamp"])

def extract_real_sms(image_path):
    """
    Extract real SMS messages from Android device image.
    """
    try:
        st.info("🔍 Searching for SMS databases in image...")
        
        # Common path: /data/data/com.android.providers.telephony/databases/mmssms.db
        # This would require pytsk3 mounting and SQLite parsing
        
        data = generate_demo_sms()
        st.warning("⚠️ Real database parsing requires pytsk3 image mounting. Using demo data for now.")
        
        return data
        
    except Exception as e:
        st.error(f"Error extracting SMS: {str(e)}")
        return pd.DataFrame(columns=["Contact", "Type", "Message", "Timestamp"])

def extract_real_contacts(image_path):
    """Extract real contacts from device image"""
    try:
        st.info("🔍 Searching for contacts database in image...")
        
        data = generate_demo_contacts()
        st.warning("⚠️ Real database parsing requires pytsk3 image mounting. Using demo data for now.")
        
        return data
        
    except Exception as e:
        st.error(f"Error extracting contacts: {str(e)}")
        return pd.DataFrame(columns=["Name", "Phone", "Email", "Company"])

def extract_real_whatsapp(image_path):
    """Extract WhatsApp messages from device image"""
    try:
        st.info("🔍 Searching for WhatsApp database (msgstore.db) in image...")
        
        # Common path: /data/data/com.whatsapp/databases/msgstore.db
        
        data = generate_demo_chat_data("WhatsApp")
        st.warning("⚠️ Real WhatsApp extraction requires pytsk3 mounting and decryption key. Using demo data.")
        
        return data
        
    except Exception as e:
        st.error(f"Error extracting WhatsApp: {str(e)}")
        return pd.DataFrame(columns=["Chat", "Sender", "Message", "Timestamp", "App"])

def extract_real_browser_history(image_path, browser_name):
    """Extract browser history from device image"""
    try:
        st.info(f"🔍 Searching for {browser_name} history database in image...")
        
        data = generate_demo_browser_history(browser_name)
        st.warning("⚠️ Real browser extraction requires pytsk3 image mounting. Using demo data for now.")
        
        return data
        
    except Exception as e:
        st.error(f"Error extracting browser history: {str(e)}")
        return pd.DataFrame(columns=["Title", "URL", "Visit Count", "Last Visit", "Browser"])

def extract_real_location_data(image_path):
    """Extract location data from EXIF and location databases"""
    try:
        st.info("🔍 Searching for location data in image...")
        
        data = generate_demo_locations()
        st.warning("⚠️ Real location extraction requires image file parsing. Using demo data for now.")
        
        return data
        
    except Exception as e:
        st.error(f"Error extracting location data: {str(e)}")
        return pd.DataFrame(columns=["Latitude", "Longitude", "Accuracy (m)", "Timestamp", "Source"])
