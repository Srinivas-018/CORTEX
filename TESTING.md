# Testing Guide for S3 Multipart Upload Feature

This document provides step-by-step instructions for testing the S3 multipart upload functionality.

## Prerequisites

- Python 3.12+
- AWS account with S3 access
- AWS credentials configured
- All dependencies installed (`pip install -r requirements.txt`)

## Unit Tests

### Test 1: Part Size Calculation

Test that the `calculate_part_size` function correctly computes optimal part sizes:

```bash
cd /home/runner/work/CORTEX/CORTEX
python3 << 'EOF'
from modules.s3_multipart import calculate_part_size, calculate_part_count

# Test 1 TB file
one_tb = 1_099_511_627_776
part_size = calculate_part_size(one_tb)
part_count = calculate_part_count(one_tb, part_size)

assert part_size >= 5 * 1024 * 1024, "Part size must be >= 5 MB"
assert part_count <= 10000, "Part count must be <= 10,000"
print(f"✅ 1 TB test passed: {part_count} parts of {part_size/(1024*1024):.2f} MB each")

# Test 100 MB file
small_file = 100 * 1024 * 1024
part_size = calculate_part_size(small_file)
assert part_size == 5 * 1024 * 1024, "Small files should use minimum 5 MB parts"
print(f"✅ 100 MB test passed: {part_size/(1024*1024):.2f} MB parts")

print("All unit tests passed!")
EOF
```

Expected output:
```
✅ 1 TB test passed: 10000 parts of 104.86 MB each
✅ 100 MB test passed: 5.00 MB parts
All unit tests passed!
```

### Test 2: FastAPI Service Health

Test that the FastAPI backend service loads correctly:

```bash
cd /home/runner/work/CORTEX/CORTEX
python3 << 'EOF'
from fastapi.testclient import TestClient
from server.s3_complete_app import app

client = TestClient(app)
response = client.get('/health')

assert response.status_code == 200, "Health endpoint should return 200"
assert response.json()["status"] == "healthy", "Status should be healthy"
print("✅ FastAPI health check passed")
print(f"Response: {response.json()}")
EOF
```

Expected output:
```
✅ FastAPI health check passed
Response: {'status': 'healthy', 'version': '1.0.0', 'aws_region': 'us-east-1'}
```

## Integration Tests

### Test 3: FastAPI Backend Service

Start the FastAPI backend service:

```bash
# Terminal 1
cd /home/runner/work/CORTEX/CORTEX
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
export S3_BUCKET=your-test-bucket

uvicorn server.s3_complete_app:app --host 0.0.0.0 --port 8001 --reload
```

Test the health endpoint:

```bash
# Terminal 2
curl http://localhost:8001/health
```

Expected output:
```json
{"status":"healthy","version":"1.0.0","aws_region":"us-east-1"}
```

### Test 4: Create Multipart Upload

Test creating a multipart upload (requires valid AWS credentials and S3 bucket):

```bash
curl -X POST http://localhost:8001/create-multipart \
  -H "Content-Type: application/json" \
  -d '{
    "bucket": "your-test-bucket",
    "key": "test/sample.bin",
    "file_size": 104857600,
    "content_type": "application/octet-stream"
  }' | jq
```

Expected output (with valid credentials):
```json
{
  "upload_id": "EXAMPLEJZ6e...",
  "key": "test/sample.bin",
  "bucket": "your-test-bucket",
  "part_size": 5242880,
  "part_count": 20,
  "presigned_parts": [
    {
      "PartNumber": 1,
      "PresignedUrl": "https://s3.amazonaws.com/..."
    },
    ...
  ]
}
```

### Test 5: Streamlit Application

Start the Streamlit application:

```bash
# Terminal 1
cd /home/runner/work/CORTEX/CORTEX
export S3_BUCKET=your-test-bucket
export S3_REGION=us-east-1
export BACKEND_URL=http://localhost:8001

streamlit run app.py
```

1. Open browser to http://localhost:8501
2. Navigate to "Large File Upload" in the sidebar
3. Verify the page loads without errors
4. Check that the configuration panel shows correct values
5. Check that the backend health indicator is green

### Test 6: End-to-End Upload Flow

**Note:** This test requires a real file to upload and valid AWS credentials.

1. Start FastAPI backend (Test 3)
2. Start Streamlit (Test 5)
3. Navigate to "Large File Upload" page
4. Enter file details:
   - File Name: test-file.bin
   - File Size: 100 MB (or actual size)
   - Content Type: application/octet-stream
5. Click "Initialize Upload"
6. Verify presigned URLs are generated
7. Select file in browser when prompted
8. Watch progress bar update
9. Verify upload completes successfully
10. Check S3 bucket for uploaded file:

```bash
aws s3 ls s3://your-test-bucket/evidence/
aws s3api head-object --bucket your-test-bucket --key evidence/test-file.bin
```

## Manual Verification

### Verify S3 Bucket Configuration

**Check CORS configuration:**

```bash
aws s3api get-bucket-cors --bucket your-test-bucket
```

Expected output:
```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
      "AllowedOrigins": ["http://localhost:8501"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

**Check lifecycle policy:**

```bash
aws s3api get-bucket-lifecycle-configuration --bucket your-test-bucket
```

Expected output:
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

### Verify IAM Permissions

Test AWS credentials have required permissions:

```bash
# Test bucket access
aws s3 ls s3://your-test-bucket/

