import re
import spacy
from spacy.matcher import Matcher
from nlp.preprocessing import get_spacy_nlp

COMMON_PROBLEM_PATTERNS = [
    (r'(?:wi[-\s]?fi|internet|network|connection).*?(?:disconnect|drop|down|offline|slow|not work|glitch)', "Wi-Fi connectivity disruption"),
    (r'(?:projector|screen|display).*?(?:flicker|not work|broken|won\'?t display|blank)', "projector display malfunction"),
    (r'(?:water|pipe|ceiling).*?(?:leak|burst|drip)', "water leakage"),
    (r'(?:ac|air condition).*?(?:not work|stopped|broken|hot air|not cool)', "air conditioning failure"),
    (r'(?:restroom|washroom|toilet).*?(?:dirty|not clean|smell|stench|overflow|clog)', "restroom hygiene and sanitation issue"),
    (r'(?:printer|copier).*?(?:jam|not work|out of paper|toner)', "printer malfunction"),
    (r'(?:power|electric).*?(?:outage|cut|blackout|tripped|shut off)', "electrical power outage"),
    (r'(?:street ?light|lamp ?post|light bulb).*?(?:broken|dead|flicker|exposed)', "lighting infrastructure fault"),
    (r'(?:smoke|fire|arcing|sparks?)', "smoke / fire safety hazard"),
    (r'(?:shuttle|bus).*?(?:late|delay|reckless|speeding|missed|not arrive)', "campus shuttle transport delay/service issue"),
    (r'(?:portal|e-learning|lms).*?(?:crash|down|500 error|timeout|not load|not show)', "student portal system error"),
    (r'(?:elevator|lift).*?(?:stuck|jerk|noise|stopped)', "elevator mechanical fault"),
    (r'(?:door|lock).*?(?:jam|broken|won\'?t latch|padlock)', "door lock / access mechanism defect"),
    (r'\b(?:lost|found)\b.*?\b(?:wallet|keys|id|card|charger|laptop|airpods)\b', "lost and found inquiry")
]

def extract_main_issue(doc, text: str) -> str:
    """
    Extract transparent, explainable problem phrase using regex patterns + spaCy dependency parsing.
    """
    text_lower = text.lower()
    
    # 1. Pattern Matching on High-Confidence Campus Problem Types
    for pattern, canonical in COMMON_PROBLEM_PATTERNS:
        if re.search(pattern, text_lower):
            return canonical
            
    # 2. Dependency Parsing (Extract Subject + Negation + Verb + Object)
    parts = []
    root = None
    for token in doc:
        if token.dep_ == "ROOT":
            root = token
            break
            
    if root is not None:
        # Find subject of root
        subj = [w.text for w in root.lefts if "subj" in w.dep_]
        # Find negations
        negs = [w.text for w in root.children if w.dep_ == "neg"]
        # Find direct objects or complements
        objs = [w.text for w in root.rights if w.dep_ in ["dobj", "attr", "acomp", "prep"]]
        
        clause = []
        if subj:
            clause.append(" ".join(subj))
        if negs:
            clause.append(" ".join(negs))
        clause.append(root.lemma_ if root.pos_ == "VERB" else root.text)
        if objs:
            clause.append(" ".join(objs[:2]))
            
        res = " ".join(clause).strip()
        if len(res) >= 5 and len(res) <= 45:
            return res
            
    # 3. Fallback: Concise first clause
    first_clause = text.split('.')[0].strip()
    first_clause = re.split(r'[,;]|\band\b', first_clause)[0].strip()
    if len(first_clause) > 50:
        first_clause = first_clause[:47] + "..."
    return first_clause if first_clause else "Unspecified issue"

def extract_information(text: str, user_provided_location: str | None = None) -> dict:
    """
    Extract structured information from complaint text using spaCy NER, 
    custom Matchers, and Regex rules.
    """
    if not text or not isinstance(text, str):
        return {
            "location": user_provided_location if user_provided_location else "Not specified",
            "extracted_location": None,
            "user_location": user_provided_location,
            "building": None,
            "room": None,
            "date": None,
            "time": None,
            "person": None,
            "org": None,
            "issue": "No description provided",
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
    room_pattern = r'\b(?:Room|Lab|Computer Lab|Engineering Lab|Physics Lab|Chemistry Lab|Lecture Hall|Hall|Seminar Hall|Room\s*#?)\s*(?:[A-Z0-9\-]+|\d+)\b'
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
    extracted_loc = None
    if room and building:
        extracted_loc = f"{room}, {building}"
    elif room:
        extracted_loc = room
    elif building:
        extracted_loc = building
    else:
        text_lower = text.lower()
        for loc_kw in location_keywords:
            if loc_kw in text_lower:
                extracted_loc = loc_kw.title()
                break

    # Prioritize user-provided location when explicitly given (Issue 13 / Correction 16)
    if user_provided_location and user_provided_location.strip():
        final_location = user_provided_location.strip()
    elif extracted_loc:
        final_location = extracted_loc
    else:
        final_location = "Not specified"

    # 3. Issue / Problem Phrase Extraction
    issue = extract_main_issue(doc, text)
    
    return {
        "location": final_location,
        "extracted_location": extracted_loc,
        "user_location": user_provided_location,
        "building": building,
        "room": room,
        "date": date_entity,
        "time": time_entity,
        "person": person_entity,
        "org": org_entity,
        "issue": issue,
        "spacy_entities": spacy_entities
    }

if __name__ == "__main__":
    sample = "There is water leaking from the ceiling near the cafeteria and the floor is very slippery."
    res = extract_information(sample)
    print("Extracted Info:")
    print("Location:", res["location"])
    print("Issue:", res["issue"])
