import json
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QScrollArea, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt

from auth_client import BASE_URL

class CoursesPage(QWidget):
    def __init__(self, auth_token=None, user_email=None):
        super().__init__()

        self.auth_token = auth_token
        self.user_email = user_email

        self.setWindowTitle("Study Forge – My Courses")
        self.setGeometry(200, 200, 600, 700)

        # Load global stylesheet
        try:
            with open("styles.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print("Stylesheet failed to load:", e)

        # Load courses.json
        try:
            with open("courses.json", "r") as f:
                self.courses = json.load(f)
        except Exception as e:
            print("Failed to load courses.json:", e)
            self.courses = {}

        # Scroll Area Setup
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)

        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Header
        header = QLabel("My Courses")
        header.setAlignment(Qt.AlignCenter)
        header.setObjectName("headerTitle")
        self.layout.addWidget(header)

        # Fetch User Progress
        self.user_progress = self.fetch_user_progress()

        # Course Cards (dynamic)
        for course_name, course_data in self.courses.items():
            
            if course_name == "Programming Fundamentals":
                completed_lessons = self.user_progress.get("completedLessons", [])
                
                # Update lesson completion status is based on backend data
                for lesson in course_data.get("lessons", []):
                    if lesson["id"] in completed_lessons:
                        lesson["completed"] = True
                    else:
                        lesson["completed"] = False
                        
                # Calculate the real progress
                progress = self.calculate_progress(course_data)
            else:
                progress = 0

            # Add the card to the UI
            self.add_course_card(course_name, progress)

        # Back Button
        back_button = QPushButton("Back to Homepage")
        back_button.setObjectName("secondaryButton")
        back_button.clicked.connect(self.go_home)
        self.layout.addWidget(back_button)

    # Method: Calculate Course Progress
    def calculate_progress(self, course_data):
        lessons = course_data.get("lessons", [])
        if not lessons:
            return 0

        completed = sum(1 for l in lessons if l.get("completed", False))
        total = len(lessons)

        return int((completed / total) * 100)

    # Method: Add Course Card
    def add_course_card(self, title, progress_value):
        card_widget = QFrame()
        card_widget.setObjectName("courseCard")
        card_widget.setAutoFillBackground(True)

        card_layout = QVBoxLayout(card_widget)

        # Course title
        title_label = QLabel(title)
        title_label.setObjectName("courseTitle")
        card_layout.addWidget(title_label)

        # Progress text
        progress_label = QLabel(f"{progress_value}% complete")
        progress_label.setObjectName("courseProgressText")
        card_layout.addWidget(progress_label)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setValue(progress_value)
        progress_bar.setObjectName("courseProgressBar")
        card_layout.addWidget(progress_bar)

        # Resume button
        resume_button = QPushButton("Resume")
        resume_button.setObjectName("resumeButton")
        resume_button.clicked.connect(lambda _, c=title: self.open_course(c))
        card_layout.addWidget(resume_button)

        # Add card to page
        self.layout.addWidget(card_widget)

    # Method: Open Course → Next Lesson
    def open_course(self, course_name):
        self.user_progress = self.fetch_user_progress()
        completed_lessons = self.user_progress.get("completedLessons", [])
        
        # Safely get lessons, causing an empty list
        course_data = self.courses.get(course_name, {})
        lessons = course_data.get("lessons", [])

        # Default to first lesson ID if nothing is found
        next_lesson_id = 1 

        if lessons:
            if completed_lessons:
                highest_completed = max(completed_lessons)
                next_lesson_id = highest_completed + 1
            else:
                next_lesson_id = lessons[0]["id"]
            
            max_lesson_id = max(lesson["id"] for lesson in lessons)
            if next_lesson_id > max_lesson_id:
                next_lesson_id = max_lesson_id

        # Open lesson window
        from lesson_window import LessonWindow
        self.lesson_window = LessonWindow(
            course=course_name,
            lesson_id=next_lesson_id,
            auth_token=self.auth_token,
            user_email=self.user_email
        )
        self.lesson_window.show()
        self.close()

    # Method: Back To Homepage
    def go_home(self):
        from homepage import HomepageWindow
        self.homepage = HomepageWindow(
            auth_token=self.auth_token, 
            user_email=self.user_email
        )
        self.homepage.show()
        self.close()

    # Methid: Fetch User Progress
    def fetch_user_progress(self):
        """Fetch user progress from the backend using the auth token."""
        if not self.auth_token:
            print("No auth token; returning empty progress")
            return {"completedLessons": []}

        try:
            response = requests.get(
                f"{BASE_URL}/progression",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=5 
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch progress (Status {response.status_code}):", response.text)
                return {"completedLessons": []}
        except Exception as e:
            print("Error fetching progress:", e)
            return {"completedLessons": []}