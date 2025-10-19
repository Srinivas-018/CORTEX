"""
Image Input Module
Handles upload and verification of mobile device images (.img, .bin, .dd)
"""

import streamlit as st
import hashlib
from pathlib import Path

def calculate_hash(file_bytes, algorithm='sha256'):
    """Calculate hash of file content"""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(file_bytes)
    return hash_obj.hexdigest()

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
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Image Information")
            st.write(f"**Filename:**  {uploaded_file.name}")
            st.write(f"**Size:** {file_size_mb:.2f} MB")
            st.write(f"**Type:** {uploaded_file.type or 'Binary Image'}")
        
        with col2:
            st.subheader("Hash Verification")
            
            with st.spinner("Calculating SHA-256 hash..."):
                sha256_hash = calculate_hash(file_bytes, 'sha256')
            
            st.code(sha256_hash, language="text")
            st.caption("SHA-256 Hash for Chain of Custody")
            
            md5_hash = calculate_hash(file_bytes, 'md5')
            st.text(f"MD5: {md5_hash}")
        
        st.divider()
        
        st.subheader("Image Metadata")
        
        metadata = analyze_image_structure(file_bytes)
        
        for key, value in metadata.items():
            st.write(f"**{key}:** {value}")
        
        if st.button("✅ Verify & Process Image", type="primary"):
            from database.db_manager import update_case, add_chain_of_custody, add_evidence
            
            update_case(case_id, image_path=uploaded_file.name, image_hash=sha256_hash)
            
            add_evidence(
                case_id, 
                "Device Image", 
                uploaded_file.name,
                file_path=uploaded_file.name,
                hash_value=sha256_hash,
                metadata=metadata
            )
            
            add_chain_of_custody(
                case_id, 
                "Image Uploaded", 
                st.session_state.get('investigator', 'Unknown'),
                f"Uploaded and verified {uploaded_file.name} (SHA-256: {sha256_hash[:16]}...)"
            )
            
            st.success("✅ Image verified and added to case evidence!")
            st.balloons()
        
        return {
            'filename': uploaded_file.name,
            'size': file_size_mb,
            'sha256': sha256_hash,
            'md5': md5_hash,
            'metadata': metadata
        }
    
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

def analyze_image_structure(file_bytes):
    """Analyze basic structure of the device image"""
    metadata = {}
    
    metadata['Total Size'] = f"{len(file_bytes):,} bytes"
    metadata['Size (MB)'] = f"{len(file_bytes) / (1024*1024):.2f} MB"
    metadata['Size (GB)'] = f"{len(file_bytes) / (1024*1024*1024):.2f} GB"
    
    header = file_bytes[:512] if len(file_bytes) >= 512 else file_bytes
    
    if b'Android' in header or b'ANDROID' in header:
        metadata['Detected OS'] = 'Android'
    elif b'Apple' in header or b'iOS' in header:
        metadata['Detected OS'] = 'iOS'
    else:
        metadata['Detected OS'] = 'Unknown'
    
    if header.startswith(b'\xEB\x52\x90') or header.startswith(b'\xEB\x76\x90'):
        metadata['File System Type'] = 'FAT32 (Suspected)'
    elif header.startswith(b'\xEB\x58\x90'):
        metadata['File System Type'] = 'exFAT (Suspected)'
    elif b'ext4' in header or b'EXT4' in header:
        metadata['File System Type'] = 'ext4 (Suspected)'
    else:
        metadata['File System Type'] = 'Unknown / Raw'
    
    metadata['Parseable'] = 'Yes' if len(file_bytes) > 1024 else 'No (too small)'
    
    return metadata
