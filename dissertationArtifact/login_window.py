# login_window.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PyQt5.QtCore import Qt
import json
import os
import auth_client


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Login")
        self.setGeometry(300, 300, 400, 300)

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

        title = QLabel("Welcome Back")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        card_layout.addWidget(title)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setFixedHeight(40)
        self.email_input.setStyleSheet("padding: 8px; font-size: 14px;")

        # Allow hitting Enter to log in
        self.email_input.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)
        self.password_input.setStyleSheet("padding: 8px; font-size: 14px;")

        # Allow hitting Enter to log in
        self.password_input.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 13px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        card_layout.addWidget(self.error_label)

        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedHeight(45)
        self.login_btn.setStyleSheet("""
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
        self.login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_btn)

        signup_btn = QPushButton("Create an account")
        signup_btn.setStyleSheet("background: none; color: #1E3A8A; border: none;")
        signup_btn.clicked.connect(self.go_to_signup)
        card_layout.addWidget(signup_btn)

        root.addWidget(card)
        self.setLayout(root)

    # Login Handling
    def handle_login(self):
        email = self.email_input.text().strip().lower()
        password = self.password_input.text().strip()

        if not email or not password:
            self.show_error("Please enter both your email and password.")
            return

        self.login_btn.setEnabled(False)
        self.show_error("")  # Clear previous error

        try:
            success = auth_client.login(email, password)
        except Exception as e:
            self.show_error(f"Cannot connect to server. Ensure it is running. ({e})")
            self.login_btn.setEnabled(True)
            return

        if not success:
            self.show_error("Invalid email or password.")
            self.login_btn.setEnabled(True)
            return

        # Save auth token in multi-user format
        self.save_user_token(email, auth_client.AUTH_TOKEN)
        self.open_homepage(email, auth_client.AUTH_TOKEN)

    # Utility Methods
    def show_error(self, message):
        self.error_label.setText(message)

    def save_user_token(self, email, token):
        """Save auth token + mark this user as last_logged_in safely."""
        data_file = "user_data.json"
        
        # Safely load existing data or create default structure
        if os.path.exists(data_file):
            try:
                with open(data_file, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {"users": {}, "last_logged_in": None}
        else:
            data = {"users": {}, "last_logged_in": None}

        # Ensure the structure exists
        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        # Mark the user as the last logged-in user
        data["last_logged_in"] = email

        if email not in data["users"]:
            data["users"][email] = {
                "last_course": "Programming Fundamentals",
                "current_lesson": 1
            }

        # Save the fresh token
        data["users"][email]["auth_token"] = token

        try:
            with open(data_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to write to {data_file}: {e}")

    def open_homepage(self, email, token):
        """Open the Homepage window for this user."""
        from homepage import HomepageWindow
        self.home = HomepageWindow(auth_token=token, user_email=email)
        self.home.show()
        self.close()

    def go_to_signup(self):
        from signup_window import SignupWindow
        self.signup = SignupWindow()
        self.signup.show()
        self.close()