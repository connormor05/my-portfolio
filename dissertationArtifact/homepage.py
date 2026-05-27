# homepage.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt
from courses_page import CoursesPage
from cards.achievements_page import AchievementsPage
from settings_window import SettingsWindow
import json
import os
import requests
import sys

from auth_client import (
    BASE_URL,
    load_saved_token,
    validate_token,
    AUTH_TOKEN
)

from data_utils import load_courses

# -------------------------
# Helper: Load all users data
# -------------------------
def load_all_users_data():
    try:
        with open("user_data.json", "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "last_logged_in": None}

# -------------------------
# Helper: Save all users data
# -------------------------
def save_all_users_data(data):
    with open("user_data.json", "w") as f:
        json.dump(data, f, indent=4)


class HomepageWindow(QWidget):
    def __init__(self, auth_token=None, user_email=None):
        super().__init__()

        # Resolve token first
        token = auth_token or load_saved_token()

        # If email missing, try recover it from saved user data
        if not user_email:
            all_users = load_all_users_data()
            users = all_users.get("users", {})

            for email, data in users.items():
                if data.get("auth_token") == token:
                    user_email = email
                    break

        if not token or not validate_token(token) or not user_email:
            print("Token missing or invalid — redirecting to login.")
            from login_window import LoginWindow
            self.login = LoginWindow()
            self.login.show()
            self.close()
            return

        self.auth_token = token
        self.user_email = user_email

        # -------------------------
        # Load Local User State (Just for auth and last course tracking)
        # -------------------------
        all_users = load_all_users_data()

        if "users" not in all_users:
            all_users["users"] = {}

        if user_email not in all_users["users"]:
            all_users["users"][user_email] = {
                "last_course": "Programming Fundamentals",
                "auth_token": token
            }

        self.user_data = all_users["users"][user_email]
        self.last_course = self.user_data.get("last_course", "Programming Fundamentals")

        # Set default progression values in case the backend fails
        self.progression = {
            "xp": 0,
            "level": 1,
            "xpNeeded": 50,
            "streak": 0,
            "achievements": {},
            "completedLessons": []
        }

        # -------------------------
        # Fetch True Progression from Backend
        # -------------------------
        try:
            response = requests.get(
                f"{BASE_URL}/progression",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=5
            )

            if response.status_code == 200:
                self.progression = response.json()
                
                # Ensure achievements is always a dictionary
                if isinstance(self.progression.get("achievements"), list):
                     self.progression["achievements"] = {key: True for key in self.progression["achievements"]}
                elif not isinstance(self.progression.get("achievements"), dict):
                     self.progression["achievements"] = {}
            else:
                print("Backend returned non-200 status for progression.")

        except Exception as e:
            print("Could not sync homepage progression:", e)

        # -------------------------
        # Window setup
        # -------------------------
        self.setWindowTitle("Study Forge – Home")
        self.setGeometry(200, 200, 600, 700)

        try:
            with open("styles.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print("Stylesheet failed to load:", e)

        # -------------------------
        # Load courses.json
        # -------------------------
        self.courses = load_courses()

        # -------------------------
        # SCROLL AREA
        # -------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)

        # -------------------------
        # TOP BAR (Logout Left, Settings Right)
        # -------------------------
        top_bar = QHBoxLayout()

        logout_button = QPushButton("Logout")
        logout_button.setObjectName("logoutButton")  # Tells CSS exactly who this is
        logout_button.clicked.connect(self.logout_user)
        top_bar.addWidget(logout_button, alignment=Qt.AlignLeft)

        top_bar.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("settingsButton") # Tells CSS exactly who this is
        settings_btn.clicked.connect(self.open_settings)
        top_bar.addWidget(settings_btn, alignment=Qt.AlignRight)

        self.layout.addLayout(top_bar)
        # -------------------------
        # FINISH SCROLL SETUP
        # -------------------------
        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Header
        header_layout = QVBoxLayout()

        title_label = QLabel("Study Forge")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("headerTitle")

        subtitle_label = QLabel("Level up your skills one lesson at a time")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setObjectName("headerSubtitle")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        self.layout.addLayout(header_layout)

        # Daily Motivation
        motivation_label = QLabel("You're doing great — keep your streak alive!")
        motivation_label.setAlignment(Qt.AlignCenter)
        motivation_label.setObjectName("motivationText")
        self.layout.addWidget(motivation_label)

        streak_label = QLabel(f"🔥 Current Streak: {self.progression.get('streak', 0)} days")
        streak_label.setAlignment(Qt.AlignCenter)
        streak_label.setObjectName("xpSubLabel")
        self.layout.addWidget(streak_label)

        # XP Progress
        xp = self.progression.get("xp", 0)
        level = self.progression.get("level", 1)
        xp_to_next = self.progression.get("xpNeeded", 50)
        
        # Calculate remaining XP, ensuring it doesn't go negative
        xp_remaining = max(0, xp_to_next - xp)

        xp_label = QLabel(f"Level {level} — {xp} / {xp_to_next} XP")
        xp_label.setAlignment(Qt.AlignCenter)
        xp_label.setObjectName("xpLabel")
        self.layout.addWidget(xp_label)

        xp_progress_label = QLabel(f"{xp_remaining} XP to Level {level + 1}")
        xp_progress_label.setAlignment(Qt.AlignCenter)
        xp_progress_label.setObjectName("xpSubLabel")
        self.layout.addWidget(xp_progress_label)

        # Continue Lesson Button
        next_lesson_id = self.get_next_lesson()
        
        lesson_title = "Start Course"
        if next_lesson_id > 1:
            try:
                course_key = self.last_course or list(self.courses.keys())[0]
                lesson = next((l for l in self.courses[course_key]["lessons"] if l["id"] == next_lesson_id), None)
                if lesson:
                     lesson_title = f"Continue: {lesson['title']}"
                else:
                     lesson_title = "Continue"
            except Exception:
                lesson_title = "Continue"

        self.continue_button = QPushButton(lesson_title)
        self.continue_button.setFixedHeight(40)
        self.continue_button.setObjectName("primaryButton")
        self.continue_button.clicked.connect(self.continue_learning)
        self.layout.addWidget(self.continue_button)

        # View Courses Button
        courses_button = QPushButton("View My Courses")
        courses_button.clicked.connect(self.open_courses_page)
        courses_button.setFixedHeight(40)
        courses_button.setObjectName("secondaryButton")
        self.layout.addWidget(courses_button)

        # View Achievements Button
        achievements_button = QPushButton("View Achievements")
        achievements_button.clicked.connect(self.open_achievements_page)
        achievements_button.setFixedHeight(40)
        achievements_button.setObjectName("primaryButton")
        self.layout.addWidget(achievements_button)

        # Dashboard Achievements Preview
        achievements_card = QFrame()
        achievements_card.setObjectName("dashboardCard")
        achievements_layout = QVBoxLayout()
        achievements_card.setLayout(achievements_layout)

        title = QLabel("Achievements")
        title.setObjectName("sectionTitle")
        achievements_layout.addWidget(title)

        achievements_dict = self.progression.get("achievements", {})
        unlocked = [name for name, value in achievements_dict.items() if value]
        recent = unlocked[-3:]

        if not recent:
            empty_label = QLabel("No achievements unlocked yet.")
            empty_label.setObjectName("achievementItem")
            achievements_layout.addWidget(empty_label)
        else:
            for name in recent:
                label = QLabel(f"• {name.replace('_', ' ').title()}")
                label.setObjectName("achievementItem")
                achievements_layout.addWidget(label)

        self.layout.addWidget(achievements_card)

    # Method: Find Next Lesson
    def get_next_lesson(self):
        """Calculates the next lesson based on the backend's completedLessons list."""
        course_key = self.last_course or "Programming Fundamentals"
        if course_key not in self.courses:
            return 1
            
        completed_lessons = self.progression.get("completedLessons", [])
        lessons = self.courses.get(course_key, {}).get("lessons", [])
        
        if not lessons:
            return 1
            
        if not completed_lessons:
            return lessons[0]["id"]
            
        highest_completed = max(completed_lessons)
        next_lesson_id = highest_completed + 1
        
        # Ensure it doesnt go past the final lesson
        max_lesson_id = max(lesson["id"] for lesson in lessons)
        if next_lesson_id > max_lesson_id:
            next_lesson_id = max_lesson_id
            
        return next_lesson_id

    def continue_learning(self):
        next_lesson_id = self.get_next_lesson()
        course_key = self.last_course or "Programming Fundamentals"

        # Update last_course in local file
        all_users = load_all_users_data()
        if "users" in all_users and self.user_email in all_users["users"]:
             all_users["users"][self.user_email]["last_course"] = course_key
             save_all_users_data(all_users)

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        try:
            from lesson_window import LessonWindow
        except ImportError as e:
            print("Cannot import LessonWindow:", e)
            return

        self.lesson_window = LessonWindow(
            course=course_key,
            lesson_id=next_lesson_id,
            auth_token=self.auth_token,
            user_email=self.user_email
        )
        self.lesson_window.show()
        self.close()

    def open_courses_page(self):
        self.courses_page = CoursesPage(auth_token=self.auth_token, user_email=self.user_email)
        self.courses_page.show()
        self.close()

    def open_achievements_page(self):
        self.achievements_window = AchievementsPage(self.progression)
        self.achievements_window.show()

    def open_settings(self):
        dlg = SettingsWindow(parent=self, user_email=self.user_email)
        dlg.exec_()

    def logout_user(self):
        # Clear last_logged_in so auto-login stops
        if os.path.exists("user_data.json"):
            with open("user_data.json", "r") as f:
                data = json.load(f)

            data["last_logged_in"] = None

            with open("user_data.json", "w") as f:
                json.dump(data, f, indent=4)

        # Clear in-memory session
        self.user_data = None
        self.auth_token = None

        # Go back to login window
        self.close()
        from login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()