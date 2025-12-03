"""
Streamlit S3 Direct Upload Integration

This module provides Streamlit components for direct browser-to-S3 uploads
using multipart upload with presigned URLs. This approach avoids routing large
files through the Streamlit server, enabling reliable uploads up to 1 TB.

Architecture:
    1. User selects file in browser (file_input for selection only, not upload)
    2. Streamlit backend calls FastAPI service or uses boto3 directly to:
       - Create multipart upload
       - Generate presigned URLs for each part
    3. Streamlit embeds HTML/JS component with presigned URLs
    4. Browser uploads parts directly to S3 using presigned URLs
    5. Browser calls FastAPI completion endpoint to finalize upload
    6. Streamlit verifies object exists and shows success

Dependencies:
    - boto3 (for S3 operations)
    - streamlit
    - requests (for calling FastAPI backend)

Configuration:
    The module requires S3 configuration, typically passed as a dictionary:
    {
        'bucket': 'my-forensics-bucket',
        'region': 'us-east-1',
        'key_prefix': 'uploads/',  # Optional prefix for uploaded objects
        'part_size': 50 * 1024 * 1024  # Optional, defaults to calculated size
    }

Backend Options:
    1. FastAPI Companion Service (Recommended):
       - Run server/s3_complete_app.py alongside Streamlit
       - Provides /create-multipart and /complete-multipart endpoints
       - Keeps S3 credentials separate from Streamlit process
    
    2. Direct boto3 (Simple but less secure):
       - Use boto3 directly in Streamlit process
       - Requires AWS credentials in Streamlit environment
       - Good for development/testing

Usage Example:
    ```python
    import streamlit as st
    from modules.s3_streamlit import render_s3_direct_upload
    
    st.title("Large File Upload")
    
    s3_config = {
        'bucket': 'my-forensics-bucket',
        'region': 'us-east-1',
        'key_prefix': 'evidence/',
        'backend_url': 'http://localhost:8001'  # FastAPI service URL
    }
    
    result = render_s3_direct_upload(
        s3_config=s3_config,
        part_size=50 * 1024 * 1024,  # 50 MB parts
        title="Upload Device Image",
        allowed_extensions=['img', 'bin', 'dd', 'raw', 'e01']
    )
    
    if result:
        st.success(f"File uploaded: {result['key']}")
        st.write(f"Location: {result['location']}")
    ```

Security Considerations:
    - Only provide presigned URLs to authenticated users
    - Validate user permissions before creating uploads
    - Use short-lived presigned URLs (1-24 hours)
    - Implement rate limiting on backend endpoints
    - Consider using S3 bucket policies to restrict access
"""

import streamlit as st
import boto3
import requests
import json
from typing import Dict, Optional, List
from pathlib import Path

from modules.s3_multipart import (
    calculate_part_size,
    calculate_part_count,
    create_multipart_upload,
    generate_presigned_part_urls,
    verify_object_exists
)


