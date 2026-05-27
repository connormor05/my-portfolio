# lesson_window.py

# PyQt widgets
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QLineEdit
)

# Core + animations
from PyQt5.QtCore import QPoint, Qt, QTimer, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtCore import QPropertyAnimation

# Networking / API
import requests
import json

# App constants
from auth_client import BASE_URL
from data_utils import load_courses
from homepage import load_all_users_data, save_all_users_data

# Custom classes
from sound_manager import SoundManager


# Backend Worker Thread
class BackendWorker(QThread):
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, payload=None, headers=None, timeout=20, retries=2, method="POST"):
        super().__init__()
        self.url = url
        self.payload = payload
        self.headers = headers or {}
        self.timeout = timeout
        self.retries = retries
        self.method = method.upper()

    def run(self):
        import requests
        attempts = 0
        while attempts < self.retries:
            try:
                if self.method == "POST":
                    response = requests.post(
                        self.url, headers=self.headers, json=self.payload, timeout=self.timeout
                    )
                else:
                    response = requests.get(
                        self.url, headers=self.headers, timeout=self.timeout
                    )
                response.raise_for_status()

                try:
                    data = response.json()
                except Exception:
                    data = {"info": response.text}

                self.result_ready.emit(data)
                return

            except requests.exceptions.Timeout:
                attempts += 1
                if attempts >= self.retries:
                    self.error.emit(f"Request timed out after {self.retries} attempts.")
            except requests.exceptions.RequestException as e:
                self.error.emit(f"Request failed: {str(e)}")
                return


# Level Up Popup
class LevelUpPopup(QFrame):
    def __init__(self, level, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 16px;
                border: 2px solid #10B981;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #065F46;
            }
        """)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(QLabel("🎉 Level Up!"))
        layout.addWidget(QLabel(f"You reached Level {level}!"))
        self.setLayout(layout)
        self.setFixedSize(220, 100)
        self.setWindowOpacity(0)


# Achievement Popup
class AchievementPopup(QFrame):
    def __init__(self, achievement_name, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            QFrame {
                background-color: #FFF8E1;
                border-radius: 16px;
                border: 2px solid #FBBF24;
            }
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #B45309;
            }
        """)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(QLabel("🏅 Achievement Unlocked!"))
        layout.addWidget(QLabel(achievement_name))
        self.setLayout(layout)
        self.setFixedSize(260, 110)
        self.setWindowOpacity(0)


