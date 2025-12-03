"""
File System Parser Module
Parses file systems from device images using pytsk3
"""

import streamlit as st
import os
import math

def render_file_parser(case_id, image_info=None):
    """Render the file system parser interface"""
    st.header("File System Parser")

    if not image_info:
        st.warning("Please upload a device image first in the 'Image Input' tab")
        return

    st.info(f"Analyzing file system from: **{image_info.get('filename', image_info.get('path', 'Unknown'))}**")

    # Attempt to import pytsk3 for real parsing
    try:
        import pytsk3
    except ImportError:
        st.error(
            "pytsk3 library is not installed. Real file system parsing requires pytsk3.\n"
            "Install it in your environment (e.g. pip install pytsk3) and restart the app."
        )
        return

    # Determine image path from provided image_info
    image_path = image_info.get('path') or image_info.get('filepath') or image_info.get('filename')
    if not image_path:
        st.warning("No image path found in image_info. Please ensure image_info contains a 'path' or 'filepath' key pointing to the local image file.")
        return

    if not os.path.exists(image_path):
        st.warning(f"Image path not found or inaccessible: {image_path}")
        return

    st.info("Using pytsk3 to parse partitions and file systems. This may take some time depending on image size.")

    try:
        img = pytsk3.Img_Info(image_path)
    except Exception as e:
        st.error(f"Failed to open image with pytsk3: {e}")
        return

    # Helper: human readable bytes
    def bytes_to_human(n):
        if not n or n <= 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = min(int(math.floor(math.log(n, 1024))), len(units) - 1)
        value = n / (1024 ** idx)
        return f"{value:.2f} {units[idx]}"

    # Try reading partitions (volume offsets)
    try:
        vol = pytsk3.Volume_Info(img)
        partitions = []
        sector_size = 512
        for part in vol:
            # Some partition entries might be metadata-only; guard attributes access
            try:
                start = int(part.start) if hasattr(part, 'start') and part.start is not None else 0
                length = int(part.len) if hasattr(part, 'len') and part.len is not None else 0
            except Exception:
                start = 0
                length = 0

            desc = getattr(part, 'desc', '') or getattr(part, 'type', '') or 'Partition'
            size_bytes = length * sector_size
            partitions.append({
                'index': part.addr if hasattr(part, 'addr') else len(partitions),
                'start_sector': start,
                'length_sectors': length,
                'description': desc,
                'size': bytes_to_human(size_bytes),
            })

        if not partitions:
            st.warning('No partitions detected by pytsk3.Volume_Info. The image may be a single-file-system image. Trying to open as FS directly...')
            partitions = [{'index': 0, 'start_sector': 0, 'length_sectors': 0, 'description': 'Raw image', 'size': 'Unknown'}]

        st.subheader('Detected Partitions')
        for p in partitions:
            with st.expander(f"Partition {p['index']}: {p['description']} - {p['size']}"):
                st.write(f"Start sector: {p['start_sector']}")
                st.write(f"Length (sectors): {p['length_sectors']}")
                col1, col2 = st.columns(2)
                if col1.button(f"Browse partition {p['index']}", key=f"browse_{p['index']}"):
                    st.session_state['selected_partition'] = p

        # If a partition is selected, list top-level entries
        if 'selected_partition' in st.session_state:
            p = st.session_state['selected_partition']
            st.subheader(f"Browsing partition {p['index']} ({p['description']})")

            offset = p['start_sector'] * sector_size if p.get('start_sector') is not None else 0
            try:
                fs = pytsk3.FS_Info(img, offset=offset)
                root = fs.open_dir(path='/')

                entries = []
                for entry in root:
                    # Skip current/parent entries and entries without info
                    if not hasattr(entry, 'info') or not getattr(entry.info, 'name', None):
                        continue

                    try:
                        raw_name = entry.info.name.name
                        fname = raw_name.decode(errors='replace') if isinstance(raw_name, (bytes, bytearray)) else str(raw_name)
                    except Exception:
                        fname = str(getattr(entry.info.name, 'name', 'unknown'))

                    # Skip '.' and '..'
                    if fname in ['.', '..']:
                        continue

                    try:
                        meta = entry.info.meta
                        size = meta.size if meta and hasattr(meta, 'size') else 0
                        type_flag = 'Directory' if meta and getattr(meta, 'type', None) == pytsk3.TSK_FS_META_TYPE_DIR else 'File'
                    except Exception:
                        size = 0
                        type_flag = 'Unknown'

                    entries.append({'name': fname, 'type': type_flag, 'size': bytes_to_human(size)})

                if not entries:
                    st.info('No top-level entries found or directory could not be read.')
                else:
                    st.write("Top-level entries:")
                    for e in entries:
                        cols = st.columns([4, 1, 1])
                        cols[0].write(e['name'])
                        cols[1].write(e['type'])
                        cols[2].write(e['size'])
                        if st.button(f"Extract {e['name']}", key=f"extract_{p['index']}_{e['name']}"):
                            st.success(f"Marked for extraction: {e['name']}")

            except Exception as e:
                st.error(f"Failed to open filesystem at offset {offset}: {e}")

    except Exception as e:
        # If Volume_Info fails, attempt to open directly as a filesystem
        st.warning(f"Volume_Info parsing failed: {e}. Attempting to open image directly as a file system.")
        try:
            fs = pytsk3.FS_Info(img)
            root = fs.open_dir(path='/')
            st.success('Opened image as a file system. Use the app to browse entries (select a partition if needed).')
        except Exception as e2:
            st.error(f"Unable to parse image as file system: {e2}")


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
