from pathlib import Path
import streamlit as st
import hashlib
import tempfile
import os

CHUNK_SIZE = 1024 * 1024  # 1 MB

def calculate_hash_file(path, algorithm='sha256'):
    """Calculate hash of a file by streaming it in chunks"""
    hash_obj = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def save_uploaded_file_to_disk(uploaded_file, dest_path=None):
    """Save Streamlit uploaded_file to disk in chunks. Returns path."""
    if dest_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
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

def render_image_input(case_id):
    """Render the image input and verification interface"""
    st.header("📱 Device Image Input & Verification")
    st.info("Upload a mobile device forensic image (.img, .bin, .dd, .raw, .e01) for analysis")

    uploaded_file = st.file_uploader(
        "Select Device Image",
        type=['img', 'bin', 'dd', 'raw', 'e01'],
        help="Upload an exact copied image of the mobile device"
    )

    if uploaded_file is not None:
        # Save file to disk in chunks to avoid blowing memory
        with st.spinner("Saving uploaded file to disk..."):
            tmp_path = save_uploaded_file_to_disk(uploaded_file)

        file_size_bytes = os.path.getsize(tmp_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Image Information")
            st.write(f"**Filename:**  {uploaded_file.name}")
            st.write(f"**Size:** {file_size_mb:.2f} MB")
            st.write(f"**Type:** {uploaded_file.type or 'Binary Image'}")

        with col2:
            st.subheader("Hash Verification")
            with st.spinner("Calculating SHA-256 hash..."):
                sha256_hash = calculate_hash_file(tmp_path, 'sha256')
            st.code(sha256_hash, language="text")
            st.caption("SHA-256 Hash for Chain of Custody")

            md5_hash = calculate_hash_file(tmp_path, 'md5')
            st.text(f"MD5: {md5_hash}")

        st.divider()

        st.subheader("Image Metadata")

        metadata = analyze_image_structure(tmp_path)

        for key, value in metadata.items():
            st.write(f"**{key}:** {value}")

        if st.button("✅ Verify & Process Image", type="primary"):
            from database.db_manager import update_case, add_chain_of_custody, add_evidence

            # You may want to move tmp_path into your project's evidence storage here
            update_case(case_id, image_path=uploaded_file.name, image_hash=sha256_hash)

            add_evidence(
                case_id,
                "Device Image",
                uploaded_file.name,
                file_path=tmp_path,
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
            'metadata': metadata,
            'tmp_path': tmp_path
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

def analyze_image_structure(file_path):
    """Analyze basic structure of the device image from disk"""
    metadata = {}

    size = os.path.getsize(file_path)
    metadata['Total Size'] = f"{size:,} bytes"
    metadata['Size (MB)'] = f"{size / (1024*1024):.2f} MB"
    metadata['Size (GB)'] = f"{size / (1024*1024*1024):.2f} GB"

    with open(file_path, 'rb') as f:
        header = f.read(512)

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

    metadata['Parseable'] = 'Yes' if size > 1024 else 'No (too small)'

    return metadata
