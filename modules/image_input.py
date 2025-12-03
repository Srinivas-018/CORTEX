"""
Image Input Module
Handles path entry and verification of large mobile device images (.img, .bin, .dd).
It uses 'streamlit-folder-browser' to let the user select a server-accessible path, 
avoiding large file uploads.
"""

import streamlit as st
import hashlib
from pathlib import Path
import os

# Import the third-party component for server-side file browsing
# The 'try/except' block provides a clean failure message if the component is missing.
try:
    from streamlit_folder_browser import st_folder_browser
except ImportError:
    st_folder_browser = lambda *args, **kwargs: st.error(
        "Error: 'streamlit-folder-browser' is not installed. Please run 'pip install streamlit-folder-browser' and restart the app."
    )

# --- Configuration and Helper Functions ---
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks

def analyze_image_structure(sample_bytes):
    """Analyze the first bytes of the device image"""
    metadata = {}
    metadata["Header sample size"] = len(sample_bytes)
    
    # OS detection logic
    if b"Android" in sample_bytes or b"ANDROID" in sample_bytes:
        metadata["Detected OS"] = "Android"
    elif b"Apple" in sample_bytes or b"iOS" in sample_bytes:
        metadata["Detected OS"] = "iOS"
    else:
        metadata["Detected OS"] = "Unknown"

    # File System Type suspicion logic
    if sample_bytes.startswith(b"\xEB\x52\x90") or sample_bytes.startswith(b"\xEB\x76\x90"):
        metadata["File System Type"] = "FAT32 (Suspected)"
    elif sample_bytes.startswith(b"\xEB\x58\x90"):
        metadata["File System Type"] = "exFAT (Suspected)"
    elif b"ext4" in sample_bytes or b"EXT4" in sample_bytes:
        metadata["File System Type"] = "ext4 (Suspected)"
    else:
        metadata["File System Type"] = "Unknown / Raw"
    return metadata

# Note: calculate_hash_stream is no longer used, as we hash directly from the disk path.

# --- Main Render Function (Updated for Path Input and Browser) ---

def render_image_input(case_id):
    """Render the image path entry & verification interface"""
    st.header("Device Image Input & Verification")
    st.info("Enter the **server-accessible path** to the forensic image or use the file browser.")
    
    # Initialize session state for path persistence across interactions
    if 'image_path_str' not in st.session_state:
        st.session_state.image_path_str = ""
    if 'show_browser' not in st.session_state:
        st.session_state.show_browser = False


    # 1. Path Input Field (Manual entry)
    image_path_str = st.text_input(
        "Full Path to Image File",
        value=st.session_state.image_path_str,
        key='path_input',
        help="The path must be fully accessible by the Streamlit server process (e.g., mounted drive)."
    )
    
    # Update session state if the user manually changes the text input
    if st.session_state.image_path_str != image_path_str:
        st.session_state.image_path_str = image_path_str

    # 2. Browse Button to trigger the server-side file browser
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Browse Server Files"):
            st.session_state.show_browser = True

    # 3. Server-side File Browser Logic
    if st.session_state.show_browser:
        st.subheader("Server File Browser")
        
        # Start browsing from the user's current working directory or a defined evidence root
        default_path = str(Path.cwd()) 
        
        # The st_folder_browser component displays the folder structure
        selected_path = st_folder_browser(default_path=default_path)
        
        if selected_path:
            # If a path is selected, update the text input and hide the browser
            st.session_state.image_path_str = selected_path
            st.session_state.show_browser = False
            st.rerun() # Rerun to update the text input value immediately
        
        # Allow the user to close the browser
        if st.button("Close Browser"):
            st.session_state.show_browser = False
            st.rerun()

        st.markdown("---") # Visual separator

    # Stop execution if no path is available 
    if not st.session_state.image_path_str:
        st.warning("Please enter or browse for a path to the device image.")
        return None
    
    # Use the path from session state for the rest of the logic
    image_path = Path(st.session_state.image_path_str)


    # --- Path Validation ---
    try:
        if not image_path.exists():
            st.error(f"Error: File not found at the specified path: `{st.session_state.image_path_str}`")
            return None
        
        if image_path.is_dir():
            st.error(f"Error: The path refers to a directory, not a file.")
            return None
            
        file_size = image_path.stat().st_size
    except Exception as e:
        st.error(f"An error occurred while checking the file path: {e}")
        return None
    # -----------------------

    # --- Hashing Logic (Reads directly from disk path) ---
    st.subheader("Hashing large image...")
    total_bytes = 0
    
    with st.spinner(f"Reading file from disk and calculating hashes..."):
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        
        try:
            with open(image_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256.update(chunk)
                    md5.update(chunk)
                    total_bytes += len(chunk)
                    
                    denominator = file_size if file_size > 0 else 1 
                    st.progress(
                        min(1.0, total_bytes / denominator),
                        text=f"{total_bytes/1e9:.2f} GB read"
                    )
        except Exception as e:
            st.error(f"An unexpected error occurred while reading the file: {e}")
            return None

    # --- Summary, Metadata, and Database Update ---
    size_mb = total_bytes / (1024 * 1024)
    st.success(f"File found and hashed: {image_path.name} ({size_mb:.2f} MB)")

    # Basic metadata using the first 512 bytes
    try:
        with open(image_path, "rb") as f:
            header_sample = f.read(512)
        metadata = analyze_image_structure(header_sample)
    except Exception:
        metadata = {"Error": "Failed to read header"}


    st.subheader("Image Summary")
    st.write(f"**Filename:** {image_path.name}")
    st.write(f"**Full Path:** `{st.session_state.image_path_str}`")
    st.write(f"**Size:** {size_mb:.2f} MB")
    st.code(f"SHA-256: {sha256.hexdigest()}")
    st.text(f"MD5: {md5.hexdigest()}")
    st.json(metadata)

    if st.button("Verify & Process Image", type="primary"):
        # Placeholder for actual database call (assuming you have db_manager setup)
        try:
            from database.db_manager import update_case, add_chain_of_custody, add_evidence
            
            # Storing the path string directly
            update_case(case_id, image_path=st.session_state.image_path_str, image_hash=sha256.hexdigest())
            add_evidence(
                case_id,
                "Device Image",
                image_path.name,
                file_path=st.session_state.image_path_str,
                hash_value=sha256.hexdigest(),
                metadata=metadata,
            )
            add_chain_of_custody(
                case_id,
                "Image Path Entered",
                st.session_state.get("investigator", "Unknown"),
                f"Referenced {image_path.name} from path (SHA-256: {sha256.hexdigest()[:16]}...)",
            )
            st.success("Image verified and path added to case evidence!")
            st.balloons()
            
        except ImportError:
            st.warning("Note: Database modules (`database.db_manager`) not found. Skipping DB operations.")
            st.success("Path processed and verified successfully!")

    return {
        "filename": image_path.name,
        "full_path": st.session_state.image_path_str,
        "size_mb": size_mb,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "metadata": metadata,
    }