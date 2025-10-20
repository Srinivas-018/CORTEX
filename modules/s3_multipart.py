"""
S3 Multipart Upload Helper Functions

This module provides helper functions for managing S3 multipart upload lifecycle,
including creating uploads, generating presigned URLs, and completing/aborting uploads.

AWS Credentials & Configuration:
    The module uses boto3 which requires AWS credentials. Configure via:
    1. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
    2. AWS credentials file: ~/.aws/credentials
    3. IAM role (when running on EC2/ECS/Lambda)

Required IAM Permissions:
    The AWS credentials used must have the following S3 permissions:
    - s3:PutObject
    - s3:GetObject
    - s3:AbortMultipartUpload
    - s3:ListMultipartUploadParts
    
    Example IAM Policy:
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:AbortMultipartUpload",
                    "s3:ListMultipartUploadParts"
                ],
                "Resource": "arn:aws:s3:::your-bucket-name/*"
            }
        ]
    }

Usage Example:
    import boto3
    from modules.s3_multipart import (
        calculate_part_size,
        create_multipart_upload,
        generate_presigned_part_urls,
        complete_multipart_upload,
        abort_multipart_upload
    )
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    bucket = 'my-forensics-bucket'
    
    # Calculate optimal part size for 1TB file
    file_size = 1_099_511_627_776  # 1 TB
    part_size = calculate_part_size(file_size)
    
    # Create multipart upload
    result = create_multipart_upload(
        s3_client, bucket, 'evidence/device-image.img', 'application/octet-stream'
    )
    upload_id = result['UploadId']
    
    # Generate presigned URLs for parts
    part_count = (file_size + part_size - 1) // part_size
    presigned_urls = generate_presigned_part_urls(
        s3_client, bucket, result['Key'], upload_id, part_count, expires_in=3600
    )
    
    # After parts are uploaded, complete the upload
    parts = [{'ETag': 'etag1', 'PartNumber': 1}, {'ETag': 'etag2', 'PartNumber': 2}]
    complete_result = complete_multipart_upload(
        s3_client, bucket, result['Key'], upload_id, parts
    )

Security Considerations:
    - Presigned URLs should be short-lived (default 1 hour, max 24 hours recommended)
    - Only provide presigned URLs to authenticated and authorized users
    - Implement S3 bucket lifecycle policies to clean up incomplete uploads
    - Use HTTPS for all S3 operations
    - Consider using S3 bucket policies to restrict access
"""

import math
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple, Optional, Any


# Constants
MIN_PART_SIZE = 5 * 1024 * 1024  # 5 MB - S3 minimum (except last part)
MAX_PARTS = 10000  # S3 maximum number of parts
DEFAULT_PART_SIZE = 50 * 1024 * 1024  # 50 MB default


def calculate_part_size(file_size_bytes: int, min_part_size: int = MIN_PART_SIZE) -> int:
    """
    Calculate optimal part size for multipart upload to stay within S3 limits.
    
    S3 has a maximum of 10,000 parts per upload. This function ensures that
    the file can be uploaded within this constraint while respecting the
    minimum part size of 5 MB (except for the last part).
    
    Algorithm:
        part_size = max(min_part_size, ceil(file_size / MAX_PARTS))
    
    Args:
        file_size_bytes: Total size of the file in bytes
        min_part_size: Minimum part size (default 5 MB, S3 requirement)
    
    Returns:
        Optimal part size in bytes
    
    Examples:
        >>> calculate_part_size(1_099_511_627_776)  # 1 TB
        109951163  # ~110 MB
        
        >>> calculate_part_size(100 * 1024 * 1024)  # 100 MB
        5242880  # 5 MB (minimum)
        
        >>> calculate_part_size(50 * 1024 * 1024)  # 50 MB
        5242880  # 5 MB (minimum)
    """
    if file_size_bytes <= 0:
        return min_part_size
    
    # Calculate part size to fit within MAX_PARTS
    calculated_part_size = math.ceil(file_size_bytes / MAX_PARTS)
    
    # Ensure we meet minimum part size requirement
    part_size = max(min_part_size, calculated_part_size)
    
    return part_size


