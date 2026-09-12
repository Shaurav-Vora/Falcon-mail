from config import CATEGORY_DEPARTMENT_MAP, EMERGENCY_KEYWORDS


def get_recommended_department(category: str) -> str:
    """Map predicted category to recommended department."""
    return CATEGORY_DEPARTMENT_MAP.get(category, "General Services / Helpdesk")


def check_emergency_keywords(text: str) -> bool:
    """Check if complaint contains critical emergency keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in EMERGENCY_KEYWORDS)


def format_confidence(confidence: float) -> str:
    """Format confidence float to percentage string."""
    return f"{confidence * 100:.1f}%"
