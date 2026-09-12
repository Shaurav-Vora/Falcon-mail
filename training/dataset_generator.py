import os
import sys
import random
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH, RANDOM_SEED

# Set seed for deterministic reproducibility
random.seed(RANDOM_SEED)

# Base templates with assigned unique template_group_id, category, and ground-truth urgency
# Urgency Labeling Policy:
# - Critical: Clear immediate physical danger, severe injury risk, fire/explosion/sparks, panic failure
# - High: Severe operational disruption, imminent exams/deadlines, flooding, power outage, safety hazards
# - Medium: Notable inconvenience affecting standard campus routine, non-emergency equipment breakdown
# - Low: Minor cosmetic flaws, slight delays, non-urgent information or lost-and-found reports

BASE_TEMPLATES = [
    # ----------------------------------------------------
    # 1. IT Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_IT_001", "The Wi-Fi network keeps disconnecting every few minutes in Computer Lab 3.", "IT", "Medium"),
    ("T_IT_002", "Students are unable to log into the portal from the Library terminals.", "IT", "Medium"),
    ("T_IT_003", "The projector in Lecture Hall A is flickering and won't display slides clearly.", "IT", "Low"),
    ("T_IT_004", "All computers in Lab 204 are frozen and displaying a blue screen crash error.", "IT", "High"),
    ("T_IT_005", "Internet speed in the male dormitory has been sluggish since yesterday.", "IT", "Low"),
    ("T_IT_006", "The printer in the student center ran out of toner and paper.", "IT", "Low"),
    ("T_IT_007", "Smartboard in Room 402 is unresponsive to touch input and digital pen.", "IT", "Medium"),
    ("T_IT_008", "Campus e-learning portal crashed right during the online assignment submission window.", "IT", "High"),
    ("T_IT_009", "Microphone sound system in Auditorium B is corrupted with heavy static noise.", "IT", "Low"),
    ("T_IT_010", "Cannot access the university online research database from off-campus VPN.", "IT", "Medium"),
    ("T_IT_011", "The desktop computer in Room 108 will not power on at all.", "IT", "Low"),
    ("T_IT_012", "Ethernet network port in faculty office 215 is physically loose and broken.", "IT", "Low"),
    ("T_IT_013", "The campus wireless signal is completely dead in the science building basement.", "IT", "Medium"),
    ("T_IT_014", "Software license for MATLAB expired on all machines in Engineering Lab 2.", "IT", "Medium"),
    ("T_IT_015", "Student ID card scanner at the main library turnstile is failing to read cards.", "IT", "High"),
    ("T_IT_016", "VPN authentication server is rejecting valid student credentials.", "IT", "High"),
    ("T_IT_017", "Submitting final assignments on the portal produces an internal server 500 error.", "IT", "High"),
    ("T_IT_018", "HDMI cable attached to the teaching podium in Room 210 is torn.", "IT", "Low"),
    ("T_IT_019", "The biometric attendance scanner at the main gate entrance is completely offline.", "IT", "High"),
    ("T_IT_020", "Cloud storage drive for final year project repository is inaccessible.", "IT", "High"),

    # ----------------------------------------------------
    # 2. Maintenance Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_MNT_001", "The door lock in Room 304 is broken and the door cannot latch shut.", "Maintenance", "Medium"),
    ("T_MNT_002", "Window pane in Block C second floor corridor is cracked and loose.", "Maintenance", "Medium"),
    ("T_MNT_003", "Air conditioning in Lecture Hall 2 stopped working and the room is overheating.", "Maintenance", "Medium"),
    ("T_MNT_004", "Elevator in the Administration building is making grinding noises and jerking abruptly.", "Maintenance", "High"),
    ("T_MNT_005", "Ceiling panel near the faculty lounge is sagging heavily and about to fall.", "Maintenance", "High"),
    ("T_MNT_006", "Desks and chairs in Room 102 have wobbly legs and damaged surfaces.", "Maintenance", "Low"),
    ("T_MNT_007", "Staircase handrail near Block B emergency exit is loose and unstable.", "Maintenance", "Medium"),
    ("T_MNT_008", "Whiteboard in Room 205 detached from the wall bracket.", "Maintenance", "Low"),
    ("T_MNT_009", "The main entry door of the Chemistry department is jammed shut.", "Maintenance", "Medium"),
    ("T_MNT_010", "Window blinds in Room 410 are jammed in the lowered position.", "Maintenance", "Low"),
    ("T_MNT_011", "Floor tiles in the central corridor are cracked creating an uneven surface.", "Maintenance", "Medium"),
    ("T_MNT_012", "Exhaust ventilation fan in the workshop is screeching loudly.", "Maintenance", "Medium"),
    ("T_MNT_013", "Automatic sliding glass door at the main entrance is stuck half-open.", "Maintenance", "Medium"),
    ("T_MNT_014", "Corridor wall plaster in Block A is peeling and dropping debris on the floor.", "Maintenance", "Low"),
    ("T_MNT_015", "Door handle of the rest room on the 3rd floor came off completely.", "Maintenance", "Low"),
    ("T_MNT_016", "Outdoor seating benches in the courtyard have broken wooden slats.", "Maintenance", "Low"),
    ("T_MNT_017", "Metal shutter of the cafeteria supply room is off its alignment track.", "Maintenance", "Medium"),
    ("T_MNT_018", "Roof shingles near the auditorium terrace are loose after strong winds.", "Maintenance", "Medium"),
    ("T_MNT_019", "Partition divider in Seminar Hall 1 is unsteady and rattling.", "Maintenance", "Low"),
    ("T_MNT_020", "Heavy main entrance gate hinges are squeaking and sticking.", "Maintenance", "Low"),

    # ----------------------------------------------------
    # 3. Safety Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_SAF_001", "There is thick smoke coming from an electrical panel near Block A ground floor.", "Safety", "Critical"),
    ("T_SAF_002", "Fire extinguisher in the Chemistry lab is missing from its designated wall mount.", "Safety", "High"),
    ("T_SAF_003", "Emergency exit door in Block C is padlocked shut preventing evacuation.", "Safety", "Critical"),
    ("T_SAF_004", "Aggressive stray dog entered the campus perimeter near the sports ground.", "Safety", "Medium"),
    ("T_SAF_005", "Pedestrian pathway behind the sports arena has no functioning street lighting at night.", "Safety", "High"),
    ("T_SAF_006", "Hazardous chemical spill of unidentified liquid reported in Chemistry Lab 3.", "Safety", "Critical"),
    ("T_SAF_007", "Unattended suspicious package left abandoned near the main entrance lobby.", "Safety", "Critical"),
    ("T_SAF_008", "Bare live electrical wires exposed on the hallway wall near Room 105.", "Safety", "Critical"),
    ("T_SAF_009", "Security guard post at the East Gate was left completely unmanned overnight.", "Safety", "Medium"),
    ("T_SAF_010", "Pungent gas leak smell detected near the chemical storage depot.", "Safety", "Critical"),
    ("T_SAF_011", "Oil slick on the workshop floor caused a student to slip and fall heavily.", "Safety", "High"),
    ("T_SAF_012", "CCTV security camera covering the female dormitory entrance is damaged.", "Safety", "High"),
    ("T_SAF_013", "Fire alarm sensor in Block B is sounding continuous false alarms.", "Safety", "Medium"),
    ("T_SAF_014", "Unidentified person without visitor badge wandering inside student dormitories.", "Safety", "High"),
    ("T_SAF_015", "Shattered glass shards scattered across the main walkway near the cafeteria.", "Safety", "Medium"),
    ("T_SAF_016", "Construction debris with exposed sharp rusty nails left open along walkway.", "Safety", "High"),
    ("T_SAF_017", "Large tree branch fractured and hanging precariously over student walkway.", "Safety", "High"),
    ("T_SAF_018", "Smoke detector in dormitory Room 201 has been tampered with and covered.", "Safety", "High"),
    ("T_SAF_019", "Emergency stop panic button inside the central elevator does not trigger.", "Safety", "Critical"),
    ("T_SAF_020", "Balcony protective railing on 4th floor Block C is structurally compromised.", "Safety", "Critical"),

    # ----------------------------------------------------
    # 4. Academic Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_ACD_001", "My learning portal is not displaying registered subjects and exam starts tomorrow morning.", "Academic", "High"),
    ("T_ACD_002", "Midterm examination timetable has scheduled two core subjects at the exact same hour.", "Academic", "High"),
    ("T_ACD_003", "Course syllabus and reference material for Data Structures have not been uploaded.", "Academic", "Low"),
    ("T_ACD_004", "Instructor was absent without notice for the scheduled 9 AM mathematics lecture.", "Academic", "Medium"),
    ("T_ACD_005", "Official grade transcript generated on portal contains incorrect marks for Semester 3.", "Academic", "High"),
    ("T_ACD_006", "Recommended textbooks for Engineering Physics are out of stock in the campus library.", "Academic", "Low"),
    ("T_ACD_007", "Laboratory manual for Microprocessors contains outdated and conflicting circuit diagrams.", "Academic", "Low"),
    ("T_ACD_008", "Faculty feedback evaluation form link is throwing a session timeout error.", "Academic", "Medium"),
    ("T_ACD_009", "Attendance record is falsely marking me absent for yesterday's lab session.", "Academic", "Medium"),
    ("T_ACD_010", "Lecture hall capacity is 40 seats but 65 students are enrolled in the course.", "Academic", "Medium"),
    ("T_ACD_011", "No teaching assistant has been assigned to support weekly programming tutorial batches.", "Academic", "Low"),
    ("T_ACD_012", "Final exam hall seating arrangement list shows conflicting room numbers for students.", "Academic", "High"),
    ("T_ACD_013", "Academic advisor has not responded to elective course approval request for two weeks.", "Academic", "Medium"),
    ("T_ACD_014", "Prerequisite waiver has not been processed on the portal blocking graduation registration.", "Academic", "High"),
    ("T_ACD_015", "Senior thesis advisor allocations have still not been published.", "Academic", "Low"),
    ("T_ACD_016", "Recorded lecture video links on the portal are broken and return 404.", "Academic", "Low"),
    ("T_ACD_017", "Paper re-evaluation submission portal has closed ahead of the officially announced date.", "Academic", "High"),
    ("T_ACD_018", "Noise levels from adjacent corridor disrupt study in the quiet library zone.", "Academic", "Low"),
    ("T_ACD_019", "Spelling error in student name printed on degree certificate verification draft.", "Academic", "High"),
    ("T_ACD_020", "Assignment submission deadline was abruptly changed without email notification.", "Academic", "Medium"),

    # ----------------------------------------------------
    # 5. Administration Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_ADM_001", "Tuition fee refund request for duplicate transaction is delayed over four weeks.", "Administration", "Medium"),
    ("T_ADM_002", "Only one cashier counter is operating at student finance resulting in massive queues.", "Administration", "Low"),
    ("T_ADM_003", "Student identity card counter remains shut during official advertised office hours.", "Administration", "Low"),
    ("T_ADM_004", "Application status for official transcript issuance has been stuck on pending for weeks.", "Administration", "Medium"),
    ("T_ADM_005", "Academic scholarship stipend disbursement check has not cleared into student bank account.", "Administration", "High"),
    ("T_ADM_006", "Disciplinary review notification was issued with mismatched student registration number.", "Administration", "Medium"),
    ("T_ADM_007", "No Objection Certificate document for mandatory internship visa is pending approval for weeks.", "Administration", "Medium"),
    ("T_ADM_008", "Administration helpdesk staff was uncooperative regarding clearance sign-off.", "Administration", "Low"),
    ("T_ADM_009", "Hostel accommodation allocation list contains duplicated room numbers.", "Administration", "Medium"),
    ("T_ADM_010", "Campus parking permit fee was debited twice from my university billing account.", "Administration", "Medium"),
    ("T_ADM_011", "Late payment penalty fee levied despite proof of payment before deadline date.", "Administration", "High"),
    ("T_ADM_012", "Student health insurance card was not delivered to international freshmen.", "Administration", "Medium"),
    ("T_ADM_013", "University general inquiry telephone lines are permanently engaged without voicemail.", "Administration", "Low"),
    ("T_ADM_014", "Graduation clearance portal is rejecting attested valid degree documentation.", "Administration", "High"),
    ("T_ADM_015", "Hostel security caution deposit refund has not been released post-checkout.", "Administration", "Medium"),
    ("T_ADM_016", "Transport pass renewal counter clerk behaved discourteously to queuing students.", "Administration", "Low"),
    ("T_ADM_017", "Fee breakdown receipt statement omits laboratory fee component.", "Administration", "Low"),
    ("T_ADM_018", "Financial hold on portal preventing exam hall ticket download after paying dues.", "Administration", "High"),
    ("T_ADM_019", "Transcript delivery address was recorded incorrectly by the registrar desk.", "Administration", "Medium"),
    ("T_ADM_020", "Immigration visa renewal documents not processed before expiry date.", "Administration", "High"),

    # ----------------------------------------------------
    # 6. Transport Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_TRN_001", "Campus shuttle bus route 2 arrived 45 minutes late during morning pickup.", "Transport", "Medium"),
    ("T_TRN_002", "Shuttle bus driver was operating vehicle recklessly near the pedestrian crossing.", "Transport", "High"),
    ("T_TRN_003", "Air conditioning inside university commuter bus 5 is defective.", "Transport", "Low"),
    ("T_TRN_004", "Insufficient seating on morning shuttle forcing students to stand in the aisle.", "Transport", "Medium"),
    ("T_TRN_005", "Campus parking lot B is congested due to non-permitted external commercial vehicles.", "Transport", "Low"),
    ("T_TRN_006", "Campus bicycle sharing station near the library has zero functional bicycles.", "Transport", "Low"),
    ("T_TRN_007", "Bus shelter canopy is leaking water heavily during rainy weather.", "Transport", "Low"),
    ("T_TRN_008", "University transport mobile application is failing to transmit live GPS location.", "Transport", "Low"),
    ("T_TRN_009", "Late night scheduled shuttle service was cancelled without prior broadcast.", "Transport", "Medium"),
    ("T_TRN_010", "Traffic bottleneck at main campus gate due to malfunctioning automated boom barrier.", "Transport", "Medium"),
    ("T_TRN_011", "Electric vehicle charging station near Block D displays an error code.", "Transport", "Low"),
    ("T_TRN_012", "Bus automated pneumatic door jammed shut trapping passenger backpack.", "Transport", "High"),
    ("T_TRN_013", "Parking payment kiosk took cash note but did not dispense an exit validation ticket.", "Transport", "Low"),
    ("T_TRN_014", "Shuttle driver was texting on phone while operating loaded bus on campus road.", "Transport", "High"),
    ("T_TRN_015", "Accessible disabled parking spaces near reception are routinely blocked by unauthorized cars.", "Transport", "Medium"),
    ("T_TRN_016", "Shuttle bus headlamp is dead on the driver side during night service.", "Transport", "High"),
    ("T_TRN_017", "Bicycle lane along the campus perimeter is blocked by maintenance machinery.", "Transport", "Low"),
    ("T_TRN_018", "Driver bypassed scheduled student stop leaving ten students stranded.", "Transport", "Medium"),
    ("T_TRN_019", "Severe exhaust fumes leaking into the passenger cabin of bus 4.", "Transport", "High"),
    ("T_TRN_020", "Bus timetable posted on campus board contradicts the digital schedule.", "Transport", "Low"),

    # ----------------------------------------------------
    # 7. Facilities Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_FAC_001", "Complete water supply disruption in washrooms of Block B second floor.", "Facilities", "High"),
    ("T_FAC_002", "Study cubicles in the library have defective desks and dead electrical sockets.", "Facilities", "Low"),
    ("T_FAC_003", "Drinking water dispenser on 3rd floor is dispensing unchilled warm water.", "Facilities", "Low"),
    ("T_FAC_004", "Student cafeteria indoor dining hall is poorly ventilated and stifling hot.", "Facilities", "Low"),
    ("T_FAC_005", "Gymnasium pulley cable snapped during a workout posing severe hazard.", "Facilities", "High"),
    ("T_FAC_006", "Indoor sports court synthetic flooring has torn seams creating trip hazards.", "Facilities", "Medium"),
    ("T_FAC_007", "Central auditorium ventilation system is blowing hot dusty air.", "Facilities", "Medium"),
    ("T_FAC_008", "Vending machine in Block A swallowed card payment without dispensing item.", "Facilities", "Low"),
    ("T_FAC_009", "Reading desk overhead lamps in library quiet zone have burned out.", "Facilities", "Low"),
    ("T_FAC_010", "Campus swimming pool water is murky green and smells heavily foul.", "Facilities", "High"),
    ("T_FAC_011", "Metal lockers in the sports pavilion have jammed rusted padlocks.", "Facilities", "Low"),
    ("T_FAC_012", "Microwave oven in the cafeteria dining area is sparking inside.", "Facilities", "High"),
    ("T_FAC_013", "Outdoor basketball court floodlights fail to ignite after sunset.", "Facilities", "Low"),
    ("T_FAC_014", "Sanitary vending machine in female facility is empty and jammed.", "Facilities", "Medium"),
    ("T_FAC_015", "Water filter indicator lamp on drinking fountain turns red indicating dirty water.", "Facilities", "High"),
    ("T_FAC_016", "Common room furniture upholstery is shredded and dirty.", "Facilities", "Low"),
    ("T_FAC_017", "Lockers in the biology laboratory cannot be locked securely.", "Facilities", "Low"),
    ("T_FAC_018", "Hand sanitizer dispensers throughout the science block are completely dry.", "Facilities", "Low"),
    ("T_FAC_019", "Central heating in dormitory blocks during cold weather is non-functional.", "Facilities", "High"),
    ("T_FAC_020", "Squash court door glass panel is loose and vibrating on impact.", "Facilities", "Medium"),

    # ----------------------------------------------------
    # 8. Cleanliness Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_CLN_001", "Restroom near the main cafeteria has not been cleaned since yesterday morning.", "Cleanliness", "Medium"),
    ("T_CLN_002", "Waste bins near Block A entrance are overflowing with rotting food scraps.", "Cleanliness", "Low"),
    ("T_CLN_003", "Pigeon droppings accumulated across windowsills and desks in Block C.", "Cleanliness", "Low"),
    ("T_CLN_004", "Heavy dust and cobwebs hanging from the ceiling corners in Room 204.", "Cleanliness", "Low"),
    ("T_CLN_005", "Dining tables in cafeteria are coated with sticky spills and food residue.", "Cleanliness", "Medium"),
    ("T_CLN_006", "Stench of rotting garbage emanating from dumpsters behind the student canteen.", "Cleanliness", "Medium"),
    ("T_CLN_007", "Stairwell landings in Science Block floor 3 are covered in mud and litter.", "Cleanliness", "Low"),
    ("T_CLN_008", "Washroom floor is flooded with contaminated water and slippery soap lather.", "Cleanliness", "High"),
    ("T_CLN_009", "Cockroaches and insects observed crawling inside hostel food preparation area.", "Cleanliness", "High"),
    ("T_CLN_010", "Medical clinic biohazard waste container left unsealed in common reception.", "Cleanliness", "High"),
    ("T_CLN_011", "Recycling receptacles in Computer Lab 1 have not been emptied for days.", "Cleanliness", "Low"),
    ("T_CLN_012", "Stagnant rainwater puddle in hostel courtyard breeding mosquitoes.", "Cleanliness", "High"),
    ("T_CLN_013", "Black mildew patches spreading across shower stalls in dorm building 2.", "Cleanliness", "Medium"),
    ("T_CLN_014", "Discarded beverage containers and food wrappers strewn across library desks.", "Cleanliness", "Low"),
    ("T_CLN_015", "Janitorial equipment and dirty wash bucket left obstructing corridor doorway.", "Cleanliness", "Low"),
    ("T_CLN_016", "Carpet in the seminar room has a persistent damp musty smell.", "Cleanliness", "Low"),
    ("T_CLN_017", "Graffiti scrawled on hallway walls in Block D second floor.", "Cleanliness", "Low"),
    ("T_CLN_018", "Hand wash liquid soap dispensers in central restrooms are all empty.", "Cleanliness", "Medium"),
    ("T_CLN_019", "Rotting fruit left uncollected beneath trees in front garden creating stench.", "Cleanliness", "Low"),
    ("T_CLN_020", "Urinal drains in ground floor male restroom blocked and emitting stench.", "Cleanliness", "High"),

    # ----------------------------------------------------
    # 9. Electrical Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_ELC_001", "Power outage in Block B west wing plunged classrooms into total darkness.", "Electrical", "High"),
    ("T_ELC_002", "Fluorescent ceiling tubes in Room 302 are flickering violently causing headaches.", "Electrical", "Low"),
    ("T_ELC_003", "Electrical wall receptacle in Room 104 sparked and produced smoke when plugging in charger.", "Electrical", "High"),
    ("T_ELC_004", "Main circuit breaker tripped in Physics Lab 2 shutting off delicate lab sensors.", "Electrical", "Medium"),
    ("T_ELC_005", "Ceiling fan in Room 205 is wobbling dangerously and making grinding metallic sounds.", "Electrical", "Medium"),
    ("T_ELC_006", "Outdoor lamppost base near library pathway has exposed energized wires.", "Electrical", "Critical"),
    ("T_ELC_007", "UPS battery storage cabinet in server room is emitting high-pitched warning sirens.", "Electrical", "High"),
    ("T_ELC_008", "Switchboard faceplate in chemistry laboratory is scorched and warm to the touch.", "Electrical", "High"),
    ("T_ELC_009", "Severe voltage fluctuations in Room 401 caused equipment monitors to reset.", "Electrical", "Medium"),
    ("T_ELC_010", "Main electrical distribution panel in basement is producing visible arcing sparks.", "Electrical", "Critical"),
    ("T_ELC_011", "Emergency evacuation lighting units failed to activate during power cut.", "Electrical", "High"),
    ("T_ELC_012", "Exhaust fan electrical cabling short-circuited inside cafeteria kitchen.", "Electrical", "High"),
    ("T_ELC_013", "Heavy duty extension cord in seminar auditorium has frayed burnt rubber insulation.", "Electrical", "High"),
    ("T_ELC_014", "Air conditioning outdoor compressor cable caught fire outside Block D.", "Electrical", "Critical"),
    ("T_ELC_015", "Overhead lighting fixtures in ground floor corridor are dead leaving area dark.", "Electrical", "Medium"),
    ("T_ELC_016", "Auditorium stage lighting panel emitting burnt plastic smell during rehearsal.", "Electrical", "High"),
    ("T_ELC_017", "Electric water geyser in sports locker room blew its internal fuse.", "Electrical", "Medium"),
    ("T_ELC_018", "Corridor motion sensors for automatic lights are defective.", "Electrical", "Low"),
    ("T_ELC_019", "Outdoor transformer unit in courtyard making loud buzzing humming sound.", "Electrical", "High"),
    ("T_ELC_020", "Wall socket switch plate is cracked in dormitory room 112.", "Electrical", "Low"),

    # ----------------------------------------------------
    # 10. Plumbing Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_PLM_001", "Water is leaking from ceiling tiles near cafeteria and floor is slippery.", "Plumbing", "High"),
    ("T_PLM_002", "Washroom supply pipe in Block A 2nd floor ruptured spraying pressurized water.", "Plumbing", "High"),
    ("T_PLM_003", "Toilet bowl in male restroom Room 102 is clogged and overflowing onto floor.", "Plumbing", "High"),
    ("T_PLM_004", "Zero water pressure discharging from faucets in chemical engineering lab.", "Plumbing", "Medium"),
    ("T_PLM_005", "Waste drainage pipe under library washbasin is uncoupled and leaking.", "Plumbing", "Medium"),
    ("T_PLM_006", "Hot water heater system in student residential hostel is completely cold.", "Plumbing", "Low"),
    ("T_PLM_007", "Flush cistern mechanism in girls restroom floor 1 running continuously.", "Plumbing", "Low"),
    ("T_PLM_008", "Underground main water supply conduit burst forming a deep trench near courtyard.", "Plumbing", "High"),
    ("T_PLM_009", "Brown discolored sediment-laden tap water coming out of drinking fountain.", "Plumbing", "High"),
    ("T_PLM_010", "Shower floor drain in hostel room 304 is blocked with pooling stagnant water.", "Plumbing", "Medium"),
    ("T_PLM_011", "Boiler pressure valve in residential block ruptured spewing hot steam.", "Plumbing", "High"),
    ("T_PLM_012", "Sewer gases backing up through drainage grates in ground floor corridor.", "Plumbing", "Medium"),
    ("T_PLM_013", "Overhead water pipe dripping directly above computer server racks.", "Plumbing", "Critical"),
    ("T_PLM_014", "Outdoor landscape watering valve stuck wide open wasting water.", "Plumbing", "Medium"),
    ("T_PLM_015", "Overhead water storage tank on Block C roof is overflowing down the exterior wall.", "Plumbing", "Medium"),
    ("T_PLM_016", "Sink tap in faculty kitchenette is dripping constantly and won't turn off.", "Plumbing", "Low"),
    ("T_PLM_017", "Gutter downspout cracked and pouring rainwater against laboratory foundation.", "Plumbing", "Medium"),
    ("T_PLM_018", "Urinal auto-flush sensor defective resulting in stagnant waste.", "Plumbing", "Medium"),
    ("T_PLM_019", "Drinking water cooler pipe leaking puddle onto wooden library floor.", "Plumbing", "Medium"),
    ("T_PLM_020", "Water pressure in dormitory showers dropped to a trickle.", "Plumbing", "Low"),

    # ----------------------------------------------------
    # 11. Other Complaints (20 base templates)
    # ----------------------------------------------------
    ("T_OTH_001", "Lost black leather wallet containing student identity card and bank cards near library.", "Other", "Low"),
    ("T_OTH_002", "Found a bunch of keys with a blue lanyard on the wooden bench outside cafeteria.", "Other", "Low"),
    ("T_OTH_003", "Lost silver laptop charger left behind in Lecture Hall 3 after the 2 PM session.", "Other", "Low"),
    ("T_OTH_004", "An injured campus cat near the staff car park requires immediate veterinary care.", "Other", "Medium"),
    ("T_OTH_005", "Noisy structural drilling outside library during mid-semester examination hours.", "Other", "Medium"),
    ("T_OTH_006", "Student club requesting approval to host blood donation drive in the activity center.", "Other", "Low"),
    ("T_OTH_007", "Lost prescription eyewear inside a black protective case near Block A stairwell.", "Other", "Low"),
    ("T_OTH_008", "Found unclaimed dark winter jacket draped over seat 14 in Auditorium A.", "Other", "Low"),
    ("T_OTH_009", "Excessively loud amplified music played late at night from adjacent hostel wing.", "Other", "Low"),
    ("T_OTH_010", "General inquiry regarding the working hours of the campus lost and found repository.", "Other", "Low"),
    ("T_OTH_011", "Lost scientific calculator left on desk 12 in the engineering design room.", "Other", "Low"),
    ("T_OTH_012", "Found student umbrella near the main entrance turnstiles after morning rain.", "Other", "Low"),
    ("T_OTH_013", "Requesting information on guest parking passes for visiting family members.", "Other", "Low"),
    ("T_OTH_014", "Stray kittens found sheltered inside the outdoor electrical equipment shed.", "Other", "Medium"),
    ("T_OTH_015", "Lost blue student backpack containing textbooks near the sports ground bleachers.", "Other", "Low"),
    ("T_OTH_016", "Inquiry regarding procedure for campus locker deposit return.", "Other", "Low"),
    ("T_OTH_017", "Commercial advertising posters pasted across notice boards without permission.", "Other", "Low"),
    ("T_OTH_018", "Drone flown unauthorized over student dormitory recreational area.", "Other", "Medium"),
    ("T_OTH_019", "Lost silver wristwatch in the gymnasium changing room.", "Other", "Low"),
    ("T_OTH_020", "Feedback regarding food options and dietary variety in campus food stalls.", "Other", "Low"),
]

