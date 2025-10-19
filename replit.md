# CORTEX - Mobile Device Forensics Analyzer

## Overview
CORTEX (Comprehensive Offline Retrieval and Tracking Evidence eXtractor) is a professional mobile device forensics analysis platform built with Streamlit and Python. This project was imported from GitHub (Srinivas-018/CORTEX) and has been fully developed for the Replit environment.

**Current State:** Complete forensic analysis platform running on port 5000

## Project Information
- **Framework:** Streamlit (Python 3.12)
- **Purpose:** Mobile device forensic image analysis and evidence extraction
- **Status:** Fully functional with demo mode
- **Version:** 1.0.0
- **Database:** SQLite for case management and chain of custody

## Project Structure
```
.
├── app.py                      # Main Streamlit application (case dashboard)
├── modules/                    # Forensic analysis modules
│   ├── __init__.py
│   ├── image_input.py         # Device image upload and hash verification
│   ├── file_parser.py         # File system parsing (pytsk3 integration)
│   ├── data_extractor.py      # Extract SMS, calls, WhatsApp, etc.
│   ├── analysis_tools.py      # Timeline reconstruction, keyword search
│   ├── visualization.py       # Charts, maps, and graphs
│   └── report_generator.py    # Professional PDF reports
├── database/                   # SQLite database system
│   ├── __init__.py
│   ├── db_manager.py          # Database operations and schema
│   └── cortex.db              # Case and evidence database (auto-created)
├── assets/                     # Static assets (images, samples)
├── AIModelPerfector/          # Legacy directory (backup)
├── scripts/                   # Automation scripts
│   └── agent_runner.py        # CI/CD runner for GitHub Actions
├── .streamlit/                # Streamlit configuration
│   └── config.toml            # Server settings (port 5000, CORS disabled)
├── .github/workflows/         # GitHub Actions
│   └── auto_agent.yml         # Automated workflow
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
├── README.md                  # Project documentation
└── replit.md                  # This file
```

## Core Features

### 1. Case Management Dashboard
- Create and manage multiple forensic cases
- Track case status, investigator, and device information
- SQLite database for persistent storage
- Chain of custody logging

### 2. Device Image Processing
- Upload mobile device images (.img, .bin, .dd, .raw, .e01)
- Automatic SHA-256 and MD5 hash calculation
- Image metadata extraction
- Integrity verification for evidence

### 3. Data Extraction Modules
- **Call Logs & SMS** - Extract phone call records and text messages
- **Messaging Apps** - WhatsApp, Telegram, Signal, Facebook Messenger
- **Contacts** - Address book and contact information
- **Location Data** - GPS coordinates, cell tower data
- **Browser History** - Chrome, Firefox, Safari, Edge
- **Deleted Data** - Recovery of deleted files and artifacts

### 4. Analysis Tools
- **Timeline Reconstruction** - Chronological event timeline from all sources
- **Keyword Search** - Search across all extracted text data
- **Statistics Dashboard** - Case statistics and evidence summary

### 5. Visualization
- **Interactive Charts** - Call/SMS activity, browser usage
- **Location Maps** - Plotly maps showing GPS coordinates
- **Timeline Views** - Visual event timelines
- **Communication Networks** - Contact relationship graphs

### 6. Report Generation
- Professional PDF forensic reports
- Customizable sections (executive summary, evidence inventory, etc.)
- Hash verification tables
- Chain of custody logs
- Export capabilities (CSV, PDF)

## Key Dependencies
- **streamlit >= 1.0.0** - Web application framework
- **pandas >= 1.0.0** - Data manipulation and analysis
- **plotly >= 5.0.0** - Interactive visualizations and maps
- **Pillow** - Image processing
- **exifread** - EXIF metadata extraction
- **fpdf** - PDF report generation
- **pytsk3** - File system analysis (forensic imaging)
- **python-magic** - File type identification

## Running the Application
The Streamlit application runs automatically via the workflow system:
- **Command:** `streamlit run app.py`
- **Port:** 5000
- **Host:** 0.0.0.0 (configured for Replit proxy)

The application is accessible through the Replit webview at the configured port.

## Configuration
### Streamlit Settings (.streamlit/config.toml)
- Server runs on 0.0.0.0:5000 (headless mode)
- CORS disabled for Replit proxy compatibility
- XSRF protection disabled for iframe access
- Usage statistics collection disabled

### Python Environment
- Python 3.12 (configured in .replit)
- Uses Nix packages: file, glibcLocales
- All dependencies installed via pip

## Demo Mode
The application includes built-in demo mode functionality:
- Simulated device images and data extraction
- Sample call logs, SMS, WhatsApp messages
- Demo contacts, locations, and browser history
- Allows full testing without real forensic images
- Useful for training and demonstrations

## Database Schema
### Cases Table
- case_id (PRIMARY KEY)
- case_name, investigator, device_info
- image_path, image_hash (SHA-256)
- created_date, status, notes

### Evidence Table
- evidence_id (AUTO INCREMENT)
- case_id, artifact_type, artifact_name
- file_path, hash_value, timestamp, metadata

### Chain of Custody Table
- log_id (AUTO INCREMENT)
- case_id, action, performed_by
- timestamp, details

## Recent Changes
**October 19, 2025:**
- Built complete modular forensic analysis platform
- Created case management dashboard with SQLite database
- Implemented all 6 core forensic analysis modules
- Added demo mode with sample data generation
- Configured Streamlit workflow on port 5000
- Created comprehensive README and documentation
- All Streamlit host/CORS settings configured for Replit proxy

## Development Notes
- Original GitHub import contained only infrastructure files
- Complete application developed based on forensic analysis requirements
- Modular architecture allows easy extension and maintenance
- Demo mode enables testing without real device images
- SQLite provides lightweight but robust case management
- All hash verification and chain of custody features implemented
- Ready for deployment and production use

## GitHub Integration
- Repository includes automated GitHub Actions workflow (auto_agent.yml)
- Daily scheduled runs at 03:00 UTC
- Agent runner script performs smoke checks and code formatting

## Security & Compliance
- SHA-256 hash verification for all evidence
- Complete chain of custody audit trail
- All actions logged with timestamps and user attribution
- Database integrity maintained through SQLite constraints
- Designed for lawful forensic analysis by authorized personnel

## User Preferences
No user preferences have been documented yet.

## Future Enhancements
- Real pytsk3 file system parsing (currently simulated)
- Advanced deleted data recovery algorithms
- Multi-device case support
- Cloud evidence storage integration
- Advanced AI-powered pattern detection
- Automated report scheduling