def calculate_part_count(file_size_bytes: int, part_size: int) -> int:
    """
    Calculate the number of parts needed for a multipart upload.
    
    Args:
        file_size_bytes: Total size of the file in bytes
        part_size: Size of each part in bytes
    
    Returns:
        Number of parts needed
    
    Examples:
        >>> calculate_part_count(1_099_511_627_776, 109951163)
        10000
    """
    if file_size_bytes <= 0 or part_size <= 0:
        return 0
    
    return math.ceil(file_size_bytes / part_size)


def create_multipart_upload(
    s3_client: boto3.client,
    bucket: str,
    key: str,
    content_type: str = 'application/octet-stream',
    metadata: Optional[Dict[str, str]] = None
) -> Dict:
    """
    Create a new S3 multipart upload.
    
    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: Object key (path) in the bucket
        content_type: MIME type of the file
        metadata: Optional metadata dictionary to attach to the object
    
    Returns:
        Dictionary with upload details:
        {
            'UploadId': str,  # Upload ID to use for subsequent operations
            'Bucket': str,    # Bucket name
            'Key': str        # Object key
        }
    
    Raises:
        ClientError: If the S3 operation fails
    
    Example:
        >>> s3 = boto3.client('s3')
        >>> result = create_multipart_upload(
        ...     s3, 'my-bucket', 'uploads/file.img', 'application/octet-stream'
        ... )
        >>> print(result['UploadId'])
        'EXAMPLEJZ6e...'
    """
    try:
        params = {
            'Bucket': bucket,
            'Key': key,
            'ContentType': content_type
        }
        
        if metadata:
            params['Metadata'] = metadata
        
        response = s3_client.create_multipart_upload(**params)
        
        return {
            'UploadId': response['UploadId'],
            'Bucket': bucket,
            'Key': key
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Failed to create multipart upload: {error_code} - {error_message}") from e


def generate_presigned_part_urls(
    s3_client: boto3.client,
    bucket: str,
    key: str,
    upload_id: str,
    part_count: int,
    expires_in: int = 3600
) -> List[Dict[str, Any]]:
    """
    Generate presigned URLs for uploading parts.
    
    Creates presigned URLs that allow direct browser-to-S3 uploads without
    routing data through the application server.
    
    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: Object key (path) in the bucket
        upload_id: Multipart upload ID from create_multipart_upload
        part_count: Number of parts to generate URLs for
        expires_in: URL expiration time in seconds (default 3600 = 1 hour)
    
    Returns:
        List of dictionaries with presigned URL details:
        [
            {
                'PartNumber': int,      # Part number (1-indexed)
                'PresignedUrl': str     # Presigned URL for PUT request
            },
            ...
        ]
    
    Raises:
        ClientError: If generating presigned URLs fails
    
    Security Note:
        - Keep expires_in short (1-24 hours recommended)
        - Only provide URLs to authenticated users
        - URLs grant temporary upload permission
    
    Example:
        >>> s3 = boto3.client('s3')
        >>> urls = generate_presigned_part_urls(
        ...     s3, 'my-bucket', 'uploads/file.img', 'upload-id', 100, 3600
        ... )
        >>> print(urls[0])
        {'PartNumber': 1, 'PresignedUrl': 'https://s3.amazonaws.com/...'}
    """
    presigned_urls = []
    
    try:
        for part_number in range(1, part_count + 1):
            url = s3_client.generate_presigned_url(
                ClientMethod='upload_part',
                Params={
                    'Bucket': bucket,
                    'Key': key,
                    'UploadId': upload_id,
                    'PartNumber': part_number
                },
                ExpiresIn=expires_in
            )
            
            presigned_urls.append({
                'PartNumber': part_number,
                'PresignedUrl': url
            })
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Failed to generate presigned URLs: {error_code} - {error_message}") from e
    
    return presigned_urls


def complete_multipart_upload(
    s3_client: boto3.client,
    bucket: str,
    key: str,
    upload_id: str,
    parts: List[Dict[str, Any]]
) -> Dict:
    """
    Complete a multipart upload after all parts have been uploaded.
    
    This finalizes the multipart upload and assembles all parts into the
    final object in S3.
    
    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: Object key (path) in the bucket
        upload_id: Multipart upload ID
        parts: List of uploaded parts with ETags:
            [
                {'ETag': str, 'PartNumber': int},
                ...
            ]
            Parts must be sorted by PartNumber
    
    Returns:
        Dictionary with completion details:
        {
            'Location': str,  # URL of the uploaded object
            'Bucket': str,    # Bucket name
            'Key': str,       # Object key
            'ETag': str       # ETag of the completed object
        }
    
    Raises:
        ClientError: If the completion fails
    
    Example:
        >>> parts = [
        ...     {'ETag': '"abc123"', 'PartNumber': 1},
        ...     {'ETag': '"def456"', 'PartNumber': 2}
        ... ]
        >>> result = complete_multipart_upload(
        ...     s3, 'my-bucket', 'uploads/file.img', 'upload-id', parts
        ... )
        >>> print(result['Location'])
        'https://my-bucket.s3.amazonaws.com/uploads/file.img'
    """
    try:
        # Ensure parts are sorted by PartNumber
        sorted_parts = sorted(parts, key=lambda x: x['PartNumber'])
        
        response = s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': sorted_parts}
        )
        
        return {
            'Location': response.get('Location', f"s3://{bucket}/{key}"),
            'Bucket': bucket,
            'Key': key,
            'ETag': response.get('ETag', '')
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Failed to complete multipart upload: {error_code} - {error_message}") from e


def abort_multipart_upload(
    s3_client: boto3.client,
    bucket: str,
    key: str,
    upload_id: str
) -> bool:
    """
    Abort a multipart upload and clean up uploaded parts.
    
    Use this to cancel an incomplete upload and free up storage. All uploaded
    parts will be deleted from S3.
    
    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: Object key (path) in the bucket
        upload_id: Multipart upload ID to abort
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        ClientError: If the abort operation fails
    
    Note:
        It's recommended to set up S3 lifecycle policies to automatically
        abort and clean up incomplete multipart uploads after a certain time
        period (e.g., 7 days).
    
    Example:
        >>> s3 = boto3.client('s3')
        >>> success = abort_multipart_upload(
        ...     s3, 'my-bucket', 'uploads/file.img', 'upload-id'
        ... )
        >>> if success:
        ...     print("Upload aborted successfully")
    """
    try:
        s3_client.abort_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id
        )
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Failed to abort multipart upload: {error_code} - {error_message}") from e


