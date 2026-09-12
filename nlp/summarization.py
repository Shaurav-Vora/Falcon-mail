def generate_summary(text: str, category: str, urgency: str, extracted_info: dict) -> str:
    """
    Generate a concise, structured summary of a complaint based on NLP analysis.
    
    Modular Design:
    - Currently uses structured extractive synthesis (fast, deterministic, zero-latency).
    - Can be easily swapped with Hugging Face Transformers BART/T5 models in future phases.
    """
    location = extracted_info.get("location")
    issue = extracted_info.get("issue")
    
    if location and location != "Not specified":
        loc_str = f"in/near {location}"
    else:
        loc_str = "on campus"
        
    if urgency == "Critical":
        summary = f"CRITICAL INCIDENT: {category} issue ({issue}) reported {loc_str}. Immediate safety intervention required."
    elif urgency == "High":
        summary = f"HIGH PRIORITY: {category} issue ({issue}) reported {loc_str} requiring urgent maintenance response."
    else:
        summary = f"{category} report: {issue.capitalize()} reported {loc_str}."
        
    return summary

if __name__ == "__main__":
    test_text = "The air conditioner in Room 302 has not worked for three days."
    test_info = {"location": "Room 302", "issue": "air conditioner not working"}
    summary = generate_summary(test_text, "Maintenance", "Medium", test_info)
    print("Generated Summary:", summary)
