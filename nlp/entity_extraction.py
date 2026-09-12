import re
import spacy
from spacy.matcher import Matcher
from nlp.preprocessing import get_spacy_nlp

def extract_information(text: str) -> dict:
    """
    Extract structured information from complaint text using spaCy NER, 
    custom Matchers, and Regex rules.
    """
    if not text or not isinstance(text, str):
        return {
            "location": None,
            "building": None,
            "room": None,
            "date": None,
            "time": None,
            "person": None,
            "org": None,
            "issue": None,
            "entities": {}
        }
        
    nlp = get_spacy_nlp()
    doc = nlp(text)
    
    # 1. Standard spaCy Named Entities
    spacy_entities = {}
    for ent in doc.ents:
        if ent.label_ not in spacy_entities:
            spacy_entities[ent.label_] = []
        spacy_entities[ent.label_].append(ent.text)
        
    date_entity = ", ".join(spacy_entities.get("DATE", [])) if "DATE" in spacy_entities else None
    time_entity = ", ".join(spacy_entities.get("TIME", [])) if "TIME" in spacy_entities else None
    person_entity = ", ".join(spacy_entities.get("PERSON", [])) if "PERSON" in spacy_entities else None
    org_entity = ", ".join(spacy_entities.get("ORG", [])) if "ORG" in spacy_entities else None
    
    # 2. Custom Regex & Matcher rules for Campus Entities
    room_pattern = r'\b(?:Room|Lab|Computer Lab|Lecture Hall|Hall|Seminar Hall)\s*(?:[A-Z0-9\-]+|\d+)\b'
    building_pattern = r'\b(?:Block|Building)\s*[A-Z0-9\-]+\b'
    location_keywords = [
        "cafeteria", "food court", "library", "auditorium", "gymnasium", 
        "sports complex", "canteen", "parking area", "parking lot", 
        "hostel", "dormitory", "main gate", "courtyard", "restroom", "washroom"
    ]
    
    room_match = re.search(room_pattern, text, re.IGNORECASE)
    building_match = re.search(building_pattern, text, re.IGNORECASE)
    
    room = room_match.group(0) if room_match else None
    building = building_match.group(0) if building_match else None
    
    # General campus location search
    location = None
    if room and building:
        location = f"{room}, {building}"
    elif room:
        location = room
    elif building:
        location = building
    else:
        text_lower = text.lower()
        for loc_kw in location_keywords:
            if loc_kw in text_lower:
                # Capitalize nicely
                location = loc_kw.title()
                break

    # 3. Issue / Problem Phrase Extraction
    issue = extract_main_issue(doc, text)
    
    return {
        "location": location if location else "Not specified",
        "building": building,
        "room": room,
        "date": date_entity,
        "time": time_entity,
        "person": person_entity,
        "org": org_entity,
        "issue": issue,
        "spacy_entities": spacy_entities
    }

def extract_main_issue(doc, text: str) -> str:
    """Extract main issue phrase from complaint using spaCy dependency parse."""
    # Look for root verb and its children/objects (e.g. "leaking from ceiling", "stopped working")
    issue_parts = []
    
    for token in doc:
        # Match problem action verbs or nouns
        if token.pos_ in ["VERB", "NOUN", "ADJ"] and token.dep_ in ["ROOT", "nsubj", "dobj", "amod", "attr"]:
            if not token.is_stop or token.lower_ in ["not", "no"]:
                issue_parts.append(token.text)
                
    if len(issue_parts) >= 2:
        return " ".join(issue_parts[:5])
        
    # Fallback: simple first clause summary
    first_sentence = text.split('.')[0].strip()
    return first_sentence if len(first_sentence) < 60 else first_sentence[:60] + "..."

if __name__ == "__main__":
    sample = "There is water leaking from the ceiling near the cafeteria and the floor is very slippery."
    res = extract_information(sample)
    print("Extracted Info:")
    print("Location:", res["location"])
    print("Issue:", res["issue"])
