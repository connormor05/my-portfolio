# achievements_page.py
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy
from PyQt5.QtCore import Qt

class AchievementsPage(QWidget):
    def __init__(self, user_data):
        super().__init__()

        self.user_data = user_data
        self.setWindowTitle("Achievements")
        self.resize(400, 600)

        # -------------------------
        # Load global stylesheet
        # -------------------------
        try:
            # We have to step up one directory because this file is in the /cards folder
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            style_path = os.path.join(base_dir, "styles.qss")
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print("Stylesheet failed to load in AchievementsPage:", e)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Title
        title = QLabel("Achievements")
        title.setObjectName("sectionTitle")
        main_layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setSpacing(6)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container.setLayout(container_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Populate achievements safely
        achievements = self.user_data.get("achievements", {})
        
        # Defensive programming: If the backend sent a list by mistake, convert it
        if isinstance(achievements, list):
             achievements = {key: True for key in achievements}

        # Check if there are any actually unlocked achievements
        has_unlocked = any(unlocked for unlocked in achievements.values())

        if has_unlocked:
            for key, unlocked in achievements.items():
                if unlocked:
                    card = QFrame()
                    # We reuse the dashboardCard style so they look consistent
                    card.setObjectName("dashboardCard") 
                    card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

                    card_layout = QVBoxLayout()
                    card_layout.setSpacing(2)
                    card_layout.setContentsMargins(8, 8, 8, 8)
                    card.setLayout(card_layout)

                    label = QLabel(self.get_achievement_text(key))
                    label.setObjectName(self.get_achievement_style(key))
                    card_layout.addWidget(label)

                    container_layout.addWidget(card)

            container_layout.addStretch()

        else:
            empty_label = QLabel("No achievements unlocked yet.")
            # FIX: Use achievementItem to match the CSS file
            empty_label.setObjectName("achievementItem") 
            container_layout.addWidget(empty_label)
            container_layout.addStretch()

    # ---------------------------------------------------------
    # UPDATED ACHIEVEMENT TEXT MAPPING (SAFE + EXPANDED)
    # ---------------------------------------------------------
    def get_achievement_text(self, achievement_key):
        mapping = {
            # Engagement
            "first_message": "💬 First Message Sent",
            "five_messages_sent": "💬 Sent 5 Messages",
            "ten_messages_sent": "💬 Sent 10 Messages",

            # Lesson Progression
            "first_lesson_completed": "🎉 First Lesson Completed",
            "three_lessons_completed": "📘 Completed 3 Lessons",
            "five_lessons_completed": "📗 Completed 5 Lessons",
            "ten_lessons_completed": "📚 Completed 10 Lessons",

            # Course Completion
            "programming_course_complete": "💻 Programming Fundamentals Completed",
            "cyber_course_complete": "🔐 Cybersecurity Basics Completed",
            "software_course_complete": "🏗 Software Engineering Principles Completed",
            "all_courses_complete": "🏆 Completed All Courses",

            # Levels
            "level_2": "⭐ Level 2 Reached",
            "level_3": "⭐ Level 3 Reached",
            "level_4": "⭐ Level 4 Reached",
            "level_5": "⭐ Level 5 Reached",
            "level_6": "⭐ Level 6 Reached",
            "level_7": "⭐ Level 7 Reached",
            "level_8": "⭐ Level 8 Reached",
            "level_9": "⭐ Level 9 Reached",
            "level_10": "🌟 Level 10 Master",

            # Streaks
            "two_day_streak": "🔥 2-Day Streak",
            "three_day_streak": "🔥 3-Day Streak",
            "five_day_streak": "🔥🔥 5-Day Streak",
            "seven_day_streak": "📅 7-Day Streak",
        }

        # Fallback: if key isn't in mapping, make it look nice anyway
        return mapping.get(achievement_key, achievement_key.replace('_', ' ').title())

    # ---------------------------------------------------------
    # STYLING
    # ---------------------------------------------------------
    def get_achievement_style(self, achievement_key):
        rare = [
            "level_5", "level_10", "all_courses_complete",
            "five_day_streak", "seven_day_streak"
        ]
        epic = ["ten_lessons_completed"]

        if achievement_key in epic:
            return "achievementEpic"
        elif achievement_key in rare:
            return "achievementRare"
        else:
            # FIX: Changed from achievementLabel to achievementItem to match CSS
            return "achievementItem"