def list_multipart_uploads(
    s3_client: boto3.client,
    bucket: str,
    prefix: str = ''
) -> List[Dict]:
    """
    List all in-progress multipart uploads in a bucket.
    
    Useful for monitoring and cleanup of incomplete uploads.
    
    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        prefix: Optional prefix to filter uploads by key prefix
    
    Returns:
        List of upload details:
        [
            {
                'UploadId': str,
                'Key': str,
                'Initiated': datetime,
                'Initiator': dict,
                'Owner': dict
            },
            ...
        ]
    
    Example:
        >>> s3 = boto3.client('s3')
        >>> uploads = list_multipart_uploads(s3, 'my-bucket', 'uploads/')
        >>> for upload in uploads:
        ...     print(f"Upload {upload['UploadId']} for {upload['Key']}")
    """
    try:
        params = {'Bucket': bucket}
        if prefix:
            params['Prefix'] = prefix
        
        response = s3_client.list_multipart_uploads(**params)
        
        return response.get('Uploads', [])
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Failed to list multipart uploads: {error_code} - {error_message}") from e


def verify_object_exists(
    s3_client: boto3.client,
    bucket: str,
    key: str
) -> bool:
    """
    Verify that an object exists in S3.
    
    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: Object key (path) in the bucket
    
    Returns:
        True if object exists, False otherwise
    
    Example:
        >>> s3 = boto3.client('s3')
        >>> if verify_object_exists(s3, 'my-bucket', 'uploads/file.img'):
        ...     print("File uploaded successfully!")
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise
