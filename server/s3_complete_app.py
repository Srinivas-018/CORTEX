"""
FastAPI S3 Multipart Upload Service

This is a companion service to Streamlit that provides endpoints for managing
S3 multipart uploads. Running this as a separate service keeps AWS credentials
isolated from the Streamlit process and provides better security.

Architecture:
    - Streamlit app runs on port 8501 (default)
    - This FastAPI service runs on port 8001 (configurable)
    - Both services can run on the same host or different hosts
    - Streamlit makes API calls to this service to manage uploads
    - Browser uploads parts directly to S3 using presigned URLs

Endpoints:
    - POST /create-multipart: Initialize a multipart upload and generate presigned URLs
    - POST /complete-multipart: Finalize a multipart upload after all parts are uploaded
    - GET /health: Health check endpoint

Configuration:
    Set environment variables:
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_DEFAULT_REGION: AWS region (default: us-east-1)
    - S3_BUCKET: Default S3 bucket (can be overridden per request)
    - API_PORT: Port to run on (default: 8001)
    - ALLOWED_ORIGINS: CORS allowed origins (default: http://localhost:8501)

Running:
    Development:
        uvicorn server.s3_complete_app:app --host 0.0.0.0 --port 8001 --reload
    
    Production:
        uvicorn server.s3_complete_app:app --host 0.0.0.0 --port 8001 --workers 4
    
    With systemd (see README for full configuration):
        sudo systemctl start s3-upload-service
        sudo systemctl enable s3-upload-service
    
    With Docker:
        docker run -p 8001:8001 -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy \
            cortex-s3-service

Dependencies:
    pip install fastapi uvicorn boto3 python-dotenv

Security:
    - Run behind reverse proxy (Nginx) with rate limiting
    - Use HTTPS in production
    - Implement authentication middleware
    - Validate user permissions before creating uploads
    - Set appropriate CORS policies
    - Use short-lived presigned URLs (1-24 hours)
    - Monitor for abuse
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import boto3
from botocore.exceptions import ClientError

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.s3_multipart import (
    calculate_part_size,
    calculate_part_count,
    create_multipart_upload,
    generate_presigned_part_urls,
    complete_multipart_upload,
    abort_multipart_upload,
    verify_object_exists
)


# Configuration
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
DEFAULT_BUCKET = os.getenv('S3_BUCKET', '')
API_PORT = int(os.getenv('API_PORT', '8001'))
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8501,http://localhost:8501/*').split(',')

# Initialize FastAPI
app = FastAPI(
    title="S3 Multipart Upload Service",
    description="Backend service for managing S3 multipart uploads",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class CreateMultipartRequest(BaseModel):
    """Request model for creating a multipart upload"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="Object key (path) in the bucket")
    file_size: int = Field(..., description="File size in bytes", ge=1)
    content_type: str = Field(default="application/octet-stream", description="MIME type")
    region: Optional[str] = Field(default=None, description="AWS region (optional)")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="Object metadata")


class CreateMultipartResponse(BaseModel):
    """Response model for multipart upload creation"""
    upload_id: str = Field(..., description="Multipart upload ID")
    key: str = Field(..., description="Object key")
    bucket: str = Field(..., description="Bucket name")
    part_size: int = Field(..., description="Part size in bytes")
    part_count: int = Field(..., description="Total number of parts")
    presigned_parts: List[Dict[str, Any]] = Field(..., description="Presigned URLs for each part")


class PartInfo(BaseModel):
    """Model for uploaded part information"""
    PartNumber: int = Field(..., description="Part number (1-indexed)")
    ETag: str = Field(..., description="ETag from S3 upload response")


class CompleteMultipartRequest(BaseModel):
    """Request model for completing a multipart upload"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="Object key")
    upload_id: str = Field(..., description="Multipart upload ID")
    parts: List[PartInfo] = Field(..., description="List of uploaded parts with ETags")


class CompleteMultipartResponse(BaseModel):
    """Response model for completed upload"""
    location: str = Field(..., description="S3 URL of the uploaded object")
    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="Object key")
    etag: str = Field(..., description="ETag of the completed object")


class AbortMultipartRequest(BaseModel):
    """Request model for aborting a multipart upload"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="Object key")
    upload_id: str = Field(..., description="Multipart upload ID to abort")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    aws_region: str = Field(..., description="Configured AWS region")


def get_s3_client(region: Optional[str] = None):
    """Get configured S3 client"""
    return boto3.client('s3', region_name=region or AWS_REGION)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns service status and configuration information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        aws_region=AWS_REGION
    )


