# sound_manager.py
import os
from settings_manager import load_settings
from PyQt5.QtMultimedia import QSound

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

class SoundManager:
    _instance = None

    @staticmethod
    def get():
        if SoundManager._instance is None:
            SoundManager._instance = SoundManager()
        return SoundManager._instance

    def __init__(self):
        # Pre-load the standard sounds
        correct_path = os.path.join(SOUNDS_DIR, "correct.wav")
        wrong_path = os.path.join(SOUNDS_DIR, "incorrect.wav")
        level_up_path = os.path.join(SOUNDS_DIR, "levelup.wav")
        achievement_path = os.path.join(SOUNDS_DIR, "achievement.wav")

        self.correct_sound = QSound(correct_path) if os.path.exists(correct_path) else None
        self.wrong_sound = QSound(wrong_path) if os.path.exists(wrong_path) else None
        self.level_up_sound = QSound(level_up_path) if os.path.exists(level_up_path) else None
        self.achievement_sound = QSound(achievement_path) if os.path.exists(achievement_path) else None

    # Instance Methods
    def _play_sound(self, sound_obj, name):
        """Helper to check settings and safely play a sound object."""
        settings = load_settings()
        if not settings.get("sound_enabled", True):
            print(f"🔇 Sound disabled. Skipped playing {name}.")
            return
            
        if sound_obj:
            print(f"🔊 Playing {name}...")
            sound_obj.play()
        else:
            print(f"⚠️ Audio file for {name} not found on disk.")

    # Static Helpers
    @staticmethod
    def play_correct():
        SoundManager.get()._play_sound(SoundManager.get().correct_sound, "correct.wav")

    @staticmethod
    def play_wrong():
        SoundManager.get()._play_sound(SoundManager.get().wrong_sound, "incorrect.wav")

    @staticmethod
    def play_level_up():
        SoundManager.get()._play_sound(SoundManager.get().level_up_sound, "levelup.wav")

    @staticmethod
    def play_confetti():
        print("🎉 Confetti animation triggered")

    @staticmethod
    def play(filename):
        """Play a custom sound file by name (e.g., 'achievement.wav')"""
        if filename == "achievement.wav":
            SoundManager.get()._play_sound(SoundManager.get().achievement_sound, filename)
        else:
            settings = load_settings()
            if settings.get("sound_enabled", True):
                filepath = os.path.join(SOUNDS_DIR, filename)
                if os.path.exists(filepath):
                    QSound.play(filepath)
                else:
                    print(f"⚠️ Audio file not found: {filepath}")