"""
CORTEX - ADB Forensics Engine
Handles direct local acquisition and parsing of Android forensic artifacts via ADB commands
"""

import subprocess
import shutil
import os
import json
import pandas as pd
from datetime import datetime
import tempfile

def check_adb_available():
    """Check if ADB is available in the system PATH"""
    return shutil.which("adb") is not None

def get_connected_devices():
    """Get a list of connected Android devices via ADB"""
    devices = []
    if not check_adb_available():
        return devices
        
    try:
        # Run adb devices -l
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            if line.strip() and "device" in line and not "authorized" in line:
                parts = line.split()
                serial = parts[0]
                model = "Android Device"
                for part in parts:
                    if part.startswith("model:"):
                        model = part.split(":")[1].replace("_", " ")
                devices.append({
                    "serial": serial, 
                    "model": model, 
                    "status": "Ready",
                    "details": line
                })
            elif "unauthorized" in line:
                parts = line.split()
                serial = parts[0]
                devices.append({
                    "serial": serial,
                    "model": "Unauthorized Device",
                    "status": "Unauthorized",
                    "details": "Please accept RSA fingerprint prompt on phone screen"
                })
    except Exception:
        pass
    return devices

def run_adb_shell(serial, command, timeout=10):
    """Run an ADB shell command on a specific device"""
    try:
        cmd = ["adb", "-s", serial, "shell"] + command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def check_device_root(serial):
    """Check if the device has root access available via su"""
    success, output = run_adb_shell(serial, ["su", "-c", "id"])
    if success and "uid=0" in output:
        return True
    return False

def extract_device_properties(serial):
    """Extract system properties from device using getprop"""
    props = {
        "Manufacturer": "ro.product.manufacturer",
        "Model": "ro.product.model",
        "Brand": "ro.product.brand",
        "Android Version": "ro.build.version.release",
        "SDK Level": "ro.build.version.sdk",
        "Security Patch": "ro.build.version.security_patch",
        "Build Fingerprint": "ro.build.fingerprint",
        "CPU Abi": "ro.product.cpu.abi",
        "Bootloader State": "ro.boot.flash.locked",
        "Serial Number": "ro.serialno"
    }
    
    extracted = {}
    for key, prop_name in props.items():
        success, output = run_adb_shell(serial, ["getprop", prop_name])
        if success and output.strip():
            extracted[key] = output.strip()
        else:
            extracted[key] = "Unknown"
            
    # Clean up bootloader state presentation
    if extracted.get("Bootloader State") == "1":
        extracted["Bootloader State"] = "Locked (Secure)"
    elif extracted.get("Bootloader State") == "0":
        extracted["Bootloader State"] = "Unlocked (Vulnerable)"
        
    # Check root access
    extracted["Root Status"] = "Rooted (su accessible)" if check_device_root(serial) else "Non-Rooted"
    extracted["Extraction Timestamp"] = datetime.now().isoformat()
    return extracted

def extract_installed_packages(serial):
    """Extract list of installed packages (third-party and system)"""
    packages = []
    # Get 3rd party packages
    success, output = run_adb_shell(serial, ["pm", "list", "packages", "-f", "-3"])
    if success:
        for line in output.splitlines():
            if line.startswith("package:"):
                # format: package:/data/app/.../base.apk=com.example.app
                parts = line.replace("package:", "").split("=")
                if len(parts) >= 2:
                    apk_path = parts[0]
                    pkg_name = "=".join(parts[1:])
                    packages.append({"Package": pkg_name, "Path": apk_path, "Type": "Third-Party"})
                    
    # Get system packages
    success_sys, output_sys = run_adb_shell(serial, ["pm", "list", "packages", "-f", "-s"])
    if success_sys:
        for line in output_sys.splitlines():
            if line.startswith("package:"):
                parts = line.replace("package:", "").split("=")
                if len(parts) >= 2:
                    apk_path = parts[0]
                    pkg_name = "=".join(parts[1:])
                    packages.append({"Package": pkg_name, "Path": apk_path, "Type": "System"})
                    
    return pd.DataFrame(packages) if packages else pd.DataFrame(columns=["Package", "Path", "Type"])

