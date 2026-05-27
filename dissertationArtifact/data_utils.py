import json
import os

# Paths
# Dynamically find courses.json based on where this script lives
COURSES_PATH = os.path.join(os.path.dirname(__file__), "courses.json")

# Courses
def load_courses():
    """Safely loads the static course data from courses.json."""
    if not os.path.exists(COURSES_PATH):
        print(f"⚠️ WARNING: courses.json not found at {COURSES_PATH}")
        return {}
        
    try:
        with open(COURSES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("❌ ERROR: courses.json is corrupted and cannot be parsed.")
        return {}
    except Exception as e:
        print(f"❌ ERROR: An unexpected error occurred reading courses: {e}")
        return {}
