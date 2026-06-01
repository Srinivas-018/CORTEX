"""
Image Input Module
Handles upload and verification of mobile device images (.img, .bin, .dd)
"""

import streamlit as st
import hashlib
from pathlib import Path
import tempfile
import os
import subprocess
import shutil
from datetime import datetime
import json
from database.db_manager import get_case

# Chunk size for processing large files (8MB chunks)
CHUNK_SIZE = 8 * 1024 * 1024

def check_adb_available():
    """Check if ADB is available in system PATH"""
    return shutil.which("adb") is not None

def get_connected_devices():
    """Get list of connected Android devices via ADB"""
    devices = []
    try:
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            if line.strip() and "device" in line:
                parts = line.split()
                serial = parts[0]
                model = "Unknown"
                for part in parts:
                    if part.startswith("model:"):
                        model = part.split(":")[1]
                devices.append({"serial": serial, "model": model, "details": line})
    except Exception:
        pass
    return devices

def acquire_logical_image(device_serial, case_id):
    """Acquire logical data (sdcard) from device and zip it"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = tempfile.mkdtemp()
        dest_zip = os.path.join(tempfile.gettempdir(), f"logical_dump_{device_serial}_{timestamp}.zip")
        
        # Simple logical acquisition of /sdcard/Download as a demo/safe path 
        # In real forensics, we'd aim for more, but /sdcard is good for logical
        # Limited to Download to avoid massive dumps in this demo
        cmd = ["adb", "-s", device_serial, "pull", "/sdcard/Download", target_dir]
        
        subprocess.run(cmd, check=True)
        
        # Zip the directory
        shutil.make_archive(dest_zip.replace('.zip', ''), 'zip', target_dir)
        
        # Cleanup temp dir
        shutil.rmtree(target_dir, ignore_errors=True)
        
        return dest_zip, f"logical_dump_{timestamp}.zip"
    except Exception as e:
        return None, str(e)

def render_direct_connection(case_id):
    """Render interface for direct device connection"""
    st.subheader("🔌 Direct Device Connection")
    
    conn_mode = st.radio(
        "Select Connection Method",
        ["Browser-based (WebUSB/WebADB - Vercel & Cloud Friendly)", "Local Server-based (Requires local ADB)"]
    )
    
    if conn_mode == "Browser-based (WebUSB/WebADB - Vercel & Cloud Friendly)":
        st.info("⚡ This mode runs entirely in your web browser. You can connect your phone directly via USB and run logical extractions without installing any local tools.")
        
        # HTML + JS WebUSB Component
        webusb_html = """
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {
              background-color: #0f172a;
              color: #e2e8f0;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              margin: 0;
              padding: 10px;
            }
            .card {
              background: rgba(30, 41, 59, 0.7);
              border: 1px solid rgba(255, 255, 255, 0.1);
              border-radius: 12px;
              padding: 20px;
              box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }
            .title {
              font-size: 18px;
              font-weight: 600;
              color: #38bdf8;
              margin-bottom: 15px;
              display: flex;
              align-items: center;
              gap: 8px;
            }
            .step-list {
              margin-bottom: 20px;
            }
            .step {
              display: flex;
              align-items: flex-start;
              margin-bottom: 12px;
              font-size: 14px;
            }
            .step-num {
              background: #0284c7;
              color: white;
              border-radius: 50%;
              width: 22px;
              height: 22px;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 12px;
              font-weight: bold;
              margin-right: 10px;
              flex-shrink: 0;
            }
            .btn {
              background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
              color: white;
              border: none;
              padding: 10px 18px;
              border-radius: 6px;
              font-weight: 500;
              cursor: pointer;
              font-size: 14px;
              transition: all 0.2s;
              display: inline-flex;
              align-items: center;
              gap: 6px;
            }
            .btn:hover {
              transform: translateY(-1px);
              box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
            }
            .btn:disabled {
              background: #475569;
              cursor: not-allowed;
              transform: none;
              box-shadow: none;
            }
            .btn-green {
              background: linear-gradient(135deg, #10b981 0%, #047857 100%);
            }
            .btn-green:hover {
              box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            }
            .terminal {
              background-color: #020617;
              border: 1px solid rgba(255, 255, 255, 0.05);
              border-radius: 8px;
              font-family: monospace;
              padding: 12px;
              height: 180px;
              overflow-y: auto;
              font-size: 12px;
              color: #34d399;
              margin-top: 15px;
            }
            .status-badge {
              display: inline-block;
              padding: 3px 8px;
              border-radius: 12px;
              font-size: 11px;
              font-weight: bold;
              background: rgba(239, 68, 68, 0.2);
              color: #ef4444;
              margin-top: 5px;
            }
            .status-badge.connected {
              background: rgba(16, 185, 129, 0.2);
              color: #10b981;
            }
          </style>
        </head>
        <body>
          <div class="card">
            <div class="title">🔌 Browser WebUSB-ADB Logical Extractor</div>
            <div class="step-list">
              <div class="step">
                <span class="step-num">1</span>
                <div>Connect Android device via USB and enable <b>USB Debugging</b>. (Tap Build Number 7 times in Settings > About to enable Developer Options).</div>
              </div>
              <div class="step">
                <span class="step-num">2</span>
                <div>Click <b>Connect Device</b> and select your phone in the browser prompt.</div>
              </div>
              <div class="step">
                <span class="step-num">3</span>
                <div>Check your phone's screen and authorize the <b>Allow USB debugging</b> RSA prompt.</div>
              </div>
              <div class="step">
                <span class="step-num">4</span>
                <div>Click <b>Extract Android Profile</b> to extract metadata, package list, process logs, and logcat files.</div>
              </div>
            </div>
            
            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
              <button id="btn-connect" class="btn" onclick="connectAdb()">🔗 Connect Device</button>
              <button id="btn-extract" class="btn btn-green" onclick="startExtraction()" disabled>🚀 Extract Android Profile</button>
              <button id="btn-download" class="btn" onclick="downloadJSON()" style="display:none; background: #475569;">💾 Download Profile (.json)</button>
            </div>
            
            <div id="status" class="status-badge">Disconnected</div>
            <div id="device-info" style="margin-top: 10px; font-size: 13px; font-weight: 500;"></div>
            
            <div class="terminal" id="log-console">Console log initialized...</div>
          </div>

          <script src="https://cdn.jsdelivr.net/npm/webadb@latest/webadb.js"></script>
          <script>
            let webusb = null;
            let adb = null;
            let extractedProfile = null;
            
            function log(msg) {
              const console = document.getElementById("log-console");
              const time = new Date().toLocaleTimeString();
              console.innerHTML += `<br>[${time}] ${msg}`;
              console.scrollTop = console.scrollHeight;
            }
            
            function setStatus(text, isConnected) {
              const badge = document.getElementById("status");
              badge.innerText = text;
              if (isConnected) {
                badge.className = "status-badge connected";
              } else {
                badge.className = "status-badge";
              }
            }
            
            async function connectAdb() {
              try {
                log("Searching for USB device...");
                webusb = await Adb.open("WebUSB");
                
                log("Negotiating ADB protocol connection...");
                adb = await webusb.connectAdb("host::");
                
                log("Checking authentication... please check device screen for RSA permission prompt!");
                setStatus("Waiting for Auth", false);
                
                // Wait briefly for handshake
                let shell = await adb.shell("getprop ro.product.model");
                let response = await shell.receive();
                
                let model = "Android Device";
                if (response && response.data) {
                  model = new TextDecoder().decode(response.data).trim();
                }
                
                log(`Successfully authenticated! Device model: ${model}`);
                document.getElementById("device-info").innerText = `Connected Device: ${model}`;
                setStatus("Connected", true);
                document.getElementById("btn-extract").disabled = false;
                
              } catch (err) {
                log(`Connection failed: ${err.message}`);
                setStatus("Disconnected", false);
                document.getElementById("btn-extract").disabled = true;
              }
            }
            
            async function runShellCmd(cmd) {
              let shell = await adb.shell(cmd);
              let out = "";
              while (true) {
                let response = await shell.receive();
                if (!response || !response.data) break;
                out += new TextDecoder().decode(response.data);
              }
              return out.trim();
            }
            
            async function startExtraction() {
              if (!adb) {
                log("No device connected!");
                return;
              }
              
              try {
                log("Starting logical forensic profile extraction...");
                document.getElementById("btn-extract").disabled = true;
                
                log("1/4: Querying System Properties...");
                let manufacturer = await runShellCmd("getprop ro.product.manufacturer");
                let model = await runShellCmd("getprop ro.product.model");
                let brand = await runShellCmd("getprop ro.product.brand");
                let release = await runShellCmd("getprop ro.build.version.release");
                let sdk = await runShellCmd("getprop ro.build.version.sdk");
                let securityPatch = await runShellCmd("getprop ro.build.version.security_patch");
                let fingerprint = await runShellCmd("getprop ro.build.fingerprint");
                let bootloader = await runShellCmd("getprop ro.boot.flash.locked");
                let serial = await runShellCmd("getprop ro.serialno");
                let rootCheck = await runShellCmd("su -c id");
                
                let isRooted = rootCheck.includes("uid=0");
                
                let props = {
                  "Manufacturer": manufacturer || "Unknown",
                  "Model": model || "Unknown",
                  "Brand": brand || "Unknown",
                  "Android Version": release || "Unknown",
                  "SDK Level": sdk || "Unknown",
                  "Security Patch": securityPatch || "Unknown",
                  "Build Fingerprint": fingerprint || "Unknown",
                  "Bootloader State": bootloader === "1" ? "Locked (Secure)" : (bootloader === "0" ? "Unlocked (Vulnerable)" : "Unknown"),
                  "Serial Number": serial || "Unknown",
                  "Root Status": isRooted ? "Rooted (su accessible)" : "Non-Rooted",
                  "Extraction Timestamp": new Date().toISOString()
                };
                
                log("2/4: Enumerating Installed Packages...");
                let pkgsRaw = await runShellCmd("pm list packages -f");
                let packages = [];
                pkgsRaw.split("\\n").forEach(line => {
                  if (line.startsWith("package:")) {
                    let parts = line.replace("package:", "").split("=");
                    if (parts.length >= 2) {
                      let path = parts[0];
                      let pkg = parts.slice(1).join("=");
                      let isSystem = path.startsWith("/system/") || path.startsWith("/product/");
                      packages.push({"Package": pkg, "Path": path, "Type": isSystem ? "System" : "Third-Party"});
                    }
                  }
                });
                
                log("3/4: Querying Active Process List...");
                let psRaw = await runShellCmd("ps -A || ps");
                let processes = [];
                let psLines = psRaw.split("\\n");
                if (psLines.length > 1) {
                  let header = psLines[0].split(/\\s+/);
                  let userIdx = header.indexOf("USER");
                  let pidIdx = header.indexOf("PID");
                  let nameIdx = header.indexOf("NAME");
                  if (nameIdx === -1) nameIdx = header.indexOf("CMD");
                  
                  for (let i = 1; i < psLines.length; i++) {
                    let parts = psLines[i].split(/\\s+/);
                    if (parts.length > Math.max(userIdx, pidIdx, nameIdx)) {
                      processes.push({
                        "PID": parts[pidIdx],
                        "User": parts[userIdx],
                        "Process Name": parts[nameIdx]
                      });
                    }
                  }
                }
                
                log("4/4: Pulling Logcat System Logs...");
                let logcatRaw = await runShellCmd("logcat -d -t 300 -v threadtime");
                let logcat = logcatRaw.split("\\n").map(l => ({"Log Entry": l.trim()})).filter(l => l["Log Entry"]);
                
                extractedProfile = {
                  "device_properties": props,
                  "installed_packages": packages,
                  "running_processes": processes,
                  "logcat": logcat,
                  "source": "WebUSB-ADB Browser Extraction"
                };
                
                log("Extraction complete! File ready for saving/downloading.");
                document.getElementById("btn-download").style.display = "inline-flex";
                document.getElementById("btn-extract").disabled = false;
                
              } catch (err) {
                log(`Extraction failed: ${err.message}`);
                document.getElementById("btn-extract").disabled = false;
              }
            }
            
            function downloadJSON() {
              if (!extractedProfile) return;
              
              const jsonStr = JSON.stringify(extractedProfile, null, 2);
              const blob = new Blob([jsonStr], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `cortex_android_logical_profile_${extractedProfile.device_properties.Model.replace(/\\s+/g, "_")}.json`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
              log("Forensic profile JSON file downloaded successfully!");
            }
          </script>
        </body>
        </html>
        """
        st.components.v1.html(webusb_html, height=520, scrolling=True)
        
        st.divider()
        st.subheader("📥 Load Extracted Profile (.json)")
        st.write("After extracting the profile and downloading the `.json` file above, upload it here to import the device data into the case.")
        
        uploaded_profile = st.file_uploader("Upload Logical Profile JSON", type=["json"], key="wasm_profile_uploader")
        
        if uploaded_profile is not None:
            try:
                # Read JSON
                profile_data = json.load(uploaded_profile)
                
                # Check structure
                if "device_properties" not in profile_data:
                    st.error("Invalid JSON profile. Missing 'device_properties'.")
                    return None
                    
                # Save to disk
                props = profile_data["device_properties"]
                model = props.get("Model", "Unknown")
                filename = f"logical_profile_{model.replace(' ', '_')}.json"
                
                # Create directory
                extract_dir = os.path.join(os.getcwd(), "extracted_evidence", case_id)
                os.makedirs(extract_dir, exist_ok=True)
                dest_path = os.path.join(extract_dir, filename)
                
                # Write to disk
                uploaded_profile.seek(0)
                with open(dest_path, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=4)
                    
                # Calculate Hash
                uploaded_profile.seek(0)
                sha256_hash = hashlib.sha256(uploaded_profile.read()).hexdigest()
                
                # Update case & evidence
                from database.db_manager import update_case, add_chain_of_custody, add_evidence
                update_case(case_id, image_path=dest_path, image_hash=sha256_hash)
                
                add_evidence(
                    case_id,
                    "Logical Profile",
                    filename,
                    file_path=dest_path,
                    hash_value=sha256_hash,
                    metadata=props
                )
                
                add_chain_of_custody(
                    case_id,
                    "Acquisition",
                    st.session_state.get('investigator', 'Unknown'),
                    f"Imported logical forensic profile for {model} via WebUSB"
                )
                
                st.success(f"✅ Successfully loaded logical profile for {model} into case!")
                st.balloons()
                
                # Refresh session state
                st.session_state['image_path'] = dest_path
                return {
                    'filename': filename,
                    'file_path': dest_path,
                    'sha256': sha256_hash,
                    'size': 0,
                    'metadata': props
                }
                
            except Exception as e:
                st.error(f"Error loading profile: {str(e)}")
                
    else:
        # Local Server-based (Native ADB)
        if not check_adb_available():
            st.error("❌ ADB (Android Debug Bridge) not found in system PATH.")
            st.warning("Please install Android Platform Tools and add 'adb' to your PATH variables.")
            return
            
        if st.button("🔄 Scan for Devices"):
            st.rerun()
            
        from modules.adb_forensics import get_connected_devices, run_full_logical_extraction
        devices = get_connected_devices()
        
        if not devices:
            st.warning("No devices detected. Please check your connection and USB Debugging settings.")
            st.markdown("""
            **Troubleshooting:**
            1. Connect phone via USB cable
            2. Enable **Developer Options** (Tap Build Number 7 times)
            3. Enable **USB Debugging**
            4. Accept the RSA fingerprint prompt on the device
            """)
            return
            
        st.success(f"Found {len(devices)} device(s)")
        
        selected_device = st.selectbox(
            "Select Target Device",
            options=devices,
            format_func=lambda d: f"{d['model']} ({d['serial']}) - [{d['status']}]"
        )
        
        if selected_device:
            if selected_device["status"] == "Unauthorized":
                st.warning("⚠️ This device is unauthorized. Please look at the phone screen and allow USB debugging.")
                return
                
            st.write("### Acquisition Options")
            acq_type = st.radio("Acquisition Type", ["Forensic Profile (Metadata, Packages, Processes, Logs)", "Logical Dump (Zip /sdcard/Download)"])
            
            if acq_type == "Forensic Profile (Metadata, Packages, Processes, Logs)":
                st.info("Extracts comprehensive system configurations, installed applications, active processes, and logs.")
                if st.button("🚀 Start Acquisition"):
                    with st.spinner("Extracting forensic profile..."):
                        file_path, profile_data = run_full_logical_extraction(selected_device['serial'], case_id)
                        
                        if file_path:
                            st.success("✅ Forensic Profile extracted successfully!")
                            st.write(f"**Saved to:** {file_path}")
                            
                            # Hashing
                            hash_progress = st.progress(0, text="Calculating Hash...")
                            with open(file_path, "rb") as f:
                                sha256_hash = calculate_hash_chunked(f, 'sha256')
                            hash_progress.progress(100, text="Done")
                            
                            props = profile_data.get("device_properties", {})
                            
                            from database.db_manager import update_case, add_chain_of_custody, add_evidence
                            update_case(case_id, image_path=file_path, image_hash=sha256_hash)
                            
                            add_evidence(
                                case_id,
                                "Logical Profile",
                                os.path.basename(file_path),
                                file_path=file_path,
                                hash_value=sha256_hash,
                                metadata=props
                            )
                            
                            add_chain_of_custody(
                                case_id,
                                "Acquisition",
                                st.session_state.get('investigator', 'Unknown'),
                                f"Acquired full logical profile from {selected_device['model']} ({selected_device['serial']})"
                            )
                            
                            st.session_state['image_path'] = file_path
                            st.balloons()
                            return {
                                'filename': os.path.basename(file_path),
                                'file_path': file_path,
                                'sha256': sha256_hash,
                                'size': 0,
                                'metadata': props
                            }
                        else:
                            st.error(f"Acquisition failed: {profile_data}")
            else:
                # Zip /sdcard/Download
                st.write("Extracts contents from `/sdcard/Download` folder as a logical container (ZIP).")
                if st.button("🚀 Start Acquisition"):
                    with st.spinner("Acquiring data from device... Do not disconnect!"):
                        file_path, name_or_error = acquire_logical_image(selected_device['serial'], case_id)
                        
                        if file_path:
                            st.success("✅ Acquisition completed successfully!")
                            st.write(f"**Saved to:** {file_path}")
                            
                            try:
                                # Hashing
                                hash_progress = st.progress(0, text="Calculating Hash...")
                                with open(file_path, "rb") as f:
                                    sha256_hash = calculate_hash_chunked(f, 'sha256')
                                hash_progress.progress(100, text="Done")
                                
                                metadata = {
                                    "Source": "Direct Connection",
                                    "Device Model": selected_device['model'],
                                    "Serial": selected_device['serial'],
                                    "Acquisition Type": "Logical"
                                }
                                
                                from database.db_manager import update_case, add_chain_of_custody, add_evidence
                                update_case(case_id, image_path=file_path, image_hash=sha256_hash)
                                
                                add_evidence(
                                    case_id, 
                                    "Logical Dump", 
                                    name_or_error,
                                    file_path=file_path,
                                    hash_value=sha256_hash,
                                    metadata=metadata
                                )
                                
                                add_chain_of_custody(
                                    case_id, 
                                    "Acquisition", 
                                    st.session_state.get('investigator', 'Unknown'),
                                    f"Acquired logical image from {selected_device['model']} ({selected_device['serial']})"
                                )
                                
                                st.session_state['image_path'] = file_path
                                st.balloons()
                                return {
                                    'filename': name_or_error,
                                    'file_path': file_path,
                                    'sha256': sha256_hash,
                                    'size': 0,
                                    'metadata': metadata
                                }
                            except Exception as e:
                                st.error(f"Error registering evidence: {str(e)}")
                        else:
                            st.error(f"Acquisition failed: {name_or_error}")

def calculate_hash_chunked(uploaded_file, algorithm='sha256'):
    """
    Calculate hash of file content using chunked reading.
    This prevents memory overflow for large files.
    """
    hash_obj = hashlib.new(algorithm)
    
    # Reset file pointer to beginning
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    
    # Read and hash in chunks
    bytes_read = 0
    while True:
        chunk = uploaded_file.read(CHUNK_SIZE)
        if not chunk:
            break
        hash_obj.update(chunk)
        bytes_read += len(chunk)
    
    # Reset file pointer for potential reuse
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    
    return hash_obj.hexdigest()

def save_uploaded_file_to_disk(uploaded_file, dest_path=None):
    """Save Streamlit uploaded_file to disk in chunks. Returns path."""
    if dest_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.img')
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

def get_file_size_mb(uploaded_file):
    """Get file size in MB without loading entire file into memory"""
    try:
        uploaded_file.seek(0, 2)  # Seek to end
        size_bytes = uploaded_file.tell()
        uploaded_file.seek(0)  # Reset to beginning
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0

def render_image_input(case_id):
    """Render the image input and verification interface"""
    st.header("📱 Device Image Input & Verification")
    
    # Bypass for Demo Case
    if case_id == "DEMO-CASE":
        st.success("✅ Demo Image Loaded Successfully")
        st.info("This is a simulated Android device image for demonstration purposes.")
        
        col1, col2 = st.columns(2)
        with col1:
             st.subheader("Image Information")
             st.write("**Filename:** demo_device_image.dd")
             st.write("**Source:** Synthetic Demo Data (India Region)")
             st.write("**Size:** 32.00 GB")
             st.write("**Detected OS:** Android 12 (Demo)")
        
        with col2:
             st.subheader("Hash Verification")
             st.code("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0", language="text")
             st.caption("SHA-256 Hash (Simulated)")
             
        return {
            'filename': 'demo_device_image.dd',
            'file_path': 'demo_device_image.dd',
            'sha256': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
            'size': 32768, # MB
            'metadata': {
                'Detected OS': 'Android',
                'File System Type': 'ext4'
            }
        }
    
    # Check if image is already uploaded for this case
    case = get_case(case_id)
    if case and case[4]:
        image_path = case[4]
        if os.path.exists(image_path):
            st.success("✅ Image File Uploaded & Verified")
            
            image_hash = case[5] if case[5] else "Not recorded"
            filename = os.path.basename(image_path)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Image Information")
                st.write(f"**Filename:** {filename}")
                st.write(f"**Path:** {image_path}")
                try:
                    size_mb = os.path.getsize(image_path) / (1024 * 1024)
                    st.write(f"**Size:** {size_mb:.2f} MB")
                except:
                    pass
            
            with col2:
                st.subheader("Hash Verification")
                st.code(image_hash, language="text")
                st.caption("SHA-256 Hash")
            
            # Return image info so other tabs function including demo case which might rely on this
            return {
                'filename': filename,
                'file_path': image_path,
                'sha256': image_hash,
                # Add dummy size/metadata if needed by consumer, or read real ones
                'size': 0,
                'metadata': {}
            }
        else:
            st.error(f"❌ Image file recorded for this case was not found on disk: {image_path}")
            st.warning("Please locate the file and provide the path again below.")
    

    
    input_method = st.radio("Select Input Source", ["Upload / Local File Path", "Direct Device Connection (USB/ADB)"])
    
    if input_method == "Direct Device Connection (USB/ADB)":
        return render_direct_connection(case_id)
        
    st.info("Enter the absolute file path of the mobile device forensic image (.img, .bin, .dd, .raw)")
    
    selected_file = None
    uploaded_file = None
    is_local = False
    
    # Session state for local path
    if 'verified_local_path' not in st.session_state:
        st.session_state['verified_local_path'] = None
    
    local_path = st.text_input("Enter Absolute File Path", placeholder="C:\\Forensics\\Case_001\\image.dd")
    
    # Reset verified path if input changes
    if local_path != st.session_state.get('verified_local_path'):
            st.session_state['verified_local_path'] = None
            
    if local_path:
        if os.path.exists(local_path) and os.path.isfile(local_path):
            if st.button("Load Local File", key="load_local") or st.session_state.get('verified_local_path') == local_path:
                try:
                    # Mark as verified
                    st.session_state['verified_local_path'] = local_path
                    st.success(f"File found: {os.path.basename(local_path)}")
                except Exception as e:
                    st.error(f"Error checking file: {str(e)}")
        elif local_path:
            st.warning("File not found or invalid path")

    # Determine which file to use
    if uploaded_file:
        selected_file = uploaded_file
        is_local = False
    elif st.session_state.get('verified_local_path'):
        try:
            selected_file = open(st.session_state['verified_local_path'], 'rb')
            is_local = True
        except Exception as e:
            st.error(f"Error opening local file: {str(e)}")
            st.session_state['verified_local_path'] = None

    if selected_file is not None:
        try:
            # For local files, we need to handle them carefully
            # Ensure we are at start of file
            selected_file.seek(0)
            
            # File name handling
            file_name = selected_file.name
            if is_local:
                file_name = os.path.basename(selected_file.name)
            
            # Get file size
            file_size_mb = 0
            try:
                if is_local:
                    file_size_mb = os.path.getsize(selected_file.name) / (1024 * 1024)
                else:
                    file_size_mb = get_file_size_mb(selected_file)
            except:
                pass
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Image Information")
                st.write(f"**Filename:** {file_name}")
                st.write(f"**Source:** {'Local Storage' if is_local else 'Upload'}")
                st.write(f"**Size:** {file_size_mb:.2f} MB ({file_size_mb/1024:.2f} GB)")
                
                if file_size_mb > 1000:
                    st.warning("⚠️ Large file detected. Processing may take time.")
            
            with col2:
                st.subheader("Hash Verification")
                
                hash_progress = st.progress(0, text="Calculating SHA-256 hash...")
                
                try:
                    sha256_hash = calculate_hash_chunked(selected_file, 'sha256')
                    hash_progress.progress(50, text="Calculating MD5 hash...")
                    md5_hash = calculate_hash_chunked(selected_file, 'md5')
                    hash_progress.progress(100, text="Hash calculation complete!")
                    
                    st.code(sha256_hash, language="text")
                    st.caption("SHA-256 Hash")
                    st.text(f"MD5: {md5_hash}")
                    
                except Exception as e:
                    st.error(f"Error calculating hash: {str(e)}")
                    if is_local: selected_file.close()
                    return None
            
            st.divider()
            
            st.subheader("Image Metadata")
            
            metadata_progress = st.progress(0, text="Analyzing image structure...")
            metadata = analyze_image_structure_chunked(selected_file)
            metadata_progress.progress(100, text="Analysis complete!")
            
            for key, value in metadata.items():
                st.write(f"**{key}:** {value}")
            
            col_btn1, col_btn2 = st.columns(2)
            
            # Use a callback or unique key to avoid state issues with button
            with col_btn1:
                if st.button("✅ Verify & Add to Case", type="primary"):
                    with st.spinner("Registering evidence..."):
                        try:
                            final_path = ""
                            image_hash = sha256_hash
                            
                            if is_local:
                                # Use the local path directly
                                final_path = selected_file.name # absolute path from open()
                                # Close the handle as we just store the path
                                selected_file.close()
                                # Important: remove from locals so we don't try to close again
                                del selected_file
                                selected_file = None
                            else:
                                # Save uploaded file
                                final_path = save_uploaded_file_to_disk(selected_file)
                            
                            from database.db_manager import update_case, add_chain_of_custody, add_evidence
                            
                            update_case(case_id, image_path=final_path, image_hash=image_hash)
                            
                            add_evidence(
                                case_id, 
                                "Device Image", 
                                file_name,
                                file_path=final_path,
                                hash_value=image_hash,
                                metadata=metadata
                            )
                            
                            add_chain_of_custody(
                                case_id, 
                                "Evidence Added", 
                                st.session_state.get('investigator', 'Unknown'),
                                f"Added image {file_name} from {'local path' if is_local else 'upload'}"
                            )
                            
                            st.session_state['image_path'] = final_path
                            
                            st.success("✅ Image verified and added to case evidence!")
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"Error processing evidence: {str(e)}")
                            if is_local and selected_file: selected_file.close()
                            return None
            
            # Close local file handle if it wasn't closed in the success block
            if is_local and selected_file: 
                 selected_file.close()

            return {
                'filename': file_name,
                'size': file_size_mb,
                'sha256': sha256_hash,
                'md5': md5_hash,
                'metadata': metadata,
                'file_path': st.session_state.get('image_path', '')
            }
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            if is_local and 'selected_file' in locals() and selected_file: selected_file.close()
            return None
    
    else:
        st.info("Please select an image to begin analysis")
        
    return None

def analyze_image_structure_chunked(uploaded_file):
    """Analyze basic structure of the device image without loading entire file"""
    metadata = {}
    
    try:
        # Get file size
        uploaded_file.seek(0, 2)
        total_bytes = uploaded_file.tell()
        uploaded_file.seek(0)
        
        metadata['Total Size'] = f"{total_bytes:,} bytes"
        metadata['Size (MB)'] = f"{total_bytes / (1024*1024):.2f} MB"
        metadata['Size (GB)'] = f"{total_bytes / (1024*1024*1024):.2f} GB"
        
        # Read only first 4KB for header analysis
        header = uploaded_file.read(4096)
        uploaded_file.seek(0)
        
        # Detect OS
        if b'Android' in header or b'ANDROID' in header:
            metadata['Detected OS'] = 'Android'
        elif b'Apple' in header or b'iOS' in header or b'HFS' in header:
            metadata['Detected OS'] = 'iOS'
        else:
            metadata['Detected OS'] = 'Unknown'
        
        # Detect file system type
        if header.startswith(b'\xEB\x52\x90') or header.startswith(b'\xEB\x76\x90'):
            metadata['File System Type'] = 'FAT32 (Suspected)'
        elif header.startswith(b'\xEB\x58\x90'):
            metadata['File System Type'] = 'exFAT (Suspected)'
        elif b'ext4' in header or b'EXT4' in header:
            metadata['File System Type'] = 'ext4 (Suspected)'
        elif b'ext3' in header or b'EXT3' in header:
            metadata['File System Type'] = 'ext3 (Suspected)'
        else:
            metadata['File System Type'] = 'Unknown / Raw'
        
        metadata['Parseable'] = 'Yes' if total_bytes > 1024 else 'No (too small)'
        
    except Exception as e:
        metadata['Error'] = str(e)
    
    # Encryption Detection
    try:
        uploaded_file.seek(0)
        # Read first 1MB for broader search if needed, but 4KB is usually enough for headers
        # Re-read header to be safe
        header = uploaded_file.read(4096) 
        uploaded_file.seek(0)
        
        encryption_found = []
        
        # LUKS (Magic bytes "LUKS\xba\xbe" at offset 0)
        if header.startswith(b'LUKS\xba\xbe'):
            encryption_found.append("LUKS")
            
        # BitLocker (Look for FVE-FS signature)
        # Usually in the OEM ID field of the boot sector (bytes 3-10) or shortly after
        if b'-FVE-FS-' in header:
            encryption_found.append("BitLocker")
            
        # FileVault (CoreStorage logic is complex, checking for common indicators)
        # This is a basic heuristic
        if b'CS' == header[0:2] and b'CORE' not in header: # Very weak check, refining:
             # CoreStorage Volume Header often starts with 'CS' at block 0? No, usually slightly later.
             # APFS Container might be encryption wrapper.
             pass

        # High Entropy Check (heuristic for VeraCrypt/random)
        # VeraCrypt hides headers, so it looks like random data.
        # Use python-magic if available but here we stick to simple heuristics or signatures.
        
        if encryption_found:
            metadata['Encryption Detected'] = ", ".join(encryption_found)
        else:
             metadata['Encryption Detected'] = "None / Unknown (or hidden)"
             
    except Exception:
        pass
        
    return metadata
