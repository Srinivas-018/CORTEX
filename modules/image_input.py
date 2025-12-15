"""
Image Input Module
Handles upload and verification of mobile device images (.img, .bin, .dd)
"""

import streamlit as st
import hashlib
from pathlib import Path
import tempfile
import os
import subprocess
import shutil
from datetime import datetime
from database.db_manager import get_case

# Chunk size for processing large files (8MB chunks)
CHUNK_SIZE = 8 * 1024 * 1024

def check_adb_available():
    """Check if ADB is available in system PATH"""
    return shutil.which("adb") is not None

def get_connected_devices():
    """Get list of connected Android devices via ADB"""
    devices = []
    try:
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            if line.strip() and "device" in line:
                parts = line.split()
                serial = parts[0]
                model = "Unknown"
                for part in parts:
                    if part.startswith("model:"):
                        model = part.split(":")[1]
                devices.append({"serial": serial, "model": model, "details": line})
    except Exception:
        pass
    return devices

def acquire_logical_image(device_serial, case_id):
    """Acquire logical data (sdcard) from device and zip it"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = tempfile.mkdtemp()
        dest_zip = os.path.join(tempfile.gettempdir(), f"logical_dump_{device_serial}_{timestamp}.zip")
        
        # Simple logical acquisition of /sdcard/Download as a demo/safe path 
        # In real forensics, we'd aim for more, but /sdcard is good for logical
        # Limited to Download to avoid massive dumps in this demo
        cmd = ["adb", "-s", device_serial, "pull", "/sdcard/Download", target_dir]
        
        subprocess.run(cmd, check=True)
        
        # Zip the directory
        shutil.make_archive(dest_zip.replace('.zip', ''), 'zip', target_dir)
        
        # Cleanup temp dir
        shutil.rmtree(target_dir, ignore_errors=True)
        
        return dest_zip, f"logical_dump_{timestamp}.zip"
    except Exception as e:
        return None, str(e)

def render_direct_connection(case_id):
    """Render interface for direct device connection"""
    st.subheader("🔌 Direct Device Connection")
    st.info("Connect an Android device via USB with USB Debugging (ADB) enabled.")
    
    if not check_adb_available():
        st.error("❌ ADB (Android Debug Bridge) not found in system PATH.")
        st.warning("Please install Android Platform Tools and add 'adb' to your PATH variables.")
        return

    if st.button("🔄 Scan for Devices"):
        st.experimental_rerun()
        
    devices = get_connected_devices()
    
    if not devices:
        st.warning("No devices detected. Please check your connection and USB Debugging settings.")
        st.markdown("""
        **Troubleshooting:**
        1. Connect phone via USB cable
        2. Enable **Developer Options** (Tap Build Number 7 times)
        3. Enable **USB Debugging**
        4. Accept the RSA fingerprint prompt on the device
        """)
        return

    st.success(f"Found {len(devices)} device(s)")
    
    selected_device = st.selectbox(
        "Select Target Device", 
        options=devices, 
        format_func=lambda d: f"{d['model']} ({d['serial']})"
    )
    
    if selected_device:
        st.write("### Acquisition Options")
        
        acq_type = st.radio("Acquisition Type", ["Logical (SD Card/Downloads)", "Physical (Requires Root)"])
        
        if acq_type == "Physical (Requires Root)":
            st.warning("Physical acquisition requires root access and `su` binary on device. Using 'dd' over ADB.")
            st.info("Coming soon in next update.")
        else:
            st.write("Extracts contents from `/sdcard/Download` folder as a logical container (ZIP).")
            
            if st.button("🚀 Start Acquisition"):
                with st.spinner("Acquiring data from device... Do not disconnect!"):
                    file_path, name_or_error = acquire_logical_image(selected_device['serial'], case_id)
                    
                    if file_path:
                        st.success("✅ Acquisition completed successfully!")
                        st.write(f"**Saved to:** {file_path}")
                        
                        # Register as evidence
                        try:
                            # Hashing
                            hash_progress = st.progress(0, text="Calculating Hash...")
                            with open(file_path, "rb") as f:
                                sha256_hash = calculate_hash_chunked(f, 'sha256')
                            hash_progress.progress(100, text="Done")
                            
                            metadata = {
                                "Source": "Direct Connection",
                                "Device Model": selected_device['model'],
                                "Serial": selected_device['serial'],
                                "Acquisition Type": "Logical"
                            }
                            
                            from database.db_manager import update_case, add_chain_of_custody, add_evidence
                            
                            update_case(case_id, image_path=file_path, image_hash=sha256_hash)
                            
                            add_evidence(
                                case_id, 
                                "Logical Dump", 
                                name_or_error,
                                file_path=file_path,
                                hash_value=sha256_hash,
                                metadata=metadata
                            )
                            
                            add_chain_of_custody(
                                case_id, 
                                "Acquisition", 
                                st.session_state.get('investigator', 'Unknown'),
                                f"Acquired logical image from {selected_device['model']} ({selected_device['serial']})"
                            )
                            
                            st.session_state['image_path'] = file_path
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"Error registering evidence: {str(e)}")
                    else:
                        st.error(f"Acquisition failed: {name_or_error}")

def calculate_hash_chunked(uploaded_file, algorithm='sha256'):
    """
    Calculate hash of file content using chunked reading.
    This prevents memory overflow for large files.
    """
    hash_obj = hashlib.new(algorithm)
    
    # Reset file pointer to beginning
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    
    # Read and hash in chunks
    bytes_read = 0
    while True:
        chunk = uploaded_file.read(CHUNK_SIZE)
        if not chunk:
            break
        hash_obj.update(chunk)
        bytes_read += len(chunk)
    
    # Reset file pointer for potential reuse
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    
    return hash_obj.hexdigest()

def save_uploaded_file_to_disk(uploaded_file, dest_path=None):
    """Save Streamlit uploaded_file to disk in chunks. Returns path."""
    if dest_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.img')
        dest_path = tmp.name
        tmp.close()

    # uploaded_file is a io.BufferedReader-like object from Streamlit
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    with open(dest_path, "wb") as f:
        while True:
            chunk = uploaded_file.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)

    # reset uploaded_file pointer (if needed elsewhere)
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    return dest_path

def get_file_size_mb(uploaded_file):
    """Get file size in MB without loading entire file into memory"""
    try:
        uploaded_file.seek(0, 2)  # Seek to end
        size_bytes = uploaded_file.tell()
        uploaded_file.seek(0)  # Reset to beginning
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0

def render_image_input(case_id):
    """Render the image input and verification interface"""
    st.header("📱 Device Image Input & Verification")
    
    # Check if image is already uploaded for this case
    case = get_case(case_id)
    if case and case[4]:
        image_path = case[4]
        if os.path.exists(image_path):
            st.success("✅ Image File Uploaded & Verified")
            
            image_hash = case[5] if case[5] else "Not recorded"
            filename = os.path.basename(image_path)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Image Information")
                st.write(f"**Filename:** {filename}")
                st.write(f"**Path:** {image_path}")
                try:
                    size_mb = os.path.getsize(image_path) / (1024 * 1024)
                    st.write(f"**Size:** {size_mb:.2f} MB")
                except:
                    pass
            
            with col2:
                st.subheader("Hash Verification")
                st.code(image_hash, language="text")
                st.caption("SHA-256 Hash")
            
            # Return image info so other tabs function including demo case which might rely on this
            return {
                'filename': filename,
                'file_path': image_path,
                'sha256': image_hash,
                # Add dummy size/metadata if needed by consumer, or read real ones
                'size': 0,
                'metadata': {}
            }
        else:
            st.error(f"❌ Image file recorded for this case was not found on disk: {image_path}")
            st.warning("Please locate the file and provide the path again below.")
    
    # Bypass for Demo Case
    if case_id == "DEMO-CASE":
        st.success("✅ Demo Image Loaded Successfully")
        st.info("This is a simulated Android device image for demonstration purposes.")
        
        col1, col2 = st.columns(2)
        with col1:
             st.subheader("Image Information")
             st.write("**Filename:** demo_device_image.dd")
             st.write("**Source:** Synthetic Demo Data")
             st.write("**Size:** 32.00 GB")
             st.write("**Detected OS:** Android 12 (Demo)")
        
        with col2:
             st.subheader("Hash Verification")
             st.code("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0", language="text")
             st.caption("SHA-256 Hash (Simulated)")
             
        return {
            'filename': 'demo_device_image.dd',
            'file_path': 'demo_device_image.dd',
            'sha256': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
            'size': 32768, # MB
            'metadata': {
                'Detected OS': 'Android',
                'File System Type': 'ext4'
            }
        }
    
    st.info("Enter the absolute file path of the mobile device forensic image (.img, .bin, .dd, .raw)")
    
    selected_file = None
    uploaded_file = None
    is_local = False
    
    # Session state for local path
    if 'verified_local_path' not in st.session_state:
        st.session_state['verified_local_path'] = None
    
    local_path = st.text_input("Enter Absolute File Path", placeholder="C:\\Forensics\\Case_001\\image.dd")
    
    # Reset verified path if input changes
    if local_path != st.session_state.get('verified_local_path'):
            st.session_state['verified_local_path'] = None
            
    if local_path:
        if os.path.exists(local_path) and os.path.isfile(local_path):
            if st.button("Load Local File", key="load_local") or st.session_state.get('verified_local_path') == local_path:
                try:
                    # Mark as verified
                    st.session_state['verified_local_path'] = local_path
                    st.success(f"File found: {os.path.basename(local_path)}")
                except Exception as e:
                    st.error(f"Error checking file: {str(e)}")
        elif local_path:
            st.warning("File not found or invalid path")

    # Determine which file to use
    if uploaded_file:
        selected_file = uploaded_file
        is_local = False
    elif st.session_state.get('verified_local_path'):
        try:
            selected_file = open(st.session_state['verified_local_path'], 'rb')
            is_local = True
        except Exception as e:
            st.error(f"Error opening local file: {str(e)}")
            st.session_state['verified_local_path'] = None

    if selected_file is not None:
        try:
            # For local files, we need to handle them carefully
            # Ensure we are at start of file
            selected_file.seek(0)
            
            # File name handling
            file_name = selected_file.name
            if is_local:
                file_name = os.path.basename(selected_file.name)
            
            # Get file size
            file_size_mb = 0
            try:
                if is_local:
                    file_size_mb = os.path.getsize(selected_file.name) / (1024 * 1024)
                else:
                    file_size_mb = get_file_size_mb(selected_file)
            except:
                pass
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Image Information")
                st.write(f"**Filename:** {file_name}")
                st.write(f"**Source:** {'Local Storage' if is_local else 'Upload'}")
                st.write(f"**Size:** {file_size_mb:.2f} MB ({file_size_mb/1024:.2f} GB)")
                
                if file_size_mb > 1000:
                    st.warning("⚠️ Large file detected. Processing may take time.")
            
            with col2:
                st.subheader("Hash Verification")
                
                hash_progress = st.progress(0, text="Calculating SHA-256 hash...")
                
                try:
                    sha256_hash = calculate_hash_chunked(selected_file, 'sha256')
                    hash_progress.progress(50, text="Calculating MD5 hash...")
                    md5_hash = calculate_hash_chunked(selected_file, 'md5')
                    hash_progress.progress(100, text="Hash calculation complete!")
                    
                    st.code(sha256_hash, language="text")
                    st.caption("SHA-256 Hash")
                    st.text(f"MD5: {md5_hash}")
                    
                except Exception as e:
                    st.error(f"Error calculating hash: {str(e)}")
                    if is_local: selected_file.close()
                    return None
            
            st.divider()
            
            st.subheader("Image Metadata")
            
            metadata_progress = st.progress(0, text="Analyzing image structure...")
            metadata = analyze_image_structure_chunked(selected_file)
            metadata_progress.progress(100, text="Analysis complete!")
            
            for key, value in metadata.items():
                st.write(f"**{key}:** {value}")
            
            col_btn1, col_btn2 = st.columns(2)
            
            # Use a callback or unique key to avoid state issues with button
            with col_btn1:
                if st.button("✅ Verify & Add to Case", type="primary"):
                    with st.spinner("Registering evidence..."):
                        try:
                            final_path = ""
                            image_hash = sha256_hash
                            
                            if is_local:
                                # Use the local path directly
                                final_path = selected_file.name # absolute path from open()
                                # Close the handle as we just store the path
                                selected_file.close()
                                # Important: remove from locals so we don't try to close again
                                del selected_file
                                selected_file = None
                            else:
                                # Save uploaded file
                                final_path = save_uploaded_file_to_disk(selected_file)
                            
                            from database.db_manager import update_case, add_chain_of_custody, add_evidence
                            
                            update_case(case_id, image_path=final_path, image_hash=image_hash)
                            
                            add_evidence(
                                case_id, 
                                "Device Image", 
                                file_name,
                                file_path=final_path,
                                hash_value=image_hash,
                                metadata=metadata
                            )
                            
                            add_chain_of_custody(
                                case_id, 
                                "Evidence Added", 
                                st.session_state.get('investigator', 'Unknown'),
                                f"Added image {file_name} from {'local path' if is_local else 'upload'}"
                            )
                            
                            st.session_state['image_path'] = final_path
                            
                            st.success("✅ Image verified and added to case evidence!")
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"Error processing evidence: {str(e)}")
                            if is_local and selected_file: selected_file.close()
                            return None
            
            # Close local file handle if it wasn't closed in the success block
            if is_local and selected_file: 
                 selected_file.close()

            return {
                'filename': file_name,
                'size': file_size_mb,
                'sha256': sha256_hash,
                'md5': md5_hash,
                'metadata': metadata,
                'file_path': st.session_state.get('image_path', '')
            }
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            if is_local and 'selected_file' in locals() and selected_file: selected_file.close()
            return None
    
    else:
        st.info("Please select an image to begin analysis")
        
    return None

def analyze_image_structure_chunked(uploaded_file):
    """Analyze basic structure of the device image without loading entire file"""
    metadata = {}
    
    try:
        # Get file size
        uploaded_file.seek(0, 2)
        total_bytes = uploaded_file.tell()
        uploaded_file.seek(0)
        
        metadata['Total Size'] = f"{total_bytes:,} bytes"
        metadata['Size (MB)'] = f"{total_bytes / (1024*1024):.2f} MB"
        metadata['Size (GB)'] = f"{total_bytes / (1024*1024*1024):.2f} GB"
        
        # Read only first 4KB for header analysis
        header = uploaded_file.read(4096)
        uploaded_file.seek(0)
        
        # Detect OS
        if b'Android' in header or b'ANDROID' in header:
            metadata['Detected OS'] = 'Android'
        elif b'Apple' in header or b'iOS' in header or b'HFS' in header:
            metadata['Detected OS'] = 'iOS'
        else:
            metadata['Detected OS'] = 'Unknown'
        
        # Detect file system type
        if header.startswith(b'\xEB\x52\x90') or header.startswith(b'\xEB\x76\x90'):
            metadata['File System Type'] = 'FAT32 (Suspected)'
        elif header.startswith(b'\xEB\x58\x90'):
            metadata['File System Type'] = 'exFAT (Suspected)'
        elif b'ext4' in header or b'EXT4' in header:
            metadata['File System Type'] = 'ext4 (Suspected)'
        elif b'ext3' in header or b'EXT3' in header:
            metadata['File System Type'] = 'ext3 (Suspected)'
        else:
            metadata['File System Type'] = 'Unknown / Raw'
        
        metadata['Parseable'] = 'Yes' if total_bytes > 1024 else 'No (too small)'
        
    except Exception as e:
        metadata['Error'] = str(e)
    
    return metadata
