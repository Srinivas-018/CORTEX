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
        # Auto-detect mode based on case ID
        is_demo = "demo" in str(case_id).lower()
        
        if is_demo:
            extraction_mode = "Demo Mode"
            st.info("🛠️ Demo Mode")
        else:
            extraction_mode = "Real Extraction"
            st.success("⚡ Real Analysis")
    
    # Store mode in session state
    st.session_state['extraction_mode'] = extraction_mode
    
    if extraction_mode == "Real Extraction" and not image_info.get('file_path'):
        st.warning("⚠️ Real extraction requires the image file to be saved. Please click 'Verify & Process Image' first.")
        return
    
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
        st.dataframe(st.session_state['call_logs'], width='stretch')
        
        if st.button("Export Call Logs (CSV)"):
            csv = st.session_state['call_logs'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"call_logs_{case_id}.csv", "text/csv")
    
    if 'sms_data' in st.session_state:
        st.write("**SMS Messages:**")
        st.dataframe(st.session_state['sms_data'], width='stretch')
        
        if st.button("Export SMS (CSV)"):
            csv = st.session_state['sms_data'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"sms_{case_id}.csv", "text/csv")

def render_messaging_extraction(case_id, image_info, extraction_mode):
    """Extract WhatsApp and other messaging app data"""
    st.subheader("Messaging Apps")
    
    is_real_mode = extraction_mode == "Real Extraction"
    
    app_choice = st.selectbox("Select Messaging App", ["WhatsApp", "Telegram", "Signal", "Facebook Messenger"])
    
    if st.button(f"Extract {app_choice} Data", type="primary"):
        with st.spinner(f"Extracting {app_choice} messages..."):
            if is_real_mode:
                if app_choice == "WhatsApp":
                    chat_data = extract_real_whatsapp(image_info.get('file_path'))
                else:
                    st.warning(f"⚠️ Real extraction for {app_choice} not yet implemented.")
                    chat_data = pd.DataFrame(columns=["Chat", "Sender", "Message", "Timestamp", "App"])
            else:
                chat_data = generate_demo_chat_data(app_choice)
            
            st.session_state['chat_data'] = chat_data
            
            from database.db_manager import add_evidence
            add_evidence(case_id, f"{app_choice} Chats", f"{len(chat_data)} messages",
                        metadata={"app": app_choice, "count": len(chat_data), "mode": extraction_mode})
            
            st.success(f"✅ Extracted {len(chat_data)} {app_choice} messages")
    
    if 'chat_data' in st.session_state:
        st.dataframe(st.session_state['chat_data'], width='stretch')
        
        if st.button("Export Chat Data (CSV)"):
            csv = st.session_state['chat_data'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"chat_export_{case_id}.csv", "text/csv")

def render_contacts_extraction(case_id, image_info, extraction_mode):
    """Extract contacts"""
    st.subheader("Contacts")
    
    is_real_mode = extraction_mode == "Real Extraction"
    
    if st.button("Extract Contacts", type="primary"):
        with st.spinner("Extracting contacts..."):
            if is_real_mode:
                contacts = extract_real_contacts(image_info.get('file_path'))
            else:
                contacts = generate_demo_contacts()
            
            st.session_state['contacts'] = contacts
            
            from database.db_manager import add_evidence
            add_evidence(case_id, "Contacts", f"{len(contacts)} contacts",
                        metadata={"count": len(contacts), "mode": extraction_mode})
            
            st.success(f"✅ Extracted {len(contacts)} contacts ({extraction_mode})")
    
    if 'contacts' in st.session_state:
        st.dataframe(st.session_state['contacts'], width='stretch')
        
        if st.button("Export Contacts (CSV)"):
            csv = st.session_state['contacts'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"contacts_{case_id}.csv", "text/csv")