def extract_running_processes(serial):
    """Extract lists of running processes"""
    processes = []
    success, output = run_adb_shell(serial, ["ps", "-A"])
    if not success or "PID" not in output:
        # Fallback to simple ps
        success, output = run_adb_shell(serial, ["ps"])
        
    if success:
        lines = output.splitlines()
        if len(lines) > 1:
            header = lines[0].split()
            # Find column indices for USER, PID, NAME
            user_idx = 0
            pid_idx = 1
            name_idx = -1
            
            for i, col in enumerate(header):
                if col.upper() == "USER": user_idx = i
                elif col.upper() == "PID": pid_idx = i
                elif col.upper() == "NAME" or col.upper() == "CMD": name_idx = i
                
            for line in lines[1:]:
                parts = line.split()
                if len(parts) > max(user_idx, pid_idx, name_idx):
                    user = parts[user_idx]
                    pid = parts[pid_idx]
                    name = parts[name_idx]
                    processes.append({"PID": pid, "User": user, "Process Name": name})
                    
    return pd.DataFrame(processes) if processes else pd.DataFrame(columns=["PID", "User", "Process Name"])

def extract_logcat(serial, line_count=300):
    """Extract recently recorded system logs"""
    logs = []
    success, output = run_adb_shell(serial, ["logcat", "-d", "-t", str(line_count), "-v", "threadtime"])
    if success:
        for line in output.splitlines():
            if line.strip():
                logs.append({"Log Entry": line.strip()})
    return pd.DataFrame(logs) if logs else pd.DataFrame(columns=["Log Entry"])

def extract_rooted_database(serial, db_type):
    """
    If the device is rooted, copy database from secure path to temp local directory.
    Supported types: 'contacts', 'sms', 'whatsapp'
    """
    db_paths = {
        "contacts": "/data/data/com.android.providers.contacts/databases/contacts2.db",
        "sms": "/data/data/com.android.providers.telephony/databases/mmssms.db",
        "whatsapp": "/data/data/com.whatsapp/databases/msgstore.db"
    }
    
    if db_type not in db_paths:
        return None, "Unsupported database type"
        
    remote_path = db_paths[db_type]
    temp_dir = tempfile.mkdtemp()
    local_db_path = os.path.join(temp_dir, os.path.basename(remote_path))
    
    # Run su -c cp to sdcard, then pull
    temp_sdcard = f"/sdcard/Download/{os.path.basename(remote_path)}"
    
    # 1. Copy database to accessible sdcard folder
    cmd_copy = ["su", "-c", f"cp {remote_path} {temp_sdcard} && chmod 666 {temp_sdcard}"]
    success, err = run_adb_shell(serial, cmd_copy)
    if not success:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"Failed to copy DB on device: {err}"
        
    # 2. Pull from sdcard to local machine
    try:
        pull_cmd = ["adb", "-s", serial, "pull", temp_sdcard, local_db_path]
        pull_res = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=15)
        
        # 3. Clean up sdcard file
        run_adb_shell(serial, ["rm", temp_sdcard])
        
        if pull_res.returncode == 0 and os.path.exists(local_db_path):
            return local_db_path, None
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, f"Failed to pull DB file: {pull_res.stderr}"
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"ADB pull error: {str(e)}"

def run_full_logical_extraction(serial, case_id):
    """
    Perform a complete logical extraction of system properties, packages, 
    processes, and logcat logs. Write everything into a JSON profile file.
    """
    profile = {}
    try:
        profile["device_properties"] = extract_device_properties(serial)
        
        pkgs_df = extract_installed_packages(serial)
        profile["installed_packages"] = pkgs_df.to_dict(orient="records")
        
        proc_df = extract_running_processes(serial)
        profile["running_processes"] = proc_df.to_dict(orient="records")
        
        logs_df = extract_logcat(serial, 500)
        profile["logcat"] = logs_df.to_dict(orient="records")
        
        # Check for root files if available
        profile["databases"] = {}
        if check_device_root(serial):
            for db_name in ["contacts", "sms", "whatsapp"]:
                local_path, err = extract_rooted_database(serial, db_name)
                if local_path and os.path.exists(local_path):
                    # We store the path to the pulled sqlite database
                    profile["databases"][db_name] = local_path
                    
        # Write to JSON file in workspace output folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extract_dir = os.path.join(os.getcwd(), "extracted_evidence", case_id)
        os.makedirs(extract_dir, exist_ok=True)
        
        profile_path = os.path.join(extract_dir, f"android_logical_profile_{timestamp}.json")
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4, default=str)
            
        return profile_path, profile
        
    except Exception as e:
        return None, str(e)
