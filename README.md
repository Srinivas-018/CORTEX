# CORTEX - Mobile Device Forensics Analyzer

🔍 **Professional Forensic Analysis Platform for Mobile Devices**

CORTEX (Comprehensive Offline Retrieval and Tracking Evidence eXtractor) is a complete mobile device forensics analysis platform built with Python and Streamlit.

## Features

### 📱 Core Capabilities
- **Device Image Processing** - Support for .img, .bin, .dd, .raw, and .e01 formats
- **File System Analysis** - Parse and explore device partitions and directories
- **Data Extraction** - Extract SMS, calls, WhatsApp, contacts, location data, browser history
- **Timeline Reconstruction** - Build chronological timelines from all artifacts
- **Keyword Search** - Search across all extracted data for specific terms
- **Visualization** - Interactive charts, location maps, and communication networks
- **Report Generation** - Professional PDF forensic reports
- **Chain of Custody** - Complete audit trail with SHA-256 hash verification

### 🎯 Evidence Types Supported
- Call logs and SMS messages
- Messaging apps (WhatsApp, Telegram, Signal, Facebook Messenger)
- Contacts and address books
- GPS location data and maps
- Browser history (Chrome, Firefox, Safari, Edge)
- Photos and videos with EXIF metadata
- Deleted and hidden data recovery
- Application databases

## Installation

### Prerequisites
- Python 3.12 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Srinivas-018/CORTEX.git
cd CORTEX
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:5000`

## Usage

### 1. Create a Case
- Start by creating a new forensic case on the dashboard
- Enter Case ID, name, investigator details, and device information

### 2. Upload Device Image
- Navigate to the "Image Input" tab
- Upload a mobile device image file (.img, .bin, .dd, etc.)
- System automatically calculates SHA-256 hash for integrity verification

### 3. Extract Data
- Use the "Data Extraction" tab to extract various artifacts:
  - Call logs and SMS messages
  - Messaging app data (WhatsApp, Telegram, etc.)
  - Contacts
  - Location history
  - Browser history
  - Deleted files

### 4. Analyze Evidence
- Use "Analysis Tools" to:
  - Build chronological timelines
  - Search for keywords across all data
  - View case statistics

### 5. Visualize Findings
- View interactive charts and graphs
- Display location data on maps
- Analyze communication networks

### 6. Generate Reports
- Create professional PDF forensic reports
- Include executive summary, evidence inventory, chain of custody
- Export timeline and data in CSV format

## Project Structure

```
CORTEX/
├── app.py                      # Main Streamlit application
├── modules/                    # Analysis modules
│   ├── image_input.py         # Image upload and verification
│   ├── file_parser.py         # File system parsing
│   ├── data_extractor.py      # Data extraction tools
│   ├── analysis_tools.py      # Timeline and keyword search
│   ├── visualization.py       # Charts and graphs
│   └── report_generator.py    # PDF report generation
├── database/                   # SQLite database
│   ├── db_manager.py          # Database operations
│   └── cortex.db              # Case and evidence database
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Large File Upload (S3 Direct Upload)

CORTEX now supports uploading files up to 1 TB using S3 direct multipart uploads. This feature bypasses the Streamlit server entirely, uploading files directly from the browser to AWS S3.

### Why Direct S3 Upload?

Traditional file uploads through Streamlit have limitations:
- **Memory constraints**: Files are loaded into server memory
- **Timeout issues**: Large uploads may timeout
- **Size limits**: Practical limit around 50-100 GB even with maxUploadSize configuration

