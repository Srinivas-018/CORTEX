# CORTEX - AI Model Perfector

## Overview
CORTEX is a forensic and data analysis platform built with Streamlit. This project was imported from GitHub (Srinivas-018/CORTEX) and has been configured to run in the Replit environment.

**Current State:** Fully functional Streamlit application running on port 5000

## Project Information
- **Framework:** Streamlit (Python 3.12)
- **Purpose:** Forensic analysis and data processing platform
- **Status:** Development ready
- **Version:** 1.0.0

## Project Structure
```
.
├── AIModelPerfector/          # Main application directory
│   ├── app.py                 # Streamlit application entry point
│   └── __init__.py            # Package initialization
├── scripts/                   # Automation scripts
│   └── agent_runner.py        # CI/CD runner script
├── .streamlit/                # Streamlit configuration
│   └── config.toml            # Server and browser settings
├── .github/workflows/         # GitHub Actions
│   └── auto_agent.yml         # Automated workflow
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
└── .replit                    # Replit configuration
```

## Available Modules
The application provides the following forensic analysis modules:

1. **File Analysis** - Analyze files and calculate hashes (MD5, SHA-256)
2. **Data Extraction** - Process CSV/Excel files with statistics and visualization
3. **Image Processing** - Extract EXIF data and analyze image files
4. **Report Generation** - Create PDF reports for forensic findings

## Key Dependencies
- streamlit >= 1.0.0 - Web application framework
- pandas >= 1.0.0 - Data manipulation
- plotly >= 5.0.0 - Interactive visualizations
- Pillow - Image processing
- exifread - EXIF metadata extraction
- fpdf - PDF report generation
- pytsk3 - File system analysis
- python-magic - File type identification

## Running the Application
The Streamlit application is configured to run automatically via the workflow system:
- **Command:** `streamlit run AIModelPerfector/app.py`
- **Port:** 5000
- **Host:** 0.0.0.0 (configured for Replit proxy)

The application is accessible through the Replit webview.

## Configuration
### Streamlit Settings (.streamlit/config.toml)
- Server runs on 0.0.0.0:5000 (headless mode)
- CORS and XSRF protection disabled for Replit proxy compatibility
- Usage statistics collection disabled

### Python Environment
- Python 3.12 (configured in .replit)
- Uses Nix packages: file, glibcLocales

## Recent Changes
**October 19, 2025:**
- Created main Streamlit application with forensic analysis modules
- Installed all required Python dependencies
- Configured Streamlit server for Replit environment
- Added .gitignore for Python project
- Set up workflow to run on port 5000
- Created project documentation

## Development Notes
- This was a skeleton GitHub import - only infrastructure files existed initially
- Main application code was created to match the forensic analysis theme indicated by requirements.txt
- All Streamlit host/CORS settings are properly configured for Replit's proxy environment
- The application handles file uploads, data analysis, image processing, and PDF report generation

## GitHub Integration
- Repository includes automated GitHub Actions workflow (auto_agent.yml)
- Daily scheduled runs at 03:00 UTC
- Agent runner script performs smoke checks and code formatting

## User Preferences
No user preferences have been documented yet.