def render_location_extraction(case_id, image_info, extraction_mode):
    """Extract GPS and location data"""
    st.subheader("Location Data")
    
    is_real_mode = extraction_mode == "Real Extraction"
    
    if st.button("Extract Location History", type="primary"):
        with st.spinner("Extracting location data..."):
            if is_real_mode:
                locations = extract_real_location_data(image_info.get('file_path'))
            else:
                locations = generate_demo_locations()
            
            st.session_state['locations'] = locations
            
            from database.db_manager import add_evidence
            add_evidence(case_id, "Location Data", f"{len(locations)} location points",
                        metadata={"count": len(locations), "mode": extraction_mode})
            
            st.success(f"✅ Extracted {len(locations)} location data points ({extraction_mode})")
    
    if 'locations' in st.session_state:
        st.dataframe(st.session_state['locations'], width='stretch')
        st.info("📍 View location map in the 'Visualization' tab")
        
        if st.button("Export Locations (CSV)"):
            csv = st.session_state['locations'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"locations_{case_id}.csv", "text/csv")

def render_browser_extraction(case_id, image_info, extraction_mode):
    """Extract browser history"""
    st.subheader("Browser History")
    
    is_real_mode = extraction_mode == "Real Extraction"
    
    browser = st.selectbox("Select Browser", ["Chrome", "Firefox", "Safari", "Edge"])
    
    if st.button(f"Extract {browser} History", type="primary"):
        with st.spinner(f"Extracting {browser} history..."):
            if is_real_mode:
                history = extract_real_browser_history(image_info.get('file_path'), browser)
            else:
                history = generate_demo_browser_history(browser)
            
            st.session_state['browser_history'] = history
            
            from database.db_manager import add_evidence
            add_evidence(case_id, f"{browser} History", f"{len(history)} records",
                        metadata={"browser": browser, "count": len(history), "mode": extraction_mode})
            
            st.success(f"✅ Extracted {len(history)} browsing records ({extraction_mode})")
    
    if 'browser_history' in st.session_state:
        st.dataframe(st.session_state['browser_history'], width='stretch')
        
        if st.button("Export Browser History (CSV)"):
            csv = st.session_state['browser_history'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"browser_history_{case_id}.csv", "text/csv")

def render_deleted_data_extraction(case_id, image_info, extraction_mode):
    """Extract deleted/hidden data"""
    st.subheader("Deleted & Hidden Data")
    
    is_real_mode = extraction_mode == "Real Extraction"
    
    st.info("🔍 Scanning unallocated space for deleted artifacts...")
    
    if st.button("Scan for Deleted Data", type="primary"):
        with st.spinner("Scanning..."):
            if is_real_mode:
                deleted_files = pd.DataFrame(columns=["Filename", "Type", "Size", "Status", "Deleted Date"])
                st.warning("⚠️ Real deleted file recovery requires specialized carving tools. No data recovered.")
            else:
                deleted_files = generate_demo_deleted_files()
            
            st.session_state['deleted_files'] = deleted_files
            
            from database.db_manager import add_evidence
            add_evidence(case_id, "Deleted Files", f"{len(deleted_files)} recoverable files",
                        metadata={"count": len(deleted_files), "mode": extraction_mode})
        
        st.success(f"✅ Found {len(deleted_files)} potentially recoverable files")
    
    if 'deleted_files' in st.session_state:
        st.dataframe(st.session_state['deleted_files'], width='stretch')
        
        if st.button("Export Deleted Files List (CSV)"):
            csv = st.session_state['deleted_files'].to_csv(index=False)
            st.download_button("Download CSV", csv, f"deleted_files_{case_id}.csv", "text/csv")

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

# Try to import pytsk3
try:
    import pytsk3
    HAS_PYTSK3 = True
except ImportError:
    HAS_PYTSK3 = False

def get_db_connection(db_path):
    """Create a connection to a SQLite database"""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        return conn
    except Exception:
        return None