The S3 Direct Upload feature solves these problems by:
- Uploading files directly from browser to S3 (bypassing server)
- Using multipart upload (splitting files into manageable parts)
- Supporting files up to 1 TB (S3's multipart upload limit)
- Providing progress tracking and resumable uploads

### Architecture

```
┌─────────┐         ┌──────────────┐         ┌─────────┐
│ Browser │ ──────> │   FastAPI    │ ──────> │   S3    │
│         │ <────── │   Backend    │         │ Bucket  │
└─────────┘         └──────────────┘         └─────────┘
     │                                              ↑
     │                                              │
     └──────────────────────────────────────────────┘
              Direct upload via presigned URLs
```

1. **Streamlit** provides the UI and coordinates the upload
2. **FastAPI Backend** manages S3 credentials and generates presigned URLs
3. **Browser** uploads file parts directly to S3
4. **S3** stores the evidence files

### Setup Instructions

#### 1. AWS Configuration

**Create S3 Bucket:**
```bash
aws s3 mb s3://your-forensics-bucket --region us-east-1
```

**Configure S3 CORS** (required for browser uploads):

Create a file named `cors.json`:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedOrigins": ["http://localhost:8501", "https://your-production-domain.com"],
    "ExposeHeaders": ["ETag", "x-amz-server-side-encryption", "x-amz-request-id"],
    "MaxAgeSeconds": 3000
  }
]
```

Apply CORS configuration:
```bash
aws s3api put-bucket-cors --bucket your-forensics-bucket --cors-configuration file://cors.json
```

**Set S3 Lifecycle Policy** (to clean up incomplete uploads):

Create a file named `lifecycle.json`:
```json
{
  "Rules": [
    {
      "Id": "DeleteIncompleteMultipartUpload",
      "Status": "Enabled",
      "Prefix": "",
      "AbortIncompleteMultipartUpload": {
        "DaysAfterInitiation": 7
      }
    }
  ]
}
```

Apply lifecycle policy:
```bash
aws s3api put-bucket-lifecycle-configuration --bucket your-forensics-bucket --lifecycle-configuration file://lifecycle.json
```

**Create IAM Policy** for S3 access:

Create a file named `s3-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-forensics-bucket",
        "arn:aws:s3:::your-forensics-bucket/*"
      ]
    }
  ]
}
```

Create IAM user and attach policy:
```bash
aws iam create-user --user-name cortex-s3-uploader
aws iam put-user-policy --user-name cortex-s3-uploader --policy-name S3UploadPolicy --policy-document file://s3-policy.json
aws iam create-access-key --user-name cortex-s3-uploader
```

Save the Access Key ID and Secret Access Key from the output.

#### 2. Environment Configuration

Set environment variables for AWS credentials:

**Linux/macOS:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
export S3_BUCKET="your-forensics-bucket"
export S3_KEY_PREFIX="evidence/"
export BACKEND_URL="http://localhost:8001"
```

**Windows (PowerShell):**
```powershell
$env:AWS_ACCESS_KEY_ID="your-access-key-id"
$env:AWS_SECRET_ACCESS_KEY="your-secret-access-key"
$env:AWS_DEFAULT_REGION="us-east-1"
$env:S3_BUCKET="your-forensics-bucket"
$env:S3_KEY_PREFIX="evidence/"
$env:BACKEND_URL="http://localhost:8001"
```

Or create a `.env` file in the project root:
```
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=your-forensics-bucket
S3_KEY_PREFIX=evidence/
BACKEND_URL=http://localhost:8001
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs boto3, FastAPI, uvicorn, and other required packages.

#### 4. Start the FastAPI Backend

The FastAPI backend service must be running to handle S3 multipart upload operations.

**Development:**
```bash
uvicorn server.s3_complete_app:app --host 0.0.0.0 --port 8001 --reload
```

**Production:**
```bash
uvicorn server.s3_complete_app:app --host 0.0.0.0 --port 8001 --workers 4
```

#### 5. Start Streamlit

```bash
streamlit run app.py
```

#### 6. Access the Upload Page

Navigate to **Large File Upload** in the Streamlit sidebar, or access directly at:
```
http://localhost:8501/large_upload
```

### Production Deployment

#### Using systemd (Linux)

Create `/etc/systemd/system/cortex-s3-backend.service`:

```ini
[Unit]
Description=CORTEX S3 Upload Backend Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/CORTEX
Environment="AWS_ACCESS_KEY_ID=your-key"
Environment="AWS_SECRET_ACCESS_KEY=your-secret"
Environment="AWS_DEFAULT_REGION=us-east-1"
Environment="S3_BUCKET=your-forensics-bucket"
ExecStart=/usr/local/bin/uvicorn server.s3_complete_app:app --host 0.0.0.0 --port 8001 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cortex-s3-backend
sudo systemctl start cortex-s3-backend
sudo systemctl status cortex-s3-backend
```

#### Using Docker

**Dockerfile for Backend:**

Create `Dockerfile.backend`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY modules/ modules/
COPY server/ server/

EXPOSE 8001

CMD ["uvicorn", "server.s3_complete_app:app", "--host", "0.0.0.0", "--port", "8001"]
```