def render_s3_direct_upload(
    s3_config: Dict,
    part_size: Optional[int] = None,
    title: str = "Direct S3 Upload",
    description: str = "Select a file to upload directly to S3 (supports files up to 1 TB)",
    allowed_extensions: Optional[List[str]] = None,
    use_backend: bool = True
) -> Optional[Dict]:
    """
    Render a Streamlit component for direct browser-to-S3 uploads.
    
    This function creates a file selector and, when a file is selected, generates
    presigned URLs and embeds an HTML/JS uploader component for direct uploads.
    
    Args:
        s3_config: S3 configuration dictionary:
            {
                'bucket': str,              # S3 bucket name
                'region': str,              # AWS region
                'key_prefix': str,          # Optional prefix for object keys
                'backend_url': str,         # FastAPI backend URL (if use_backend=True)
                'aws_access_key_id': str,   # Optional, for direct boto3 mode
                'aws_secret_access_key': str,  # Optional, for direct boto3 mode
            }
        part_size: Part size in bytes (optional, calculated automatically if not provided)
        title: Title to display above the upload component
        description: Description text to show
        allowed_extensions: List of allowed file extensions (e.g., ['img', 'bin', 'dd'])
        use_backend: If True, use FastAPI backend; if False, use boto3 directly
    
    Returns:
        Dictionary with upload results if successful:
        {
            'key': str,         # S3 object key
            'location': str,    # S3 URL
            'bucket': str,      # Bucket name
            'size': int,        # File size in bytes
            'etag': str         # ETag of completed object
        }
        Returns None if upload not completed or in progress
    
    Example:
        >>> s3_config = {
        ...     'bucket': 'forensics-data',
        ...     'region': 'us-east-1',
        ...     'backend_url': 'http://localhost:8001'
        ... }
        >>> result = render_s3_direct_upload(s3_config)
        >>> if result:
        ...     print(f"Uploaded to {result['location']}")
    """
    st.subheader(title)
    st.info(description)
    
    # File selection (not upload through Streamlit)
    # We use a unique key to track state
    file_selector_key = f"file_selector_{s3_config.get('bucket', 'default')}"
    
    # Use a simple file input that doesn't actually upload through Streamlit
    st.write("**Step 1:** Select the file to upload")
    
    # Create a placeholder for file metadata input
    col1, col2 = st.columns(2)
    
    with col1:
        file_name = st.text_input(
            "File Name",
            key=f"{file_selector_key}_name",
            placeholder="device-image.img",
            help="Enter the name of the file you want to upload"
        )
    
    with col2:
        file_size_mb = st.number_input(
            "File Size (MB)",
            min_value=1,
            max_value=1048576,  # 1 TB in MB
            value=100,
            key=f"{file_selector_key}_size",
            help="Enter the size of your file in megabytes"
        )
    
    content_type = st.text_input(
        "Content Type (optional)",
        value="application/octet-stream",
        key=f"{file_selector_key}_content_type",
        help="MIME type of the file"
    )
    
    if not file_name:
        st.warning("⚠️ Please enter a file name to continue")
        return None
    
    # Validate file extension if specified
    if allowed_extensions:
        file_ext = Path(file_name).suffix.lstrip('.')
        if file_ext not in allowed_extensions:
            st.error(f"❌ File extension '.{file_ext}' not allowed. Allowed: {', '.join(allowed_extensions)}")
            return None
    
    file_size_bytes = int(file_size_mb * 1024 * 1024)
    
    st.divider()
    
    # Calculate optimal part size
    if part_size is None:
        part_size = calculate_part_size(file_size_bytes)
    
    part_count = calculate_part_count(file_size_bytes, part_size)
    
    st.write("**Upload Configuration:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("File Size", f"{file_size_mb:,.0f} MB")
    with col2:
        st.metric("Part Size", f"{part_size / (1024*1024):.1f} MB")
    with col3:
        st.metric("Total Parts", f"{part_count:,}")
    
    if part_count > 10000:
        st.error(f"❌ File too large: {part_count} parts exceeds S3 limit of 10,000 parts")
        return None
    
    st.divider()
    
    # Create upload button
    if st.button("🚀 Start Upload", type="primary", key=f"{file_selector_key}_upload"):
        with st.spinner("Initializing multipart upload..."):
            try:
                # Generate object key
                key_prefix = s3_config.get('key_prefix', 'uploads/')
                object_key = f"{key_prefix}{file_name}"
                
                if use_backend:
                    # Use FastAPI backend
                    upload_config = _create_upload_via_backend(
                        s3_config,
                        object_key,
                        file_size_bytes,
                        content_type
                    )
                else:
                    # Use boto3 directly
                    upload_config = _create_upload_direct(
                        s3_config,
                        object_key,
                        file_size_bytes,
                        content_type,
                        part_size
                    )
                
                # Store upload config in session state
                st.session_state[f"{file_selector_key}_upload_config"] = upload_config
                
                st.success("✅ Multipart upload initialized!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to initialize upload: {str(e)}")
                return None
    
    # Check if we have an upload configuration ready
    upload_config_key = f"{file_selector_key}_upload_config"
    if upload_config_key in st.session_state:
        upload_config = st.session_state[upload_config_key]
        
        st.write("**Step 2:** Upload in progress via browser")
        st.info("📤 The upload component below will handle the direct upload to S3. Select your file when prompted.")
        
        # Render the upload component
        _render_upload_component(upload_config, s3_config, file_selector_key)
        
        # Check if upload is complete
        if st.session_state.get(f"{file_selector_key}_complete", False):
            result = st.session_state.get(f"{file_selector_key}_result")
            
            # Clean up session state
            del st.session_state[upload_config_key]
            del st.session_state[f"{file_selector_key}_complete"]
            del st.session_state[f"{file_selector_key}_result"]
            
            return result
    
    return None


def _create_upload_via_backend(
    s3_config: Dict,
    object_key: str,
    file_size: int,
    content_type: str
) -> Dict:
    """
    Create multipart upload via FastAPI backend.
    
    Args:
        s3_config: S3 configuration with 'backend_url'
        object_key: S3 object key
        file_size: File size in bytes
        content_type: MIME type
    
    Returns:
        Upload configuration dictionary with presigned URLs
    """
    backend_url = s3_config.get('backend_url', 'http://localhost:8001')
    
    response = requests.post(
        f"{backend_url}/create-multipart",
        json={
            'bucket': s3_config['bucket'],
            'key': object_key,
            'file_size': file_size,
            'content_type': content_type,
            'region': s3_config.get('region', 'us-east-1')
        },
        timeout=30
    )
    
    response.raise_for_status()
    return response.json()


def _create_upload_direct(
    s3_config: Dict,
    object_key: str,
    file_size: int,
    content_type: str,
    part_size: int
) -> Dict:
    """
    Create multipart upload directly using boto3.
    
    Args:
        s3_config: S3 configuration with credentials
        object_key: S3 object key
        file_size: File size in bytes
        content_type: MIME type
        part_size: Part size in bytes
    
    Returns:
        Upload configuration dictionary with presigned URLs
    """
    # Initialize S3 client
    s3_client_params = {
        'region_name': s3_config.get('region', 'us-east-1')
    }
    
    if 'aws_access_key_id' in s3_config:
        s3_client_params['aws_access_key_id'] = s3_config['aws_access_key_id']
        s3_client_params['aws_secret_access_key'] = s3_config['aws_secret_access_key']
    
    s3_client = boto3.client('s3', **s3_client_params)
    
    # Create multipart upload
    upload_result = create_multipart_upload(
        s3_client,
        s3_config['bucket'],
        object_key,
        content_type
    )
    
    # Generate presigned URLs
    part_count = calculate_part_count(file_size, part_size)
    presigned_parts = generate_presigned_part_urls(
        s3_client,
        s3_config['bucket'],
        object_key,
        upload_result['UploadId'],
        part_count,
        expires_in=3600  # 1 hour
    )
    
    return {
        'upload_id': upload_result['UploadId'],
        'key': object_key,
        'bucket': s3_config['bucket'],
        'part_size': part_size,
        'presigned_parts': presigned_parts,
        'backend_url': s3_config.get('backend_url', '')
    }


def _render_upload_component(upload_config: Dict, s3_config: Dict, selector_key: str):
    """
    Render the HTML/JS upload component.
    
    Args:
        upload_config: Upload configuration with presigned URLs
        s3_config: S3 configuration
        selector_key: Unique key for this upload session
    """
    # Load the HTML component
    html_file = Path(__file__).parent.parent / 'components' / 's3_uploader.html'
    
    if not html_file.exists():
        st.error("❌ Upload component not found. Please ensure components/s3_uploader.html exists.")
        return
    
    with open(html_file, 'r') as f:
        html_template = f.read()
    
    # Inject configuration into HTML
    config_json = json.dumps(upload_config)
    backend_url = upload_config.get('backend_url', s3_config.get('backend_url', 'http://localhost:8001'))
    
    html_content = html_template.replace('{{CONFIG}}', config_json)
    html_content = html_content.replace('{{BACKEND_URL}}', backend_url)
    
    # Render the component
    st.components.v1.html(html_content, height=400, scrolling=True)
    
    # Note: The component will handle the upload and POST to the completion endpoint
    # The completion endpoint should then trigger a callback or update state
    st.info("💡 The upload is handled entirely in your browser. The file never passes through the Streamlit server.")


def check_upload_completion(
    s3_config: Dict,
    object_key: str
) -> bool:
    """
    Check if an upload has been completed by verifying object existence in S3.
    
    Args:
        s3_config: S3 configuration
        object_key: S3 object key to check
    
    Returns:
        True if object exists, False otherwise
    """
    try:
        s3_client_params = {
            'region_name': s3_config.get('region', 'us-east-1')
        }
        
        if 'aws_access_key_id' in s3_config:
            s3_client_params['aws_access_key_id'] = s3_config['aws_access_key_id']
            s3_client_params['aws_secret_access_key'] = s3_config['aws_secret_access_key']
        
        s3_client = boto3.client('s3', **s3_client_params)
        
        return verify_object_exists(s3_client, s3_config['bucket'], object_key)
    except Exception:
        return False
