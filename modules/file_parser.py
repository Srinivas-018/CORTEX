"""
File System Parser Module
Parses file systems from device images using pytsk3
"""

import streamlit as st
import os
import math

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
        demo_mode = st.checkbox("Demo Mode", value=True, help="Toggle between demo data and real file system parsing")
    
    if demo_mode:
        st.subheader("📂 Detected Partitions")
        
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
    
    else:
        st.subheader("📂 Real File System Parsing")
        st.info("🔍 Attempting to parse real file system using pytsk3...")
        
        if st.button("Parse File System", type="primary"):
            with st.spinner("Parsing file system..."):
                try:
                    import pytsk3
                    
                    image_path = image_info.get('file_path', '')
                    
                    if not image_path or not os.path.exists(image_path):
                        st.error("❌ Image file not found. Please verify and process the image first.")
                    else:
                        # Try to open the image
                        img_info = pytsk3.Img_Info(image_path)
                        st.success(f"✅ Successfully opened image file: {image_path}")
                        st.write(f"**Image Size:** {img_info.get_size() / (1024*1024*1024):.2f} GB")
                        
                        # Try to get volume info
                        try:
                            volume_info = pytsk3.Volume_Info(img_info)
                            st.write(f"**Partitions Found:** {len(volume_info)}")
                            
                            partition_data = []
                            for partition in volume_info:
                                if partition.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                                    partition_data.append({
                                        "Index": partition.addr,
                                        "Start": partition.start,
                                        "Length": partition.len,
                                        "Description": partition.desc.decode('utf-8', errors='ignore'),
                                        "Size (MB)": (partition.len * 512) / (1024 * 1024)
                                    })
                            
                            if partition_data:
                                import pandas as pd
                                st.dataframe(pd.DataFrame(partition_data), use_container_width=True)
                            else:
                                st.warning("No allocated partitions found")
                                
                        except Exception as e:
                            st.warning(f"Could not parse partitions: {str(e)}")
                            st.info("This may be a raw file system image without partition table")
                        
                except ImportError:
                    st.error("❌ pytsk3 library not available")
                    st.info("Install with: pip install pytsk3")
                except Exception as e:
                    st.error(f"❌ Error parsing file system: {str(e)}")
                    st.info("The image file may be corrupted or in an unsupported format")
        
        with st.expander("ℹ️ About Real File System Parsing"):
            st.markdown("""
            **Real parsing capabilities:**
            - Extract partition table information
            - Browse file system directories
            - Extract individual files
            - Recover deleted files
            
            **Requirements:**
            - pytsk3 library installed
            - Valid forensic image file (.img, .dd, .raw)
            - Sufficient disk space for extraction
            
            **Limitations:**
            - Encrypted file systems require decryption keys
            - Some proprietary formats may not be supported
            - Large images may take time to process
            """)

def get_key_directories(partition):
    """Get forensically important directories based on partition type"""

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