@app.post("/create-multipart", response_model=CreateMultipartResponse)
async def create_multipart_endpoint(request: CreateMultipartRequest):
    """
    Create a new S3 multipart upload and generate presigned URLs for parts.
    
    This endpoint:
    1. Calculates optimal part size based on file size
    2. Creates a multipart upload in S3
    3. Generates presigned URLs for each part
    4. Returns all information needed for the browser to upload
    
    Args:
        request: CreateMultipartRequest with bucket, key, file_size, etc.
    
    Returns:
        CreateMultipartResponse with upload_id and presigned URLs
    
    Raises:
        HTTPException: If S3 operations fail
    
    Example:
        POST /create-multipart
        {
            "bucket": "forensics-bucket",
            "key": "evidence/device-image.img",
            "file_size": 1099511627776,
            "content_type": "application/octet-stream"
        }
    """
    try:
        # Get S3 client
        s3_client = get_s3_client(request.region)
        
        # Calculate part size and count
        part_size = calculate_part_size(request.file_size)
        part_count = calculate_part_count(request.file_size, part_size)
        
        # Validate part count
        if part_count > 10000:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: requires {part_count} parts, but S3 maximum is 10,000"
            )
        
        # Create multipart upload
        upload_result = create_multipart_upload(
            s3_client,
            request.bucket,
            request.key,
            request.content_type,
            request.metadata
        )
        
        # Generate presigned URLs for parts
        presigned_parts = generate_presigned_part_urls(
            s3_client,
            request.bucket,
            request.key,
            upload_result['UploadId'],
            part_count,
            expires_in=3600  # 1 hour
        )
        
        return CreateMultipartResponse(
            upload_id=upload_result['UploadId'],
            key=request.key,
            bucket=request.bucket,
            part_size=part_size,
            part_count=part_count,
            presigned_parts=presigned_parts
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=500,
            detail=f"S3 error: {error_code} - {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create multipart upload: {str(e)}"
        )


@app.post("/complete-multipart", response_model=CompleteMultipartResponse)
async def complete_multipart_endpoint(request: CompleteMultipartRequest):
    """
    Complete a multipart upload after all parts have been uploaded.
    
    This endpoint finalizes the multipart upload by assembling all parts
    into the final S3 object.
    
    Args:
        request: CompleteMultipartRequest with bucket, key, upload_id, and parts
    
    Returns:
        CompleteMultipartResponse with location and ETag
    
    Raises:
        HTTPException: If completion fails
    
    Example:
        POST /complete-multipart
        {
            "bucket": "forensics-bucket",
            "key": "evidence/device-image.img",
            "upload_id": "EXAMPLEJZ6e...",
            "parts": [
                {"PartNumber": 1, "ETag": "\"abc123\""},
                {"PartNumber": 2, "ETag": "\"def456\""}
            ]
        }
    """
    try:
        # Get S3 client (use default region as upload was created with it)
        s3_client = get_s3_client()
        
        # Convert Pydantic models to dict format expected by boto3
        parts_list = [part.dict() for part in request.parts]
        
        # Complete the multipart upload
        result = complete_multipart_upload(
            s3_client,
            request.bucket,
            request.key,
            request.upload_id,
            parts_list
        )
        
        # Verify object exists
        exists = verify_object_exists(s3_client, request.bucket, request.key)
        if not exists:
            raise HTTPException(
                status_code=500,
                detail="Upload reported as complete but object not found in S3"
            )
        
        return CompleteMultipartResponse(
            location=result['Location'],
            bucket=result['Bucket'],
            key=result['Key'],
            etag=result['ETag']
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=500,
            detail=f"S3 error: {error_code} - {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete multipart upload: {str(e)}"
        )


@app.post("/abort-multipart")
async def abort_multipart_endpoint(request: AbortMultipartRequest):
    """
    Abort a multipart upload and clean up uploaded parts.
    
    Use this to cancel an incomplete upload. All uploaded parts will be
    deleted from S3.
    
    Args:
        request: AbortMultipartRequest with bucket, key, and upload_id
    
    Returns:
        Success message
    
    Raises:
        HTTPException: If abort fails
    """
    try:
        s3_client = get_s3_client()
        
        success = abort_multipart_upload(
            s3_client,
            request.bucket,
            request.key,
            request.upload_id
        )
        
        if success:
            return {"status": "success", "message": "Multipart upload aborted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to abort upload")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=500,
            detail=f"S3 error: {error_code} - {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to abort multipart upload: {str(e)}"
        )


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return {
        "error": str(exc),
        "detail": "An unexpected error occurred"
    }


if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting S3 Multipart Upload Service on port {API_PORT}")
    print(f"AWS Region: {AWS_REGION}")
    print(f"Allowed Origins: {ALLOWED_ORIGINS}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )
