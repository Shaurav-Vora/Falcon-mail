import os

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

# Database Path
DB_PATH = os.path.join(DATABASE_DIR, "sentinel.db")

# Reproducibility Central Seed
RANDOM_SEED = 42

# Dataset Path
COMPLAINTS_CSV_PATH = os.path.join(DATA_DIR, "complaints.csv")
UNSEEN_TEST_CSV_PATH = os.path.join(DATA_DIR, "unseen_test_cases.csv")

# Trained Models Paths (Models trained by us on our labeled complaint dataset)
CATEGORY_MODEL_PATH = os.path.join(MODELS_DIR, "category_classifier.pkl")
URGENCY_MODEL_PATH = os.path.join(MODELS_DIR, "urgency_classifier.pkl")

# Pretrained Open-Source NLP Models
SPACY_MODEL_NAME = "en_core_web_sm"
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"

# Duplicate Detection Settings (Selected validation threshold based on 60 labeled pairs: 0.65, F1: 0.8727)
DEFAULT_DUPLICATE_THRESHOLD = 0.65

# Complaint Categories
CATEGORIES = [
    "IT",
    "Maintenance",
    "Safety",
    "Academic",
    "Administration",
    "Transport",
    "Facilities",
    "Cleanliness",
    "Electrical",
    "Plumbing",
    "Other",
]

# Urgency Priority Levels
URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Safety Rule Elevation Keywords (Critical priority override)
EMERGENCY_KEYWORDS = [
    "fire",
    "smoke",
    "electric shock",
    "explosion",
    "gas leak",
    "injured",
    "injury",
    "bleeding",
    "unconscious",
    "structural collapse",
    "bomb",
]

# Time-Sensitive / High Priority Rule Elevation Keywords
HIGH_URGENCY_KEYWORDS = [
    "exam tomorrow",
    "test tomorrow",
    "exam in",
    "test in",
    "very urgent",
    "urgently",
    "urgent",
    "exam starts",
    "test starts",
    "deadline today",
    "deadline in",
    "asap",
    "immediately",
    "portal crashed",
]

# Category to Recommended Department Mapping
CATEGORY_DEPARTMENT_MAP = {
    "IT": "IT Support & Services",
    "Maintenance": "Facilities Management & Maintenance",
    "Safety": "Campus Security & Safety Office",
    "Academic": "Academic Affairs & Registrar",
    "Administration": "General Administration",
    "Transport": "Transport & Parking Department",
    "Facilities": "Facilities & Infrastructure",
    "Cleanliness": "Housekeeping & Janitorial Services",
    "Electrical": "Electrical Maintenance Services",
    "Plumbing": "Plumbing Services",
    "Other": "General Services / Helpdesk",
}
