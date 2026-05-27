# auth_client.py

import requests
import json
import os

BASE_URL = "http://localhost:3000"
AUTH_TOKEN = None
USER_DATA_FILE = "user_data.json"


def load_saved_token():
    global AUTH_TOKEN

    if not os.path.exists(USER_DATA_FILE):
        return None

    try:
        with open(USER_DATA_FILE, "r") as f:
            data = json.load(f)

            last_user = data.get("last_logged_in")
            if last_user and "users" in data:
                user_entry = data["users"].get(last_user)
                if user_entry:
                    token = user_entry.get("auth_token")
                    if token:
                        AUTH_TOKEN = token
                        return token

    except Exception as e:
        print("Error loading saved token:", e)

    return None


def save_token(email, token):
    global AUTH_TOKEN
    AUTH_TOKEN = token

    # Load existing multi-user data
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}
    else:
        data = {}

    if "users" not in data:
        data["users"] = {}

    # Ensure user entry exists
    if email not in data["users"]:
        data["users"][email] = {
            "last_course": None,
            "current_lesson": 1,
            "xp": 0,
            "level": 1,
            "xp_to_next_level": 50,
            "streak": 0,
            "achievements": {},
        }

    # Update token
    data["users"][email]["auth_token"] = token

    # Update last_logged_in
    data["last_logged_in"] = email

    # Save back to file
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def login(email, password):
    global AUTH_TOKEN

    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={"email": email, "password": password},
            timeout=2
        )
    except Exception as e:
        print("Login request failed:", e)
        return False

    try:
        data = response.json()
    except:
        print("Invalid JSON response from server.")
        return False

    token = data.get("token")
    if token:
        save_token(email, token)
        print("TOKEN SET:", AUTH_TOKEN)
        return True

    print("Login failed:", data)
    return False


def validate_token(token):
    try:
        r = requests.get(
            f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=1
        )
        return r.status_code == 200
    except:
        return False