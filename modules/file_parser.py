"""
File System Parser Module
Parses file systems from device images using pytsk3
"""

import streamlit as st
import os
import sys
import logging

def ensure_pytsk3():
    """
    Ensures pytsk3 is available for file system parsing.
    Shows user-friendly error message with install instructions if not available.
    Returns True if pytsk3 is available, otherwise stops execution.
    """
    try:
        import pytsk3  # noqa: F401
        return True
    except ImportError as exc:
        install_hint = """pytsk3 is required for real file system parsing. Install with:

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y libtsk-dev
pip install pytsk3
```

**macOS (with Homebrew):**
```bash
brew install sleuthkit
pip install pytsk3
```

**Windows:**
```bash
# Install Visual C++ Build Tools first, then:
pip install pytsk3
```

**Docker/CI (Debian-based):**
```dockerfile
RUN apt-get update && apt-get install -y libtsk-dev && pip install pytsk3
```

For more information, visit: https://github.com/py4n6/pytsk
"""
        logging.error("pytsk3 import failed: %s", exc)
        
        try:
            st.error("⚠️ pytsk3 is required but not installed. Real file system parsing will not work.")
            st.markdown(f"**Installation Instructions:**\n{install_hint}")
            st.stop()
        except Exception:
            sys.stderr.write("ERROR: pytsk3 is required but not installed.\n")
            sys.stderr.write(install_hint + "\n")
            sys.exit(1)

# Ensure pytsk3 is available at module load time
ensure_pytsk3()

# Now import pytsk3 for use in this module
import pytsk3

def render_file_parser(case_id, image_info=None):
    """Render the file system parser interface"""
    st.header("File System Parser")
    
    if not image_info:
        st.warning("Please upload a device image first in the 'Image Input' tab")
        return
    
    st.info(f"Analyzing file system from: **{image_info.get('filename', 'Unknown')}**")
    
    demo_mode = st.checkbox("Use Demo Mode (Simulated Data)", value=True)
    
    if demo_mode:
        st.subheader("Detected Partitions")
        
        partitions = [
            {"name": "boot", "type": "ext4", "size": "32 MB", "files": 150},
            {"name": "system", "type": "ext4", "size": "2.8 GB", "files": 4521},
            {"name": "userdata", "type": "ext4", "size": "12.5 GB", "files": 8934},
            {"name": "cache", "type": "ext4", "size": "512 MB", "files": 342},
        ]
        
        for partition in partitions:
            with st.expander(f"Partition: {partition['name']} ({partition['type']}) - {partition['size']}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Type", partition['type'])
                col2.metric("Size", partition['size'])
                col3.metric("Files", partition['files'])
                
                if st.button(f"Browse {partition['name']}", key=f"browse_{partition['name']}"):
                    st.session_state['selected_partition'] = partition['name']
        
        st.divider()
        
        if 'selected_partition' in st.session_state:
            partition_name = st.session_state['selected_partition']
            st.subheader(f"Browsing: /{partition_name}")
            
            key_directories = get_key_directories(partition_name)
            
            for directory in key_directories:
                with st.expander(f"{directory['path']}"):
                    st.write(f"**Description:** {directory['description']}")
                    st.write(f"**Files:** {directory['file_count']}")
                    st.write(f"**Forensic Value:** {directory['value']}")
                    
                    if st.button(f"Extract Data", key=f"extract_{directory['path']}"):
                        st.success(f"Marked for extraction: {directory['path']}")
    
    else:
        st.info("🔍 Real file system parsing with pytsk3")
        
        if not image_info:
            st.warning("Please upload a device image first")
            return
        
        # TODO: Implement actual partition mounting and file extraction
        # This is where real pytsk3-based filesystem parsing would occur
        st.markdown("**Example pytsk3 usage:**")
        st.code("""
import pytsk3

# Open the disk image
img = pytsk3.Img_Info('/path/to/image.img')

# Access the volume system (partition table)
volume = pytsk3.Volume_Info(img)

# Iterate through partitions
for partition in volume:
    # Mount and analyze each partition
    # Extract files and directories
    pass
        """, language="python")
        
        st.info("💡 Real-time filesystem parsing implementation coming soon. For now, use Demo Mode.")


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