# Test object upload
echo "test" > /tmp/test.txt
aws s3 cp /tmp/test.txt s3://your-test-bucket/test/test.txt

# Test object read
aws s3 cp s3://your-test-bucket/test/test.txt /tmp/test-download.txt

# Clean up
aws s3 rm s3://your-test-bucket/test/test.txt
rm /tmp/test.txt /tmp/test-download.txt
```

## Performance Testing

### Test Large File Upload Speed

Monitor upload speed for different file sizes:

```bash
# Create test files
dd if=/dev/zero of=/tmp/test-100mb.bin bs=1M count=100
dd if=/dev/zero of=/tmp/test-1gb.bin bs=1M count=1024

# Upload via AWS CLI (baseline)
time aws s3 cp /tmp/test-100mb.bin s3://your-test-bucket/test/

# Upload via multipart (using the Streamlit interface)
# Record time and compare
```

### Monitor S3 Metrics

Use AWS CloudWatch to monitor:
- Number of PUT requests
- Transfer speed
- Error rates
- Incomplete multipart uploads

```bash
# List incomplete uploads
aws s3api list-multipart-uploads --bucket your-test-bucket

# Abort incomplete upload if needed
aws s3api abort-multipart-upload \
  --bucket your-test-bucket \
  --key test/sample.bin \
  --upload-id <upload-id>
```

## Troubleshooting Tests

### Test: Diagnose CORS Issues

```bash
# Test CORS from browser console
fetch('https://your-bucket.s3.amazonaws.com/test/file.bin', {
  method: 'PUT',
  body: 'test'
}).then(r => console.log('Success:', r)).catch(e => console.error('CORS Error:', e));
```

### Test: Diagnose AWS Credential Issues

```bash
# Verify credentials are loaded
python3 << 'EOF'
import boto3
try:
    s3 = boto3.client('s3')
    response = s3.list_buckets()
    print("✅ Credentials valid")
    print(f"Found {len(response['Buckets'])} buckets")
except Exception as e:
    print(f"❌ Credentials error: {e}")
EOF
```

### Test: Diagnose Network Issues

```bash
# Test connectivity to S3
curl -I https://s3.amazonaws.com/

# Test FastAPI backend connectivity
curl -v http://localhost:8001/health

# Test Streamlit connectivity
curl -I http://localhost:8501/
```

## Automated Test Script

Create a comprehensive test script:

```bash
#!/bin/bash
# test_s3_upload.sh - Automated test script

echo "Starting S3 Upload Feature Tests"
echo "================================="

# Test 1: Python syntax
echo "Test 1: Python syntax check"
python3 -m py_compile modules/s3_multipart.py modules/s3_streamlit.py server/s3_complete_app.py
if [ $? -eq 0 ]; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
    exit 1
fi

# Test 2: Unit tests
echo "Test 2: Part size calculation"
python3 -c "
from modules.s3_multipart import calculate_part_size, calculate_part_count
assert calculate_part_count(1099511627776, calculate_part_size(1099511627776)) <= 10000
print('✅ PASSED')
"

# Test 3: FastAPI health
echo "Test 3: FastAPI service health"
python3 -c "
from fastapi.testclient import TestClient
from server.s3_complete_app import app
client = TestClient(app)
assert client.get('/health').status_code == 200
print('✅ PASSED')
"

echo "================================="
echo "All tests completed!"
```

Make it executable and run:

```bash
chmod +x test_s3_upload.sh
./test_s3_upload.sh
```

## Test Checklist

- [ ] Part size calculation works for files from 5 MB to 1 TB
- [ ] Part count never exceeds 10,000
- [ ] Minimum part size is 5 MB (except last part)
- [ ] FastAPI service starts without errors
- [ ] FastAPI health endpoint returns 200
- [ ] FastAPI accepts create-multipart requests
- [ ] FastAPI accepts complete-multipart requests
- [ ] Streamlit app starts without errors
- [ ] Large Upload page loads correctly
- [ ] Configuration panel shows correct values
- [ ] Backend health check indicator works
- [ ] S3 bucket has correct CORS configuration
- [ ] S3 bucket has lifecycle policy for incomplete uploads
- [ ] IAM permissions allow required S3 operations
- [ ] Presigned URLs are generated correctly
- [ ] Presigned URLs have correct expiration time
- [ ] Browser can upload directly to S3 using presigned URLs
- [ ] Upload progress tracking works
- [ ] Completion POST succeeds
- [ ] Uploaded files appear in S3 bucket
- [ ] File integrity is maintained (hash verification)

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Test S3 Upload Feature

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run syntax check
        run: |
          python3 -m py_compile modules/s3_multipart.py
          python3 -m py_compile server/s3_complete_app.py
      - name: Run unit tests
        run: python3 test_s3_upload.sh
      - name: Test FastAPI service
        run: |
          python3 -c "from fastapi.testclient import TestClient; from server.s3_complete_app import app; client = TestClient(app); assert client.get('/health').status_code == 200"
```

## Conclusion

Following these tests ensures the S3 multipart upload feature is working correctly and ready for production use. Always test in a staging environment before deploying to production.