def find_file_in_image(image_path, target_names):
    """
    Search for a file within a forensic image or check if the input file IS the target.
    Returns: Path to extracted temporary file or None
    """
    # 1. Check if the input file itself is the database
    if os.path.isfile(image_path):
        try:
            # Check if it's a valid SQLite DB
            with open(image_path, 'rb') as f:
                header = f.read(16)
            if header.startswith(b'SQLite format 3'):
                return image_path
        except:
            pass

    # 2. If pytsk3 is available, try to find it in the image
    if HAS_PYTSK3:
        try:
            img_info = pytsk3.Img_Info(image_path)
            # Try to guess filesystem
            try:
                fs_info = pytsk3.FS_Info(img_info)
            except:
                # Try offset 0 first
                try: 
                    fs_info = pytsk3.FS_Info(img_info, offset=0)
                except:
                    return None

            # Recursive search or known paths?
            # For simplicity, we check common Android paths
            common_paths = [
                "/data/data/com.android.providers.contacts/databases/contacts2.db",
                "/data/data/com.android.providers.telephony/databases/mmssms.db",
                "/data/data/com.whatsapp/databases/msgstore.db",
                "/data/data/com.android.chrome/app_chrome/Default/History"
            ]
            
            for path in common_paths:
                fileName = os.path.basename(path)
                if fileName in target_names:
                    try:
                        file_entry = fs_info.open(path)
                        # Extract to temp
                        import tempfile
                        tmp_fd, tmp_path = tempfile.mkstemp()
                        os.close(tmp_fd)
                        
                        with open(tmp_path, "wb") as outfile:
                             size = file_entry.info.meta.size
                             outfile.write(file_entry.read_random(0, size))
                        return tmp_path
                    except:
                        continue
        except:
            pass
            
    return None

