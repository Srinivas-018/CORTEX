# CORTEX - Quick Start Guide

## Running the Application

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py

# Access at http://localhost:8501
```

### Streamlit Cloud Deployment
1. Push code to GitHub
2. Connect Streamlit Cloud to repository
3. Deploy with requirements.txt

---

## Basic Workflow

### 1. Create a Case
```
Dashboard → Create New Case Form
- Enter Case ID (e.g., CASE-2025-001)
- Case Name
- Investigator Name
- Device Info (optional)
- Notes (optional)
```

### 2. Upload Device Image
```
Open Case → Image Input Tab
- Click "Select Device Image"
- Upload .img, .bin, .dd, .raw, or .e01 file
- Wait for hash calculation (progress bar shown)
- Click "✅ Verify & Process Image"
```

### 3. Choose Extraction Mode
```
Data Extraction Tab → Mode Selector
- Demo Mode: Generate sample data for testing
- Real Extraction: Parse actual databases from image
```

### 4. Extract Artifacts

#### Calls & SMS
```
- Click "Extract Call Logs"
- Click "Extract SMS Messages"
- View extracted data in table
- Export to CSV if needed
```

#### Messaging Apps
```
- Select app (WhatsApp, Telegram, Signal, Facebook)
- Click "Extract [App] Data"
- View messages in table
- Export to CSV
```

#### Contacts
```
- Click "Extract Contacts"
- View contacts list
- Export to CSV
```

#### Location Data
```
- Click "Extract Location History"
- View GPS coordinates
- Go to Visualization tab to see map
- Export to CSV
```

#### Browser History
```
- Select browser (Chrome, Firefox, Safari, Edge)
- Click "Extract [Browser] History"
- View browsing history
- Export to CSV
```

#### Deleted Data
```
- Click "Scan for Deleted Data"
- View potentially recoverable files
- Export list to CSV
```

### 5. Analyze Data

#### Timeline Reconstruction
```
Analysis Tools Tab → Timeline Reconstruction
- Click "Generate Timeline"
- View chronological events
- Filter by event type
- Export to CSV
```

#### Keyword Search
```
Analysis Tools Tab → Keyword Search
- Enter search term
- Choose case sensitive option
- Click "Search"
- View matches across all data
```

#### Statistics
```
Analysis Tools Tab → Statistics
- View case evidence summary
- See artifact counts
- Review extraction status
```

### 6. Visualize Findings

#### Charts
```
Visualization Tab → Charts
- Call activity pie chart
- Hourly call distribution
- SMS volume by contact
- Browser activity
```

#### Location Map
```
Visualization Tab → Location Map
- Interactive map with GPS points
- Color-coded by source (GPS/WiFi/Cell)
- Size by accuracy
- Hover for details
```

#### Timeline View
```
Visualization Tab → Timeline View
- Event activity over time
- Distribution by type
- Interactive line charts
```

#### Communication Network
```
Visualization Tab → Communication Network
- Contact communication matrix
- Scatter plot of calls vs SMS
- Top communicators
```

### 7. Generate Report
```
Reports Tab
- Configure report settings:
  * Report title
  * Lead investigator
  * Agency
  * Report date
  * Classification level
  
- Select sections to include:
  * Executive Summary
  * Device Information
  * Evidence Inventory
  * Timeline Analysis
  * Data Extraction Results
  * Chain of Custody
  * Hash Verification
  * Conclusions

- Write executive summary
- Write conclusions
- Click "Generate Report"
- Download PDF
```

---

## Tips & Best Practices

### File Upload
- ✅ Large files (> 1GB) are supported
- ✅ Progress bars show processing status
- ✅ Hash verification ensures integrity
- ⚠️ Very large files may take time

### Extraction Modes
- 🎭 **Demo Mode**: Use for training, demos, testing workflows
- 🔍 **Real Extraction**: Use for actual forensic investigations
- 💡 Start with demo mode to learn the interface

### Data Export
- 📊 All data can be exported to CSV
- 💾 Export frequently to save work
- 📁 Organize exports by artifact type

### Reports
- 📄 Generate reports after completing analysis
- ✏️ Write detailed summaries and conclusions
- 🔐 Choose appropriate classification level
- 📋 Include all relevant sections

### Case Management
- 📝 Use descriptive case IDs and names
- 👤 Record investigator names accurately
- 📌 Add detailed notes for future reference
- 🗑️ Delete test cases regularly

### Chain of Custody
- 🔗 Every action is logged automatically
- ⏰ Timestamps recorded for all operations
- 🔐 Hash values stored for verification
- 📋 View complete audit trail in reports

---

## Troubleshooting

### Application Won't Start
```bash
# Check if all dependencies are installed
pip install -r requirements.txt

# Run with verbose logging
streamlit run app.py --logger.level debug
```

### Large File Upload Fails
- Check available disk space
- Verify file format is supported
- Try with smaller file first
- Check Streamlit Cloud limits if deployed

### Real Extraction Shows Demo Data
- Verify image file was saved (click "Verify & Process Image")
- Check image file format is valid
- Ensure pytsk3 is installed
- Check error messages in extraction tab

### Visualization Not Showing
- Extract data first in Data Extraction tab
- Check if data exists in session
- Refresh the page if needed
- Generate timeline for timeline visualizations

### Report Generation Fails
- Verify fpdf is installed
- Check if case data exists
- Ensure no special characters in text fields
- Try with shorter summary/conclusions

### Memory Issues
- Close other applications
- Process files in smaller batches
- Use demo mode for testing
- Upgrade to larger Streamlit Cloud plan

---

## Keyboard Shortcuts

- `R` - Rerun the app
- `C` - Clear cache
- `?` - Show keyboard shortcuts
- `Ctrl+C` - Stop the app (in terminal)

---

## Support & Documentation

- **Full Documentation**: See README.md
- **Technical Details**: See IMPROVEMENTS.md
- **Case Studies**: See examples/ folder (if available)
- **Issues**: Report on GitHub

---

## Example Use Cases

### Training Scenario
1. Create demo case
2. Use demo mode extraction
3. Practice timeline analysis
4. Generate sample reports
5. Learn interface features

### Real Investigation
1. Create official case
2. Upload actual device image
3. Use real extraction mode
4. Analyze extracted data
5. Search for evidence
6. Generate official report

### Data Recovery
1. Upload corrupted image
2. Try demo mode first
3. Switch to real extraction
4. Use deleted data scan
5. Export recovered artifacts

---

## Security Considerations

- 🔒 Store device images securely
- 🔐 Use encryption for sensitive data
- 👥 Limit access to authorized personnel
- 🗑️ Securely delete cases when closed
- 📋 Maintain complete audit trails
- ⚖️ Follow legal requirements

---

## Next Steps

1. ✅ Complete this quick start guide
2. 📚 Read full README.md for details
3. 🎓 Practice with demo data
4. 🔍 Perform real investigations
5. 📊 Master visualization tools
6. 📄 Generate professional reports

---

**Need Help?**
- Check IMPROVEMENTS.md for technical details
- Review README.md for comprehensive guide
- Search documentation for specific features
- Report issues on GitHub

---

© 2025 CORTEX - Mobile Device Forensics Analyzer