Build and run:
```bash
docker build -f Dockerfile.backend -t cortex-s3-backend .
docker run -d -p 8001:8001 \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e S3_BUCKET=your-forensics-bucket \
  --name cortex-s3-backend \
  cortex-s3-backend
```

#### Nginx Reverse Proxy Configuration

Create `/etc/nginx/sites-available/cortex`:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/m;

upstream streamlit {
    server localhost:8501;
}

upstream fastapi {
    server localhost:8001;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Streamlit app
    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Note: client_max_body_size doesn't matter for direct S3 uploads
        # But keep reasonable for other endpoints
        client_max_body_size 100M;
    }
    
    # FastAPI backend
    location /api/ {
        # Rate limiting
        limit_req zone=upload_limit burst=5;
        
        proxy_pass http://fastapi/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # WebSocket for Streamlit
    location /_stcore/stream {
        proxy_pass http://streamlit/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Enable the configuration:
```bash
sudo ln -s /etc/nginx/sites-available/cortex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Security Considerations

**Presigned URLs:**
- Default expiration: 1 hour (configurable in `server/s3_complete_app.py`)
- Keep expiration time as short as practical (1-24 hours recommended)
- URLs are single-use for specific operations
- Monitor S3 access logs for abuse

**Authentication & Authorization:**
- Implement authentication middleware in FastAPI backend
- Verify user permissions before creating uploads
- Use JWT tokens or session-based auth
- Rate limit upload creation endpoints

**S3 Bucket Security:**
- Enable S3 bucket encryption (AES-256 or KMS)
- Enable S3 access logging
- Use bucket policies to restrict access
- Enable versioning for audit trails
- Disable public access

**Network Security:**
- Use HTTPS in production (Let's Encrypt recommended)
- Run backend service on internal network if possible
- Use VPC endpoints for S3 access (when running on AWS)
- Implement firewall rules to restrict access

**Monitoring:**
- Monitor S3 CloudWatch metrics
- Set up alerts for unusual upload patterns
- Monitor FastAPI logs for errors
- Track incomplete multipart uploads

### Testing & Verification

**Manual Testing:**

1. **Test Backend Health:**
   ```bash
   curl http://localhost:8001/health
   ```
   Expected output: `{"status":"healthy","version":"1.0.0","aws_region":"us-east-1"}`

2. **Test Multipart Upload Creation:**
   ```bash
   curl -X POST http://localhost:8001/create-multipart \
     -H "Content-Type: application/json" \
     -d '{
       "bucket": "your-forensics-bucket",
       "key": "test/sample.bin",
       "file_size": 104857600,
       "content_type": "application/octet-stream"
     }'
   ```

3. **Test via Streamlit:**
   - Navigate to the Large File Upload page
   - Enter file details
   - Click "Initialize Upload"
   - Verify backend returns presigned URLs

4. **Verify S3 Object:**
   ```bash
   aws s3 ls s3://your-forensics-bucket/evidence/
   aws s3api head-object --bucket your-forensics-bucket --key evidence/your-file.img
   ```

**Unit Testing:**

Create `tests/test_s3_multipart.py`:
```python
import pytest
from modules.s3_multipart import calculate_part_size, calculate_part_count

def test_calculate_part_size():
    # 1 TB should use ~110 MB parts
    one_tb = 1_099_511_627_776
    part_size = calculate_part_size(one_tb)
    part_count = calculate_part_count(one_tb, part_size)
    
    assert part_size >= 5 * 1024 * 1024  # >= 5 MB
    assert part_count <= 10000  # <= 10,000 parts
    assert part_count == 10000 or part_count < 10000

def test_calculate_part_size_small_file():
    # 100 MB should use 5 MB parts (minimum)
    small_file = 100 * 1024 * 1024
    part_size = calculate_part_size(small_file)
    
    assert part_size == 5 * 1024 * 1024

def test_calculate_part_count():
    part_size = 50 * 1024 * 1024  # 50 MB
    file_size = 500 * 1024 * 1024  # 500 MB
    
    assert calculate_part_count(file_size, part_size) == 10
```

Run tests:
```bash
pytest tests/test_s3_multipart.py -v
```

### Troubleshooting

**Backend Service Not Reachable:**
- Check if service is running: `curl http://localhost:8001/health`
- Check logs: `journalctl -u cortex-s3-backend -f` (systemd) or `docker logs cortex-s3-backend` (Docker)
- Verify firewall allows port 8001

**CORS Errors in Browser:**
- Check S3 bucket CORS configuration: `aws s3api get-bucket-cors --bucket your-bucket`
- Ensure AllowedOrigins includes your Streamlit URL
- Check browser console for specific error messages

**Permission Denied Errors:**
- Verify AWS credentials are set correctly
- Check IAM policy has required permissions
- Test with AWS CLI: `aws s3 ls s3://your-bucket`

**Upload Fails or Times Out:**
- Check browser console for JavaScript errors
- Verify presigned URLs are not expired
- Check S3 region matches configuration
- Ensure network allows HTTPS to S3

**Incomplete Multipart Uploads:**
- List incomplete uploads: `aws s3api list-multipart-uploads --bucket your-bucket`
- Manually abort if needed: `aws s3api abort-multipart-upload --bucket your-bucket --key file.img --upload-id <id>`
- Lifecycle policy will auto-clean after 7 days

### Performance Optimization

**Part Size Tuning:**
- Smaller parts = more HTTP requests, better parallelism
- Larger parts = fewer requests, less overhead
- Default: Calculated to stay under 10,000 parts limit
- Optimal range: 50-100 MB for most use cases

**Concurrency:**
- Browser uploads 4 parts concurrently by default
- Adjust in `components/s3_uploader.html` (line ~150)
- More concurrency = faster but more bandwidth

**Network:**
- Use S3 Transfer Acceleration for faster uploads
- Enable in S3 bucket and update endpoint
- Costs more but significantly faster for long-distance uploads

### Cost Estimation

**S3 Storage Costs** (us-east-1, Standard storage):
- Storage: $0.023 per GB/month
- 1 TB file: ~$23.55/month

**S3 Request Costs:**
- PUT requests: $0.005 per 1,000 requests
- 1 TB file (10,000 parts): ~$0.05 per upload

**Data Transfer:**
- Upload to S3: FREE
- Download from S3: $0.09 per GB (first 10 TB/month)

**Total Example (1 TB file):**
- Upload: ~$0.05
- Storage (1 month): ~$23.55
- Download: ~$92.16 (if downloaded once)

### Additional Resources

**AWS Documentation:**
- [S3 Multipart Upload Overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
- [S3 CORS Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html)
- [Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

**Code References:**
- `modules/s3_multipart.py` - Core S3 multipart upload functions
- `modules/s3_streamlit.py` - Streamlit integration helpers
- `server/s3_complete_app.py` - FastAPI backend service
- `components/s3_uploader.html` - Browser upload component
- `pages/large_upload.py` - Streamlit demo page



- **Frontend:** Streamlit
- **Backend:** Python 3.12
- **Database:** SQLite
- **Visualization:** Plotly
- **Data Analysis:** pandas, numpy
- **PDF Generation:** fpdf
- **Forensic Tools:** pytsk3, python-magic, exifread

## Demo Mode

The application includes demo mode functionality that simulates data extraction without requiring actual device images. This is useful for:
- Training and demonstrations
- Testing workflows
- Understanding the platform capabilities

## Security & Integrity

- **Hash Verification:** SHA-256 and MD5 hashes calculated for all evidence
- **Chain of Custody:** Complete audit log of all actions
- **Database Storage:** All evidence metadata stored in SQLite for tracking
- **Integrity Checks:** Verification of image integrity throughout analysis

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

This project is available under standard open source licensing terms.

## Disclaimer

This tool is designed for lawful forensic analysis by authorized personnel only. Users are responsible for complying with all applicable laws and regulations regarding digital forensics and evidence handling.

## Support

For questions, issues, or feature requests, please open an issue on GitHub.

---

**CORTEX** - Making Mobile Forensics Accessible and Professional

© 2025 Digital Forensics Lab
