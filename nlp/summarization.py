import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CATEGORY_DEPARTMENT_MAP

def generate_summary(text: str, category: str, urgency: str, extracted_info: dict) -> str:
    """
    Generate a natural, grammatically sound summary of a campus complaint.
    
    Academic Design:
    - Rule-based extractive synthesis that is deterministic, zero-latency, and runs locally.
    - Dynamically incorporates the recommended department for targeted actionable routing.
    - Avoids hardcoded 'maintenance' references for IT/Academic/Safety incidents.
    - Avoids 'None reported' or awkward phrasing.
    """
    location = extracted_info.get("location")
    issue = extracted_info.get("issue") or "Incident"
    dept = CATEGORY_DEPARTMENT_MAP.get(category, "the responsible department")
    
    # Format location phrase
    if location and location.lower() != "not specified":
        loc_str = f"in {location}" if ("room" in location.lower() or "lab" in location.lower()) else f"near {location}"
    else:
        loc_str = "on campus"
        
    issue_clean = issue.strip().rstrip('.')
    if issue_clean:
        # Lowercase first character if part of sentence, unless abbreviation like Wi-Fi/AC/HDMI
        if not (issue_clean.startswith("Wi-Fi") or issue_clean.startswith("AC") or issue_clean.startswith("HDMI") or issue_clean.startswith("GPS")):
            issue_clean = issue_clean[0].lower() + issue_clean[1:]

    if urgency == "Critical":
        summary = f"CRITICAL INCIDENT: {category} emergency involving {issue_clean} reported {loc_str}. Immediate safety intervention required by {dept}."
    elif urgency == "High":
        summary = f"HIGH PRIORITY: {category} incident regarding {issue_clean} reported {loc_str}, requiring prompt attention from {dept}."
    elif urgency == "Medium":
        summary = f"{category} report: {issue_clean.capitalize()} reported {loc_str}, routed to {dept} for standard operational review."
    else:
        summary = f"{category} log: Minor issue regarding {issue_clean} noted {loc_str}."
        
    return summary

if __name__ == "__main__":
    test_info = {"location": "Lab 205", "issue": "Wi-Fi connectivity disruption"}
    s1 = generate_summary("Wi-Fi down", "IT", "High", test_info)
    print("IT Summary:", s1)
    
    test_info2 = {"location": "Block A ground floor", "issue": "smoke / fire safety hazard"}
    s2 = generate_summary("Smoke in panel", "Safety", "Critical", test_info2)
    print("Safety Summary:", s2)
