import json
import os
import subprocess
import psutil
import sys
import requests
import shutil

from PyQt5.QtWidgets import QApplication

from homepage import HomepageWindow
from login_window import LoginWindow
from auth_client import BASE_URL, validate_token


def is_server_healthy():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=1)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def ensure_server_running():
    if shutil.which("node") is None:
        raise RuntimeError("Node.js is not installed or not in your system's PATH.")

    if is_server_healthy():
        print("Server is already running and healthy.")
        return

    # Kill existing server if stuck
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'node' in proc.info['name'].lower():
                if proc.info['cmdline'] and 'server.js' in ' '.join(proc.info['cmdline']).lower():
                    print(f"Killing stuck Node process (PID: {proc.info['pid']})...")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    print("Starting Node server...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(base_dir, "src")
    
    node_command = ["node", "server.js"]
    subprocess.Popen(node_command, cwd=server_path)


def load_user_data():
    """Handles loading and initialising the user_data.json file safely."""
    data_file = "user_data.json"
    default_data = {"users": {}, "last_logged_in": None}

    if not os.path.exists(data_file):
        with open(data_file, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data

    try:
        with open(data_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(data_file, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data


if __name__ == "__main__":
    ensure_server_running()

    all_users = load_user_data()

    user_email = None
    saved_token = None

    # Auto-login the last logged-in user if present
    last_logged_in = all_users.get("last_logged_in")
    users = all_users.get("users", {})

    if last_logged_in and last_logged_in in users:
        user = users[last_logged_in]
        saved_token = user.get("auth_token")
        user_email = last_logged_in 

    # Start PyQt
    app_qt = QApplication(sys.argv)

    if saved_token and validate_token(saved_token):
        print(f"Saved token is valid. Auto-logging in as {user_email}.")
        homepage = HomepageWindow(auth_token=saved_token, user_email=user_email)
        homepage.show()
    else:
        print("No valid token found. Showing login window.")
        login_window = LoginWindow()
        login_window.show()

    sys.exit(app_qt.exec_())