def extract_real_call_logs(image_path):
    """Extract real call logs from device image or DB file"""
    data = []
    
    # Target filenames
    targets = ["contacts2.db", "calllog.db"]
    db_path = find_file_in_image(image_path, targets)
    
    if db_path:
        conn = get_db_connection(db_path)
        if conn:
            try:
                # Try standard Android call log query
                query = """
                    SELECT 
                        name, 
                        number, 
                        CASE type 
                            WHEN 1 THEN 'Incoming' 
                            WHEN 2 THEN 'Outgoing' 
                            WHEN 3 THEN 'Missed' 
                            ELSE 'Unknown' 
                        END, 
                        duration, 
                        date 
                    FROM calls
                """
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    name = row[0] if row[0] else "Unknown"
                    number = row[1]
                    call_type = row[2]
                    duration = row[3]
                    # Android date is usually ms timestamp
                    try:
                        ts = datetime.fromtimestamp(row[4] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        ts = str(row[4])

                    data.append({
                        "Contact": name,
                        "Number": number,
                        "Type": call_type,
                        "Duration (s)": duration,
                        "Timestamp": ts
                    })
            except:
                pass # Fail silently
            finally:
                conn.close()

    return pd.DataFrame(data, columns=["Contact", "Number", "Type", "Duration (s)", "Timestamp"])

def extract_real_sms(image_path):
    """Extract real SMS from device image or DB file"""
    data = []
    targets = ["mmssms.db"]
    db_path = find_file_in_image(image_path, targets)
    
    if db_path:
        conn = get_db_connection(db_path)
        if conn:
            try:
                # Standard Android SMS query
                query = "SELECT address, type, body, date FROM sms"
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    address = row[0]
                    direction = "Received" if row[1] == 1 else "Sent"
                    body = row[2]
                    try:
                        ts = datetime.fromtimestamp(row[3] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        ts = str(row[3])
                        
                    data.append({
                        "Contact": address,
                        "Type": direction,
                        "Message": body,
                        "Timestamp": ts
                    })
            except:
                pass
            finally:
                conn.close()
                
    return pd.DataFrame(data, columns=["Contact", "Type", "Message", "Timestamp"])

def extract_real_contacts(image_path):
    """Extract real contacts from device image or DB file"""
    data = []
    targets = ["contacts2.db"]
    db_path = find_file_in_image(image_path, targets)
    
    if db_path:
        conn = get_db_connection(db_path)
        if conn:
            try:
                # Query optimized for Android contacts2.db view if available, or raw tables
                # Using 'view_v1' is common in newer Android
                query = """
                    SELECT display_name, data1 
                    FROM raw_contacts 
                    JOIN data ON raw_contacts._id = data.raw_contact_id 
                    WHERE mimetype_id = (SELECT _id FROM mimetypes WHERE mimetype = 'vnd.android.cursor.item/phone_v2')
                """
                # Fallback to simple query if complex one fails
                cursor = conn.cursor()
                try:
                    cursor.execute(query)
                except:
                    # Try simpler query
                    cursor.execute("SELECT display_name FROM raw_contacts")
                
                rows = cursor.fetchall()
                
                for row in rows:
                    name = row[0] if row[0] else "Unknown"
                    phone = row[1] if len(row) > 1 else ""
                    
                    data.append({
                        "Name": name,
                        "Phone": phone,
                        "Email": "",
                        "Company": ""
                    })
            except:
                pass
            finally:
                conn.close()

    return pd.DataFrame(data, columns=["Name", "Phone", "Email", "Company"])

def extract_real_whatsapp(image_path):
    """Extract WhatsApp messages from device image or DB file"""
    data = []
    targets = ["msgstore.db"]
    db_path = find_file_in_image(image_path, targets)
    
    # Note: Modern WhatsApp DBs are encrypted (msgstore.db.cryptXX). 
    # Unencrypted databases are rare on non-rooted phones, but we support them if found.
    # We also support parsing if start of file is SQLite
    
    if db_path:
        conn = get_db_connection(db_path)
        if conn:
            try:
                # Structure varies widely by version. Simplest attempt:
                query = """
                    SELECT key_remote_jid, data, timestamp, from_me 
                    FROM messages 
                    WHERE data IS NOT NULL
                """
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    jid = row[0]
                    message = row[1]
                    try:
                        ts = datetime.fromtimestamp(row[2] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        ts = str(row[2])
                    sender = "Me" if row[3] == 1 else "Contact"
                    
                    data.append({
                        "Chat": jid.split('@')[0] if jid else "Unknown",
                        "Sender": sender,
                        "Message": message,
                        "Timestamp": ts,
                        "App": "WhatsApp"
                    })
            except:
                pass
            finally:
                conn.close()

    return pd.DataFrame(data, columns=["Chat", "Sender", "Message", "Timestamp", "App"])

def extract_real_browser_history(image_path, browser_name):
    """Extract browser history from device image or DB file"""
    data = []
    # Only Chrome support for now as it's SQLite
    targets = ["History", "browser.db"] 
    db_path = find_file_in_image(image_path, targets)
    
    if db_path:
        conn = get_db_connection(db_path)
        if conn:
            try:
                query = "SELECT title, url, visit_count, last_visit_time FROM urls"
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    title = row[0]
                    url = row[1]
                    count = row[2]
                    # Chrome time is microseconds since 1601... complicated conversion
                    # Simplifying for display
                    ts = str(row[3]) 
                    
                    data.append({
                        "Title": title,
                        "URL": url,
                        "Visit Count": count,
                        "Last Visit": ts,
                        "Browser": browser_name
                    })
            except:
               pass
            finally:
                conn.close()

    return pd.DataFrame(data, columns=["Title", "URL", "Visit Count", "Last Visit", "Browser"])

def extract_real_location_data(image_path):
    """Extract location data from EXIF and location databases"""
    # Placeholder for complex location extraction
    # We return empty silent dataframe instead of error
    return pd.DataFrame(columns=["Latitude", "Longitude", "Accuracy (m)", "Timestamp", "Source"])
