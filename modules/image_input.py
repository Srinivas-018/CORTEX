"""
Image Input Module
Handles upload and verification of mobile device images (.img, .bin, .dd)
"""

import streamlit as st
import hashlib
from pathlib import Path
import tempfile
import os

# Chunk size for processing large files (8MB chunks)
CHUNK_SIZE = 8 * 1024 * 1024

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
    
    st.info("Upload a mobile device forensic image (.img, .bin, .dd, .raw) for analysis")
    
    uploaded_file = st.file_uploader(
        "Select Device Image", 
        type=['img', 'bin', 'dd', 'raw', 'e01'],
        help="Upload an exact copied image of the mobile device"
    )
    
    if uploaded_file is not None:
        try:
            # Get file size without reading entire file
            file_size_mb = get_file_size_mb(uploaded_file)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Image Information")
                st.write(f"**Filename:**  {uploaded_file.name}")
                st.write(f"**Size:** {file_size_mb:.2f} MB ({file_size_mb/1024:.2f} GB)")
                st.write(f"**Type:** {uploaded_file.type or 'Binary Image'}")
                
                if file_size_mb > 100:
                    st.warning("⚠️ Large file detected. Processing may take some time.")
            
            with col2:
                st.subheader("Hash Verification")
                
                # Progress bar for hash calculation
                hash_progress = st.progress(0, text="Calculating SHA-256 hash...")
                
                try:
                    sha256_hash = calculate_hash_chunked(uploaded_file, 'sha256')
                    hash_progress.progress(50, text="Calculating MD5 hash...")
                    md5_hash = calculate_hash_chunked(uploaded_file, 'md5')
                    hash_progress.progress(100, text="Hash calculation complete!")
                    
                    st.code(sha256_hash, language="text")
                    st.caption("SHA-256 Hash for Chain of Custody")
                    st.text(f"MD5: {md5_hash}")
                    
                except Exception as e:
                    st.error(f"Error calculating hash: {str(e)}")
                    return None
            
            st.divider()
            
            st.subheader("Image Metadata")
            
            # Analyze only first few MB for metadata to avoid memory issues
            metadata_progress = st.progress(0, text="Analyzing image structure...")
            metadata = analyze_image_structure_chunked(uploaded_file)
            metadata_progress.progress(100, text="Analysis complete!")
            
            for key, value in metadata.items():
                st.write(f"**{key}:** {value}")
            
            # Save file to disk for processing
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("✅ Verify & Process Image", type="primary"):
                    with st.spinner("Saving image file..."):
                        try:
                            # Save to temporary location
                            temp_path = save_uploaded_file_to_disk(uploaded_file)
                            
                            from database.db_manager import update_case, add_chain_of_custody, add_evidence
                            
                            update_case(case_id, image_path=temp_path, image_hash=sha256_hash)
                            
                            add_evidence(
                                case_id, 
                                "Device Image", 
                                uploaded_file.name,
                                file_path=temp_path,
                                hash_value=sha256_hash,
                                metadata=metadata
                            )
                            
                            add_chain_of_custody(
                                case_id, 
                                "Image Uploaded", 
                                st.session_state.get('investigator', 'Unknown'),
                                f"Uploaded and verified {uploaded_file.name} (SHA-256: {sha256_hash[:16]}...)"
                            )
                            
                            # Store image path in session state
                            st.session_state['image_path'] = temp_path
                            
                            st.success("✅ Image verified and added to case evidence!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error saving image: {str(e)}")
                            return None
            
            return {
                'filename': uploaded_file.name,
                'size': file_size_mb,
                'sha256': sha256_hash,
                'md5': md5_hash,
                'metadata': metadata,
                'file_path': st.session_state.get('image_path', '')
            }
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error("This may be due to insufficient memory. Please try a smaller file or contact support.")
            return None
    
    else:
        st.warning("⚠️ No device image uploaded yet")
        
        with st.expander("ℹ️ Supported Image Formats"):
            st.markdown("""
            - **.img** - Raw disk image
            - **.bin** - Binary image file
            - **.dd** - Disk dump (dd command output)
            - **.raw** - Raw forensic image
            - **.e01** - Expert Witness Format (EnCase)
            
            **Note:** For best results, use forensically sound imaging tools like:
            - dd (Linux/macOS)
            - FTK Imager
            - Cellebrite
            - UFED
            """)
    
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
