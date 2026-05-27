# settings_manager.py
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "sound_enabled": True,
    "animations_enabled": True
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r") as f:
            user_settings = json.load(f)
            
        settings = DEFAULT_SETTINGS.copy()
        if isinstance(user_settings, dict):
            settings.update(user_settings)
            
        return settings
        
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ Warning: Failed to load settings ({e}). Restoring defaults.")
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except OSError as e:
        print(f"❌ Error: Could not save settings to {SETTINGS_FILE}: {e}")