# Neutral context/time phrases that do NOT alter the complaint's urgency
NEUTRAL_CONTEXT_PHRASES = [
    "for the past two days",
    "since yesterday morning",
    "noticed by several students",
    "causing inconvenience to students and staff",
    "observed during the morning class",
    "reported earlier today",
    "this has been ongoing since last week",
    "several people have pointed this out",
    "which is affecting normal activities",
    "affecting people in the area"
]

# Syntactic introductory variations
INTRO_VARIATIONS = [
    "Please note:",
    "Reporting that",
    "Urgent notification:",
    "Attention needed:",
    "Incident report:",
    "Campus report:"
]

def generate_dataset():
    """
    Generates synthetic dataset of university complaints with:
    - Explicit template_group_id to eliminate data leakage.
    - Internally consistent urgency labels (Issue 2).
    - Balanced class distribution across all 11 categories (Issue 3).
    - Preserved campus realism without identical copies.
    """
    records = []
    
    for template_id, base_text, category, urgency in BASE_TEMPLATES:
        # 1. Base sample
        records.append({
            "template_group_id": template_id,
            "text": base_text,
            "category": category,
            "urgency": urgency
        })
        
        # 2. Contextual variation (neutral context modifier preserving urgency)
        ctx = random.choice(NEUTRAL_CONTEXT_PHRASES)
        text_ctx = f"{base_text.rstrip('.')} {ctx}."
        records.append({
            "template_group_id": template_id,
            "text": text_ctx,
            "category": category,
            "urgency": urgency
        })
        
        # 3. Natural syntactic variation (active phrasing / inverted)
        if "is" in base_text:
            text_alt = base_text.replace(" is ", " has been ").replace(" are ", " have been ")
            if text_alt != base_text:
                records.append({
                    "template_group_id": template_id,
                    "text": text_alt,
                    "category": category,
                    "urgency": urgency
                })
        elif "The " in base_text:
            text_alt = f"Regarding the campus facilities: {base_text}"
            records.append({
                "template_group_id": template_id,
                "text": text_alt,
                "category": category,
                "urgency": urgency
            })

    df = pd.DataFrame(records)
    # Shuffle while keeping all records intact
    df = df.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
    
    # Ensure columns order
    df = df[["text", "category", "urgency", "template_group_id"]]
    
    df.to_csv(COMPLAINTS_CSV_PATH, index=False)
    
    print(f"==========================================================")
    print(f"       SENTINEL DATASET GENERATOR - EXECUTION REPORT       ")
    print(f"==========================================================")
    print(f"Dataset generated at: {COMPLAINTS_CSV_PATH}")
    print(f"Total samples: {len(df)}")
    print(f"Total unique template groups: {df['template_group_id'].nunique()}")
    print("\nSamples per category:")
    print(df['category'].value_counts().to_string())
    print("\nSamples per urgency:")
    print(df['urgency'].value_counts().to_string())
    print(f"==========================================================")
    
    return df

if __name__ == "__main__":
    generate_dataset()
