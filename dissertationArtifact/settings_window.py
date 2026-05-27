# settings_window.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QMessageBox
from settings_manager import load_settings, save_settings
from auth_client import BASE_URL
import requests

class SettingsWindow(QDialog):
    def __init__(self, parent=None, user_email=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(300, 200)
        self.resize(350, 250)

        self.user_email = user_email
        print("SettingsWindow opened for:", self.user_email)

        self.settings = load_settings()

        self.sound_checkbox = QCheckBox("Enable sound")
        self.sound_checkbox.setChecked(self.settings.get("sound_enabled", True))
        self.sound_checkbox.stateChanged.connect(self.toggle_sound)

        self.animations_checkbox = QCheckBox("Enable animations")
        self.animations_checkbox.setChecked(self.settings.get("animations_enabled", True))
        self.animations_checkbox.stateChanged.connect(self.toggle_animations)

        self.reset_btn = QPushButton("Reset Progress")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_progress)

        layout = QVBoxLayout()
        layout.setSpacing(15) 
        layout.addWidget(self.sound_checkbox)
        layout.addWidget(self.animations_checkbox)
        layout.addStretch()
        layout.addWidget(self.reset_btn)
        
        self.setLayout(layout)

    def toggle_sound(self, state):
        self.settings["sound_enabled"] = bool(state)
        save_settings(self.settings)

    def toggle_animations(self, state):
        self.settings["animations_enabled"] = bool(state)
        save_settings(self.settings)

    def reset_progress(self):
        from homepage import load_all_users_data, save_all_users_data

        confirm = QMessageBox.question(
            self,
            "Reset Progress",
            "Are you sure you want to reset all progress? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        # Load local JSON
        all_users = load_all_users_data()

        if "users" not in all_users or self.user_email not in all_users["users"]:
            QMessageBox.warning(self, "Error", "User not found locally.")
            return

        user = all_users["users"][self.user_email]
        token = user.get("auth_token")

        if not token:
            QMessageBox.warning(self, "Error", "Authentication token missing. Please log in again.")
            return

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "xp": 0,
            "level": 1,
            "streak": 0,
            "achievements": {},
            "completedLessons": []
        }

        try:
            response = requests.post(
                f"{BASE_URL}/progression/update",
                json=payload,
                headers=headers,
                timeout=10 
            )
            
            if response.status_code != 200:
                QMessageBox.warning(self, "Backend Error", f"Failed to reset on server. Status Code: {response.status_code}")
                return
                
        except requests.exceptions.RequestException as e:
            QMessageBox.warning(self, "Network Error", f"Failed to connect to backend:\n{e}")
            return

        # If backend reset succeeds, reset LOCAL JSON values
        user["xp"] = 0
        user["level"] = 1
        user["xp_to_next_level"] = 50
        user["streak"] = 0
        user["achievements"] = {}
        user["completedLessons"] = []
        user["current_lesson"] = 1

        save_all_users_data(all_users)

        QMessageBox.information(self, "Progress Reset", "Your progress has been reset successfully.")

        # Reload Homepage to fresh backend values
        from homepage import HomepageWindow

        if self.parent():
            self.parent().close()

        self.new_home = HomepageWindow(
            auth_token=token,
            user_email=self.user_email
        )
        self.new_home.show()

        # Close the settings window
        self.close()