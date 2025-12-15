import streamlit as st
import os
import math
import pandas as pd
from datetime import datetime

# Try to import pytsk3, handle if missing
try:
    import pytsk3
    HAS_PYTSK3 = True
except ImportError:
    HAS_PYTSK3 = False

def get_file_type(entry):
    """Get human readable file type"""
    if not entry.info.meta:
        return "Unknown"
    
    if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
        return "DIR"
    elif entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
        return "FILE"
    else:
        return "OTHER"

def list_directory_contents(image_path, offset, path="/"):
    """List contents of a directory using pytsk3"""
    results = []
    try:
        img_info = pytsk3.Img_Info(image_path)
        try:
            fs_info = pytsk3.FS_Info(img_info, offset=offset)
        except Exception:
            # If offset points to start of image or valid but not FS, try opening without offset or detect
             fs_info = pytsk3.FS_Info(img_info)

        directory = fs_info.open_dir(path)
        
        for entry in directory:
            try:
                if entry.info.name.name in [b".", b".."]:
                    continue
                
                name = entry.info.name.name.decode('utf-8', 'replace')
                file_type = get_file_type(entry)
                size = entry.info.meta.size if entry.info.meta else 0
                inode = entry.info.meta.addr if entry.info.meta else 0
                
                # Get timestamps if available
                created = ""
                if entry.info.meta and entry.info.meta.crtime:
                    try:
                        created = datetime.fromtimestamp(entry.info.meta.crtime).strftime('%Y-%m-%d %H:%M:%S')
                    except: pass
                
                results.append({
                    "Name": name,
                    "Type": file_type,
                    "Size": size,
                    "Inode": inode,
                    "Created": created
                })
            except Exception:
                continue
                
    except Exception as e:
        st.error(f"Error listing directory: {str(e)}")
        
    return pd.DataFrame(results)

def extract_file(image_path, offset, path, output_path):
    """Extract a specific file"""
    try:
        img_info = pytsk3.Img_Info(image_path)
        fs_info = pytsk3.FS_Info(img_info, offset=offset)
        file_entry = fs_info.open(path)
        
        with open(output_path, "wb") as outfile:

            # Copy file data
            # Reading in chunks 
            offset_read = 0
            size = file_entry.info.meta.size
            BUFF_SIZE = 1024 * 1024
            
            while offset_read < size:
                available_to_read = min(BUFF_SIZE, size - offset_read)
                data = file_entry.read_random(offset_read, available_to_read)
                if not data: break
                outfile.write(data)
                offset_read += len(data)
                
        return True, "Extraction successful"
    except Exception as e:
        return False, str(e)

def render_file_parser(case_id, image_info=None):
    """Render the file system parser interface"""
    st.header("🗂️ File System Parser")
    
    if not image_info:
        st.warning("⚠️ Please upload a device image first in the 'Image Input' tab")
        return
    
    st.info(f"Analyzing file system from: **{image_info.get('filename', 'Unknown')}**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**File Size:** {image_info.get('size', 0):.2f} MB")
    with col2:
        if str(case_id).lower() in ["democase", "demo-case"]:
            demo_mode = st.checkbox("Demo Mode", value=True, help="Toggle between demo data and real file system parsing")
        else:
            demo_mode = False
    
    if demo_mode:
        render_demo_mode()
    else:
        render_real_parsing(case_id, image_info)

def render_demo_mode():
    st.subheader("📂 Detected Partitions (Demo)")   
    
    partitions = [
        {"name": "boot", "type": "ext4", "size": "32 MB", "files": 150},
        {"name": "system", "type": "ext4", "size": "2.8 GB", "files": 4521},
        {"name": "userdata", "type": "ext4", "size": "12.5 GB", "files": 8934},
        {"name": "cache", "type": "ext4", "size": "512 MB", "files": 342},
    ]
    
    for partition in partitions:
        with st.expander(f"📁 Partition: {partition['name']} ({partition['type']}) - {partition['size']}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Type", partition['type'])
            col2.metric("Size", partition['size'])
            col3.metric("Files", partition['files'])
            
            if st.button(f"Browse {partition['name']}", key=f"browse_{partition['name']}"):
                st.session_state['selected_partition'] = partition['name']
    
    st.divider()
    
    if 'selected_partition' in st.session_state:
        partition_name = st.session_state['selected_partition']
        st.subheader(f"📂 Browsing: /{partition_name}")
        
        key_directories = get_key_directories(partition_name)
        
        for directory in key_directories:
            with st.expander(f"📁 {directory['path']}"):
                st.write(f"**Description:** {directory['description']}")
                st.write(f"**Files:** {directory['file_count']}")
                st.write(f"**Forensic Value:** {directory['value']}")
                
                if st.button(f"Extract Data", key=f"extract_{directory['path']}"):
                    st.success(f"✅ Marked for extraction: {directory['path']}")

