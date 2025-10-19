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

## Technology Stack

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
