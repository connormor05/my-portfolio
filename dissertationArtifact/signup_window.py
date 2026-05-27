# signup_window.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PyQt5.QtCore import Qt
import json
import os
import requests

import auth_client
from auth_client import login, BASE_URL

# Helper: Load all users data Safely
def load_all_users_data():
    data_file = "user_data.json"
    if os.path.exists(data_file):
        try:
            with open(data_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass # File is corrupted, fall through to default
    return {"users": {}, "last_logged_in": None}

# Helper: Save all users data
def save_all_users_data(data):
    try:
        with open("user_data.json", "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save user data: {e}")


class SignupWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Create Account")
        self.setGeometry(300, 300, 400, 350)

        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 20px;
            }
        """)

        card_layout = QVBoxLayout()
        card_layout.setAlignment(Qt.AlignCenter)
        card.setLayout(card_layout)

        title = QLabel("Create Your Account")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        card_layout.addWidget(title)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setFixedHeight(40)
        self.email_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.email_input.returnPressed.connect(self.handle_signup)
        card_layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)
        self.password_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.password_input.returnPressed.connect(self.handle_signup)
        card_layout.addWidget(self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm Password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setFixedHeight(40)
        self.confirm_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.confirm_input.returnPressed.connect(self.handle_signup)
        card_layout.addWidget(self.confirm_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 13px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        card_layout.addWidget(self.error_label)

        self.signup_btn = QPushButton("Sign Up")
        self.signup_btn.setFixedHeight(45)
        self.signup_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: white;
                border-radius: 12px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #274BB5;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
            }
        """)
        self.signup_btn.clicked.connect(self.handle_signup)
        card_layout.addWidget(self.signup_btn)

        back_btn = QPushButton("Already have an account? Log in")
        back_btn.setStyleSheet("background: none; color: #1E3A8A; border: none;")
        back_btn.clicked.connect(self.go_to_login)
        card_layout.addWidget(back_btn)

        root.addWidget(card)
        self.setLayout(root)

    def handle_signup(self):
        email = self.email_input.text().strip().lower()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()

        if not email or not password or not confirm:
            self.error_label.setText("Please fill in all fields.")
            return

        if password != confirm:
            self.error_label.setText("Passwords do not match.")
            return

        self.signup_btn.setEnabled(False)
        self.error_label.setText("")

        # Backend signup request
        try:
            response = requests.post(
                f"{BASE_URL}/signup",
                json={"email": email, "password": password},
                timeout=5
            )
            
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException as e:
            print("Signup network error:", e)
            self.error_label.setText("Could not connect to the server.")
            self.signup_btn.setEnabled(True)
            return
        except ValueError:
            print("Signup parsing error: Server returned non-JSON")
            self.error_label.setText("Unexpected response from server.")
            self.signup_btn.setEnabled(True)
            return

        if "error" in data:
            self.error_label.setText(data["error"])
            self.signup_btn.setEnabled(True)
            return

        # Auto-login
        success = login(email, password)

        if not success or auth_client.AUTH_TOKEN is None:
            self.error_label.setText("Login after signup failed. Try logging in manually.")
            self.signup_btn.setEnabled(True)
            return

        # Save new user in multi-user JSON
        all_users = load_all_users_data()

        if "users" not in all_users or not isinstance(all_users["users"], dict):
            all_users["users"] = {}

        all_users["users"][email] = {
            "last_course": "Programming Fundamentals",
            "current_lesson": 1,
            "auth_token": auth_client.AUTH_TOKEN
        }

        # Update last_logged_in
        all_users["last_logged_in"] = email

        save_all_users_data(all_users)

        # Open homepage
        from homepage import HomepageWindow
        self.home = HomepageWindow(auth_token=auth_client.AUTH_TOKEN, user_email=email)
        self.home.show()
        self.close()

    def go_to_login(self):
        from login_window import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()