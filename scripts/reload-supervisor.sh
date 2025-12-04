#!/bin/bash
set -euo pipefail

# Stop failing/unwanted services if they are running (ignore errors)
sudo supervisorctl stop fastapi || true
sudo supervisorctl stop react || true

# Reload configuration and apply changes
sudo supervisorctl reread
sudo supervisorctl update

# Start streamlit service
sudo supervisorctl start streamlit || true

echo "Supervisor configuration reloaded and streamlit start requested."