def render_real_parsing(case_id, image_info):
    if not HAS_PYTSK3:
        st.error("❌ pytsk3 library not installed. Please install it to use real parsing.")
        return

    st.subheader("📂 Real File System Parsing")
    
    image_path = image_info.get('file_path', '')
    if not image_path or not os.path.exists(image_path):
        st.error("❌ Image file not found.")
        return

    # Initialize session state for browsing
    if 'fs_current_path' not in st.session_state:
        st.session_state['fs_current_path'] = "/"
    if 'fs_offset' not in st.session_state:
        st.session_state['fs_offset'] = 0

    # Partition Table Analysis
    if st.button("🔍 Scan for Partitions", type="primary"):
        with st.spinner("Scanning partition table..."):
            try:
                img_info = pytsk3.Img_Info(image_path)
                volume_info = pytsk3.Volume_Info(img_info)
                
                partitions = []
                for p in volume_info:
                    if p.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                        partitions.append({
                            "Address": p.addr,
                            "Start": p.start,
                            "Length": p.len,
                            "Description": p.desc.decode('utf-8'),
                            "Offset_Bytes": p.start * 512
                        })
                st.session_state['partitions_found'] = partitions
                st.session_state['show_decryption'] = False
                st.success(f"Found {len(partitions)} partitions")
            except Exception as e:
                st.session_state['show_decryption'] = True
                err_msg = str(e)
                if "Volume_Info" in err_msg:
                    st.warning("⚠️ Partition table not found. Volume might be encrypted or raw.")
                else:
                    st.error(f"Error scanning partitions: {err_msg}")
                
                # Fallback: maybe it's a raw filesystem
                st.session_state['partitions_found'] = [{"Address": 0, "Start": 0, "Length": 0, "Description": "Raw/Unknown", "Offset_Bytes": 0}]

    # Decryption Interface (Persistent)
    if st.session_state.get('show_decryption', False):
        with st.expander("🔐 Decryption / Encrypted Volume Analysis", expanded=True):
            st.info("If this is an encrypted image, perform decryption here to unlock analysis.")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                enc_method = st.selectbox("Encryption", ["BitLocker", "LUKS", "VeraCrypt", "FileVault"])
            with c2:
                password = st.text_input("Password / Recovery Key", type="password")
                
            if st.button("🔓 Decrypt & Mount Image"):
                if not password:
                    st.warning("Please enter a password.")
                else:
                    st.info(f"Attempting {enc_method} decryption on image...")
                    # Simulation of decryption process
                    import time
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)
                        progress_bar.progress(i + 1)
                    
                    # Since we don't have actual decryption binaries:
                    if str(case_id).lower() in ["democase", "demo-case"]:
                        st.success("Decryption successful (Demo)! Volume mounted.")
                        st.session_state['show_decryption'] = False
                        # In demo, we could fake a partition list update here if we wanted
                    else:
                        st.error(f"Decryption failed: Native decryption tools for {enc_method} (e.g., dislocker, bde-mount) are not installed or configured in this environment.")
                        st.caption("To analyze this file, please decrypt it externally and upload the decrypted .dd/.img file.")

    if 'partitions_found' in st.session_state:
        st.write("### Select Partition to Browse")
        
        # Create a selection list
        opts = {f"{p['Description']} (Start: {p['Start']})": p['Offset_Bytes'] for p in st.session_state['partitions_found']}
        selected_desc = st.selectbox("Partition", list(opts.keys()))
        selected_offset = opts[selected_desc]
        
        if selected_offset != st.session_state['fs_offset']:
            st.session_state['fs_offset'] = selected_offset
            st.session_state['fs_current_path'] = "/" # Reset path on partition change

        st.divider()
        
        # File Browser
        current_path = st.session_state['fs_current_path']
        st.markdown(f"**Current Path:** `{current_path}`")
        
        # Navigation
        col_nav1, col_nav2 = st.columns([1, 4])
        with col_nav1:
            if st.button("⬆️ Up"):
                parent = os.path.dirname(current_path)
                if parent == current_path: parent = "/" 
                # fix for root 
                if not parent.endswith("/") and parent != "/": parent = parent 
                # simplified parent logic
                if current_path != "/":
                     st.session_state['fs_current_path'] = os.path.dirname(current_path.rstrip("/"))
                     if st.session_state['fs_current_path'] == "": st.session_state['fs_current_path'] = "/"
                     st.rerun()

        # List files
        with st.spinner(f"Listing {current_path}..."):
            df_files = list_directory_contents(image_path, st.session_state['fs_offset'], current_path)
        
        if not df_files.empty:
            # Display as interactive table? 
            # We want buttons. Dataframe with selection is okay, but explicit buttons are better for actions.
            
            # Filter options
            show_dirs = st.checkbox("Show Directories", value=True)
            show_files = st.checkbox("Show Files", value=True)
            
            # Sort by name
            df_display = df_files
            if not show_dirs: df_display = df_display[df_display['Type'] != 'DIR']
            if not show_files: df_display = df_display[df_display['Type'] != 'FILE']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Action selector
            st.write("### Actions")
            selected_file_name = st.selectbox("Select File/Folder", df_display['Name'].tolist())
            
            selected_row = df_display[df_display['Name'] == selected_file_name].iloc[0]
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if selected_row['Type'] == 'DIR':
                    if st.button(f"Open Folder: {selected_file_name}"):
                        new_path = os.path.join(current_path, selected_file_name).replace("\\", "/")
                        st.session_state['fs_current_path'] = new_path
                        st.rerun()
                else:
                    if st.button(f"Extract File: {selected_file_name}"):
                        # Create extraction dir
                        extract_dir = os.path.join(os.getcwd(), "extracted_evidence", case_id)
                        os.makedirs(extract_dir, exist_ok=True)
                        output_file = os.path.join(extract_dir, selected_file_name)
                        
                        full_file_path = os.path.join(current_path, selected_file_name).replace("\\", "/")
                        
                        success, msg = extract_file(
                            image_path, 
                            st.session_state['fs_offset'], 
                            full_file_path, 
                            output_file
                        )
                        
                        if success:
                            st.success(f"File extracted to: {output_file}")
                            # Add to evidence DB
                            from database.db_manager import add_evidence
                            add_evidence(case_id, "Extracted File", selected_file_name, output_file, "", {"source_path": full_file_path})
                        else:
                            st.error(f"Extraction failed: {msg}")

        else:
            st.info("Directory is empty or could not be read")

def get_key_directories(partition):
    """Get forensically important directories based on partition type (Demo)"""
    if partition == "userdata":
        return [
            {
                "path": "/data/data/com.whatsapp/databases",
                "description": "WhatsApp chat databases",
                "file_count": 45,
                "value": "High"
            },
            {
                "path": "/data/data/com.android.providers.contacts/databases",
                "description": "Contacts database",
                "file_count": 12,
                "value": "High"
            },
            {
                "path": "/data/data/com.android.providers.telephony/databases",
                "description": "SMS and call logs",
                "file_count": 8,
                "value": "Critical"
            },
            {
                "path": "/data/media/DCIM",
                "description": "Camera photos and videos",
                "file_count": 532,
                "value": "Medium"
            },
            {
                "path": "/data/data/com.android.chrome/app_chrome/Default",
                "description": "Chrome browser history and cache",
                "file_count": 234,
                "value": "Medium"
            },
            {
                "path": "/data/system/users/0",
                "description": "User account information",
                "file_count": 23,
                "value": "High"
            }
        ]
    elif partition == "system":
        return [
            {
                "path": "/system/build.prop",
                "description": "System build properties",
                "file_count": 1,
                "value": "Low"
            }
        ]
    else:
        return []