# Lesson Window
class LessonWindow(QWidget):
    def __init__(self, course, lesson_id, auth_token, user_email=None):
        super().__init__()

        self.animations = []
        self.lesson_phase = "info"
        self.current_task = None
        self.last_reply_was_task = False
        self.course = course
        self.lesson_id = lesson_id
        self.auth_token = auth_token
        self.user_email = user_email
        self.suppress_home_redirect = False
        self.next_lesson_from_backend = None

        self.courses = load_courses()
        self.lesson = self.get_lesson_info()
        if not self.lesson:
            raise ValueError(f"Lesson ID {lesson_id} not found in course '{course}'")

        # Reset backend lesson state
        if self.auth_token:
            worker = BackendWorker(
                f"{BASE_URL}/lesson/start",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                method="POST"
            )
            worker.start()

        # Load Real User Data
        all_users = load_all_users_data()

        if "users" not in all_users:
            all_users["users"] = {}

        if self.user_email in all_users["users"]:
            self.user_data = all_users["users"][self.user_email]
        else:
            self.user_data = {
                "xp": 0,
                "level": 1,
                "xp_to_next_level": 50,
                "streak": 0,
                "achievements": {},
                "completedLessons": [],
                "current_lesson": 1,
                "last_course": None,
                "auth_token": self.auth_token
            }
            all_users["users"][self.user_email] = self.user_data
            save_all_users_data(all_users)

        if isinstance(self.user_data.get("achievements"), list):
            self.user_data["achievements"] = {key: True for key in self.user_data["achievements"]}

        # Fetch backend progression
        if self.auth_token:
            prog_worker = BackendWorker(
                f"{BASE_URL}/progression",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                method="GET"
            )
            prog_worker.finished.connect(self.sync_user_data)
            prog_worker.start()

        # Window Setup
        self.setWindowTitle(f"Lesson {self.lesson_id}")
        self.setGeometry(250, 250, 600, 500)

        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # Header Bar
        self.header = QFrame()
        self.header.setStyleSheet("""
            QFrame {
                background-color: #F3F4F6;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)

        self.back_btn = QPushButton("←")
        self.back_btn.setFixedWidth(40)
        self.back_btn.clicked.connect(self.handle_return_home)

        self.title_label = QLabel(f"{self.lesson['title']}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.xp_label = QLabel(f"XP: {self.user_data.get('xp',0)}")
        self.xp_label.setAlignment(Qt.AlignRight)
        self.xp_label.setStyleSheet("font-size: 16px;")

        # Fetch current streak from local data immediately
        current_streak = self.user_data.get('streak', 0)
        self.streak_label = QLabel(f"🔥 {current_streak}‑day streak")
        self.streak_label.setAlignment(Qt.AlignRight)
        
        # Apply orange color if streak > 0, otherwise it is grey
        streak_color = "#FFA500" if current_streak > 0 else "#777"
        self.streak_label.setStyleSheet(f"font-size: 14px; color: {streak_color}; font-weight: bold;")
        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(self.title_label, stretch=1)
        header_layout.addWidget(self.xp_label)
        header_layout.addWidget(self.streak_label)

        self.header.setLayout(header_layout)
        root.addWidget(self.header)

        # XP Bar
        self.xp_bar = QProgressBar()
        self.xp_bar.setMaximum(self.user_data.get("xp_to_next_level", 50))
        self.xp_bar.setValue(self.user_data.get("xp", 0))
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setFixedHeight(10)
        self.xp_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E5E7EB;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 5px;
            }
        """)
        header_layout.addWidget(self.xp_bar)

        # Card Area
        self.card_container = QFrame()
        self.card_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 20px;
            }
        """)
        self.card_layout = QVBoxLayout()
        self.card_layout.setAlignment(Qt.AlignCenter)
        self.card_container.setLayout(self.card_layout)
        root.addWidget(self.card_container, stretch=1)

        # Action Area
        self.action_area = QFrame()
        action_layout = QVBoxLayout()
        action_layout.setAlignment(Qt.AlignCenter)
        self.action_area.setLayout(action_layout)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setFixedHeight(45)
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: white;
                border-radius: 12px;
                font-size: 16px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #274BB5;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
            }
        """)
        self.continue_btn.clicked.connect(self.handle_continue)
        action_layout.addWidget(self.continue_btn)
        root.addWidget(self.action_area)

        self.setLayout(root)

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout:
                self.clear_layout(child_layout)

    # Helper Functions
    def get_lesson_info(self):
        lessons = self.courses.get(self.course, {}).get("lessons", [])
        for lesson in lessons:
            if lesson["id"] == self.lesson_id:
                return lesson
        return None

    def get_next_lesson_id(self):
        lessons = self.courses.get(self.course, {}).get("lessons", [])
        ids = [l["id"] for l in lessons]
        if self.lesson_id not in ids:
            return None
        idx = ids.index(self.lesson_id)
        return ids[idx + 1] if idx + 1 < len(ids) else None

    def set_phase(self, phase):
        print(f"Phase → {phase}")
        self.lesson_phase = phase

    # Final Test Mode
    def load_test_mode(self):
        self.in_test_mode = True
        self.score = 0
        self.current_test_index = 0
        self.test_total = 12

        self.test_layout = self.card_layout
        self.clear_layout(self.test_layout)
        self.continue_btn.hide()
        self.send_to_backend("continue")

    def show_test_question(self):
        while self.test_layout.count():
            item = self.test_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self.current_question
        qtype = q.get("type")

        question_text = q.get("question") or q.get("statement") or "Question:"
        label = QLabel(question_text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 18px; margin-bottom: 12px;")
        self.test_layout.addWidget(label)

        if qtype == "multiple_choice":
            for i, opt in enumerate(q.get("options", [])):
                btn = QPushButton(opt)
                btn.clicked.connect(lambda _, idx=i: self.check_test_answer(idx))
                self.test_layout.addWidget(btn)

        elif qtype == "fill_blank":
            self.input_box = QLineEdit()
            self.test_layout.addWidget(self.input_box)
            submit = QPushButton("Submit")
            submit.clicked.connect(lambda: self.check_test_answer(self.input_box.text()))
            self.test_layout.addWidget(submit)

        elif qtype in ("predict_output", "code_output", "debug_code"):
            code = q.get("code", "")
            code_label = QLabel(f"<pre>{code}</pre>")
            code_label.setTextFormat(Qt.RichText)
            code_label.setStyleSheet("font-size: 16px; margin: 8px 0;")
            self.test_layout.addWidget(code_label)

            for i, opt in enumerate(q.get("options", [])):
                btn = QPushButton(opt)
                btn.clicked.connect(lambda _, idx=i: self.check_test_answer(idx))
                self.test_layout.addWidget(btn)

        elif qtype == "true_false":
            true_btn = QPushButton("True")
            false_btn = QPushButton("False")
            true_btn.clicked.connect(lambda: self.check_test_answer(True))
            false_btn.clicked.connect(lambda: self.check_test_answer(False))
            self.test_layout.addWidget(true_btn)
            self.test_layout.addWidget(false_btn)
        else:
            fallback = QLabel("⚠ Unsupported question type.")
            self.test_layout.addWidget(fallback)

    def check_test_answer(self, user_answer):
        q = self.current_question
        correct = q.get("answer")

        if isinstance(correct, str):
            if str(user_answer).strip().lower() == correct.strip().lower():
                self.score += 1
        elif isinstance(correct, bool):
            if bool(user_answer) == correct:
                self.score += 1
        else:
            if user_answer == correct:
                self.score += 1

        self.current_test_index += 1
        if self.current_test_index >= self.test_total:
            self.finish_test()
        else:
            self.send_to_backend("continue")

    def finish_test(self):
        while self.test_layout.count():
            item = self.test_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        result = QLabel(f"Final Score: {self.score}/{self.test_total}")
        result.setAlignment(Qt.AlignCenter)
        result.setStyleSheet("font-size: 26px; font-weight: bold; margin-top: 20px;")
        self.test_layout.addWidget(result)
        
        # Test mode assumes backend summary logic will handle the rest
        self.send_to_backend("continue")

    # Sync User Data
    def sync_user_data(self, prog=None):
            if prog is None:
                return

            self.user_data["xp"] = prog.get("xp", 0)
            self.user_data["level"] = prog.get("level", 1)
            self.user_data["xp_to_next_level"] = prog.get("xpNeeded", 50)
            self.user_data["streak"] = prog.get("streak", 0)

            self.xp_bar.setMaximum(self.user_data["xp_to_next_level"])
            self.xp_bar.setValue(self.user_data["xp"])
            self.xp_label.setText(f"XP: {self.user_data['xp']}")
            
            # Force the streak label to update with fresh backend data
            self.update_streak_ui(self.user_data["streak"], 0)

    def update_user_progress(self, data):
        """Updates UI based on backend summary data"""
        old_xp = self.user_data.get("xp", 0)

        self.user_data["xp"] = data.get("new_xp_total", old_xp)
        self.user_data["level"] = data.get("level", self.user_data.get("level", 1))        
        self.user_data["xp_to_next_level"] = data.get("xpNeeded", 50)
    
        self.xp_bar.setMaximum(self.user_data["xp_to_next_level"])

        if self.user_data["level"] >= 5 and not self.user_data["achievements"].get("level_5", False):
            self.user_data["achievements"]["level_5"] = True
            self.show_achievement_popup("⭐ Level 5 Reached")

        new_xp = self.user_data["xp"]
        self.animate_xp_gain(old_xp, new_xp)

        if "streak" in data:
            self.update_streak_ui(data["streak"], self.user_data.get("streak", 0))
            self.user_data["streak"] = data["streak"]

        if self.user_data["streak"] >= 3 and not self.user_data["achievements"].get("three_day_streak", False):
            self.user_data["achievements"]["three_day_streak"] = True
            self.show_achievement_popup("🔥 3-Day Streak")

        # Save to local file just for safety
        all_users = load_all_users_data()
        all_users["users"][self.user_email] = self.user_data
        save_all_users_data(all_users)

    # Animations
    def animate_xp_gain(self, old_xp, new_xp):
        step = 1 if new_xp > old_xp else -1
        current = old_xp

        def update():
            nonlocal current
            if (step > 0 and current >= new_xp) or (step < 0 and current <= new_xp):
                self.xp_bar.setValue(new_xp)
                self.xp_label.setText(f"XP: {new_xp}")
                timer.stop()
                self.flash_xp_bar()
                gained = new_xp - old_xp
                if gained > 0:
                    self.show_xp_float(gained)
                return

            current += step
            if (step > 0 and current > new_xp) or (step < 0 and current < new_xp):
                current = new_xp

            self.xp_bar.setValue(current)
            self.xp_label.setText(f"XP: {current}")

        timer = QTimer(self)
        timer.timeout.connect(update)
        timer.start(10)

    def flash_xp_bar(self):
        self.xp_bar.setStyleSheet("""
            QProgressBar { background-color: #E5E7EB; border-radius: 5px; }
            QProgressBar::chunk { background-color: #34D399; border-radius: 5px; }
        """)
        QTimer.singleShot(300, lambda: self.xp_bar.setStyleSheet("""
            QProgressBar { background-color: #E5E7EB; border-radius: 5px; }
            QProgressBar::chunk { background-color: #10B981; border-radius: 5px; }
        """))

    def show_xp_float(self, amount):
        label = QLabel(f"+{amount} XP", self)
        label.setStyleSheet("""
            QLabel { color: #10B981; font-size: 18px; font-weight: bold; }
        """)
        label.move(self.width() - 120, 40)
        label.show()
        anim = QPropertyAnimation(label, b"pos")
        anim.setDuration(800)
        anim.setStartValue(label.pos())
        anim.setEndValue(label.pos() - QPoint(0, 40))
        anim.finished.connect(label.deleteLater)
        anim.start()
    
    def animate_bounce(self, widget):
        try:
            from settings_manager import load_settings
            settings = load_settings()
            if not settings.get("animations_enabled", True): return
        except: pass

        start_pos = widget.pos()
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(300)
        anim.setStartValue(start_pos)
        anim.setKeyValueAt(0.5, QPoint(start_pos.x(), start_pos.y() - 15))
        anim.setEndValue(start_pos)
        anim.setEasingCurve(QEasingCurve.OutBounce)
        anim.start()
        self.animations.append(anim)

    def animate_shake(self, widget):
        try:
            from settings_manager import load_settings
            settings = load_settings()
            if not settings.get("animations_enabled", True): return
        except: pass

        start_pos = widget.pos()
        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(300)
        anim.setStartValue(start_pos)
        anim.setEndValue(start_pos)
        anim.setKeyValueAt(0.1, QPoint(start_pos.x() - 10, start_pos.y()))
        anim.setKeyValueAt(0.2, QPoint(start_pos.x() + 10, start_pos.y()))
        anim.setKeyValueAt(0.3, QPoint(start_pos.x() - 10, start_pos.y()))
        anim.setKeyValueAt(0.4, QPoint(start_pos.x() + 10, start_pos.y()))
        anim.setKeyValueAt(0.5, start_pos)
        anim.start()
        self.animations.append(anim)

    # Fade In/Out
    def fade_in_widget(self, widget, duration=200, on_finished=None):
        widget.setWindowOpacity(0)
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(1)
        if on_finished:
            anim.finished.connect(on_finished)
        anim.start()
        self.animations.append(anim)

    def fade_out_widget(self, widget, duration=200, on_finished=None):
        if not widget:
            if on_finished: on_finished()
            return
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(1)
        anim.setEndValue(0)
        if on_finished:
            anim.finished.connect(on_finished)
        anim.start()
        self.animations.append(anim)

    def fade_in(self, widget, duration=300):
        widget.setWindowOpacity(0)
        widget.show()
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.start()
        widget._animation = animation

    # Update Streak UI
    def update_streak_ui(self, streak, old_streak):
        if streak <= 0:
            self.streak_label.setText("🔥 0‑day streak")
            self.streak_label.setStyleSheet("font-size: 14px; color: #777; font-weight: bold;")
            return

        self.streak_label.setText(f"🔥 {streak}‑day streak")
        self.streak_label.setStyleSheet("font-size: 14px; color: #FFA500; font-weight: bold;")
        if streak > old_streak:
            anim = QPropertyAnimation(self.streak_label, b"windowOpacity")
            anim.setDuration(600)
            anim.setStartValue(0.2)
            anim.setEndValue(1.0)
            anim.start()
            self.animations.append(anim)

    # Card Rendering
    def clear_card(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_info_card(self, text):
        self.clear_card()
        try:
            from cards.info_card import InfoCard
            card = InfoCard(text)
            self.card_layout.addWidget(card)
            self.fade_in_widget(card)
            self.continue_btn.show()
        except ImportError:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            self.card_layout.addWidget(lbl)
            self.continue_btn.show()

    def show_task_card(self, task):
        self.set_phase("task")
        self.clear_card()
        try:
            from cards.task_card import TaskCard
            card = TaskCard(task, self.handle_task_answer)
            self.current_task_card = card
            self.card_layout.addWidget(card)
            self.fade_in_widget(card)
            self.continue_btn.hide()
        except ImportError:
            self.show_info_card(f"Task data: {task}")

    def show_info_detail_card(self, info):
        self.set_phase("info_detail")
        def load_info():
            self.clear_card()
            try:
                from cards.info_card import InfoCard
                card = InfoCard(info)
                self.current_task_card = card
                self.card_layout.addWidget(card)
                self.fade_in_widget(card)
                self.continue_btn.show()
            except ImportError:
                lbl = QLabel(info)
                lbl.setWordWrap(True)
                self.card_layout.addWidget(lbl)
                self.continue_btn.show()

        self.fade_out_widget(getattr(self, "current_task_card", None), on_finished=load_info)

    def show_feedback_card(self, correct, message):
        self.set_phase("feedback")
        self.clear_card()

        if getattr(self, "in_test_mode", False):
            callback = self.handle_test_feedback_continue
        else:
            callback = self.handle_feedback_continue

        try:
            from cards.feedback_card import FeedbackCard
            card = FeedbackCard(correct, message, callback)
            self.card_layout.addWidget(card)
            self.fade_in(card)
            self.continue_btn.hide()

            if correct:
                self.animate_bounce(card)
            else:
                self.animate_shake(card)
        except ImportError:
            self.show_info_card(f"Feedback: {message}")

    def handle_test_feedback_continue(self):
        self.send_to_backend("continue")

    def show_summary_card(self, xp_gained, achievements):
        self.set_phase("summary")
        self.clear_card()
        try:
            from cards.summary_card import SummaryCard
            card = SummaryCard(
                xp_gained,
                achievements,
                self.handle_next_lesson,
                self.handle_return_home
            )
            self.card_layout.addWidget(card)
            self.fade_in(card)
            self.continue_btn.hide()
        except ImportError:
            self.show_info_card(f"Summary: Gained {xp_gained} XP!")

    def show_loading_card(self, text="Thinking..."):
        self.clear_card()
        try:
            from cards.loading_card import LoadingCard
            card = LoadingCard(text)
            self.card_layout.addWidget(card)
            self.fade_in(card)
        except ImportError:
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)

    def show_ask_card(self, text):
        self.set_phase("ask")
        self.clear_card()
        try:
            from cards.ask_card import AskCard
            card = AskCard(
                text,
                self.handle_user_question,
                self.handle_skip_question
            )
            self.card_layout.addWidget(card)
            self.fade_in(card)
            self.continue_btn.hide()
        except ImportError:
            self.show_info_card(text)

    def show_achievement_popup(self, achievement_name):
        popup = AchievementPopup(achievement_name, parent=self)
        try:
            xp_y = self.xp_bar.y() + self.xp_bar.height() + 10
        except:
            xp_y = 80

        popup_x = self.width()//2 - popup.width()//2
        popup.move(popup_x, xp_y)
        popup.show()

        if not hasattr(self, "_achievement_anims"):
            self._achievement_anims = []

        fade_in = QPropertyAnimation(popup, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)

        hold = QTimer(self)
        hold.setSingleShot(True)

        fade_out = QPropertyAnimation(popup, b"windowOpacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)

        def start_fade_out(): fade_out.start()
        def delete_popup(): popup.deleteLater()

        fade_in.finished.connect(lambda: hold.start(1400))
        hold.timeout.connect(start_fade_out)
        fade_out.finished.connect(delete_popup)

        fade_in.start()

        self._achievement_anims.extend([fade_in, fade_out, hold])
        try: SoundManager.play("achievement.wav")
        except: pass

    def show_level_up_popup(self, new_level):
        try:
            from settings_manager import load_settings
            settings = load_settings()
            if not settings.get("animations_enabled", True):
                return
        except: pass

        popup = LevelUpPopup(new_level, parent=self)
        popup.move(self.width()//2 - popup.width()//2, 80)
        popup.show()

        fade_in = QPropertyAnimation(popup, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)

        hold = QTimer(self)
        hold.setSingleShot(True)

        fade_out = QPropertyAnimation(popup, b"windowOpacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)

        def start_fade_out(): fade_out.start()
        def delete_popup(): popup.deleteLater()

        fade_in.finished.connect(lambda: hold.start(1200))
        hold.timeout.connect(start_fade_out)
        fade_out.finished.connect(delete_popup)
        fade_in.start()

        try: SoundManager.play_level_up()
        except: pass

    # Backend Communication
    def send_to_backend(self, message=None, task_answer=None):
        if not getattr(self, "in_test_mode", False):
            if hasattr(self, "continue_btn") and self.continue_btn is not None:
                self.continue_btn.setEnabled(False)

        payload = {
            "course": self.course,
            "lesson": self.lesson_id,
            "level": self.user_data.get("level", 1)
        }

        if message is not None:
            payload["message"] = message

        # Achievement Check
        user_achievements = self.user_data.get("achievements", {})
        if not isinstance(user_achievements, dict):
            user_achievements = {}

        if (message and message not in ["continue", "no"] 
            and not user_achievements.get("first_message", False)):
            self.user_data.setdefault("achievements", {})["first_message"] = True
            self.show_achievement_popup("🏅 First Message")

        if task_answer is not None:
            payload["task_answer"] = task_answer

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        print("🔥 Sending to backend:", payload)

        try:
            if hasattr(self, "backend_worker") and self.backend_worker is not None:
                if self.backend_worker.isRunning():
                    self.backend_worker.quit()
                    self.backend_worker.wait()
        except Exception as e:
            print("⚠ Worker cleanup error:", e)

        worker = BackendWorker(f"{BASE_URL}/chat", payload, headers, timeout=20, retries=2)
        self.backend_worker = worker

        worker.result_ready.connect(self.handle_backend_reply)
        worker.error.connect(lambda e: self.show_info_card(f"⚠️ Backend error: {e}"))

        if not getattr(self, "in_test_mode", False):
            worker.finished.connect(lambda: self.continue_btn.setEnabled(True) if hasattr(self, 'continue_btn') and self.continue_btn else None)
            worker.error.connect(lambda _: self.continue_btn.setEnabled(True) if hasattr(self, 'continue_btn') and self.continue_btn else None)

        worker.start()

    def handle_backend_reply(self, data):
        print("🔥 RAW DATA RECEIVED BY HANDLER:", data)

        if isinstance(data, dict) and "newlyUnlocked" in data:
            for ach in data["newlyUnlocked"]:
                pretty = ach.replace("_", " ").title()
                self.show_achievement_popup(pretty)

        if getattr(self, "in_test_mode", False):
            if "task" in data and isinstance(data["task"], dict):
                self.current_question = data["task"]
                self.show_test_question()
                return
            task_types = ["fill_blank", "multiple_choice", "true_false", "predict_output", "debug_code"]
            if data.get("type") in task_types:
                self.current_question = data
                self.show_test_question()
                return
            if "feedback" in data:
                fb = data["feedback"]
                if fb.get("correct", False):
                    try: SoundManager.get().play_correct()
                    except: pass
                else:
                    try: SoundManager.get().play_wrong()
                    except: pass
                self.show_feedback_card(fb.get("correct", False), fb.get("message", ""))
                self.current_test_index += 1
                if self.current_test_index >= self.test_total:
                    self.finish_test()
                return
            if "info" in data: return

        if not isinstance(data, dict):
            self.show_info_card("⚠ Unexpected server response format.")
            return

        if "error" in data:
            print("❌ Backend error:", data["error"])
            self.show_info_card(f"⚠ Server error: {data['error']}")
            return

        if "info" in data:
            text = data["info"]
            lower = text.lower()
            if "would you like to ask" in lower:
                self.set_phase("ask")
                self.clear_card()
                self.show_ask_card(text)
                return
            if any(phrase in lower for phrase in ["final test", "start test", "ready for your test", "begin your test"]):
                self.pending_test = True
                self.set_phase("info_detail")
                self.show_info_card(text)
                return
            if "welcome" in lower:
                self.set_phase("info")
                self.show_info_card(text)
                return
            self.set_phase("info_detail")
            self.show_info_card(text)
            return
        
        if "task" in data and isinstance(data["task"], dict):
            self.show_task_card(data["task"])
            return

        task_types = ["fill_blank", "multiple_choice", "true_false", "predict_output", "debug_code"]
        if data.get("type") in task_types:
            self.show_task_card(data)
            return

        if "feedback" in data:
            fb = data["feedback"]
            if fb.get("correct", False):
                try: SoundManager.get().play_correct()
                except: pass
            else:
                try: SoundManager.get().play_wrong()
                except: pass
            self.show_feedback_card(fb.get("correct", False), fb.get("message", ""))
            return

        if "summary" in data:
            s = data["summary"]
            try:
                self.next_lesson_from_backend = s.get("next_lesson")

                new_ach = s.get("achievements", {})
                if isinstance(new_ach, list):
                    new_ach = {k: True for k in new_ach}
                elif not isinstance(new_ach, dict):
                    new_ach = {}

                self.user_data.setdefault("achievements", {}).update(new_ach)
                self.update_user_progress(s)

                xp_gained = s.get("xp", 0)
                achievements = data.get("newlyUnlocked", [])
                pretty_achievements = [ach.replace("_", " ").title() for ach in achievements]

                self.show_summary_card(xp_gained, pretty_achievements)

                try:
                    from cards.confetti import Confetti
                    confetti = Confetti(self)
                    confetti.show()
                    SoundManager.play_confetti()
                except: pass

            except Exception as e:
                print("Error processing summary:", e)
            return

        print("⚠ Unknown backend reply:", data)
        self.show_info_card("⚠ Unexpected server response.")

    # Card Callbacks
    def handle_task_answer(self, answer):
        print("Task answer submitted:", answer)
        self.send_to_backend(task_answer=answer)

    def handle_feedback_continue(self):
        print("Feedback continue pressed")
        self.send_to_backend(message="continue")

    def handle_user_question(self, question):
        print("User asked:", question)
        self.send_to_backend(message=question)

    def handle_skip_question(self):
        print("User skipped question")
        self.send_to_backend(message="skip")

    def handle_continue(self):
        # 1. Disable the button to prevent spam
        if hasattr(self, 'continue_btn') and self.continue_btn:
            self.continue_btn.setEnabled(False)

        # 2. Fire the network request Once
        self.send_to_backend("continue")

        # 3. Safety re-enable after 1.5s
        QTimer.singleShot(1500, lambda: self.continue_btn.setEnabled(True) if hasattr(self, 'continue_btn') and self.continue_btn else None)

    def handle_next_lesson(self):
        print("Next lesson pressed")
        next_id = getattr(self, "next_lesson_from_backend", None) or self.get_next_lesson_id()
        
        if not next_id:
            print("No more lessons in this course.")
            self.handle_return_home()
            return

        all_users = load_all_users_data()
        if "users" not in all_users:
            all_users["users"] = {}
        if self.user_email not in all_users["users"]:
            all_users["users"][self.user_email] = self.user_data

        all_users["users"][self.user_email]["current_lesson"] = next_id
        save_all_users_data(all_users)

        self.suppress_home_redirect = True
        
        import sys, os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        try:
            from lesson_window import LessonWindow
            self.next_window = LessonWindow(
                self.course,
                next_id,
                self.auth_token,
                user_email=self.user_email
            )
            self.next_window.show()
            self.close()
        except ImportError as e:
            print("Failed to load next lesson:", e)
            self.handle_return_home()

    def handle_return_home(self):
        print("Return home pressed")

        all_users = load_all_users_data()
        if "users" not in all_users:
            all_users["users"] = {}
        if self.user_email not in all_users["users"]:
            all_users["users"][self.user_email] = self.user_data

        all_users["users"][self.user_email]["current_lesson"] = self.lesson_id
        save_all_users_data(all_users)

        from homepage import HomepageWindow
        self.homepage = HomepageWindow(
            auth_token=self.auth_token,
            user_email=self.user_email
        )
        self.homepage.show()
        self.close()

    # Window Close
    def closeEvent(self, event):
        event.accept()
