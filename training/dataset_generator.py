import os
import sys
import random
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COMPLAINTS_CSV_PATH

# Seed for reproducibility
random.seed(42)

# High-quality templates and variations for dataset generation
COMPLAINT_TEMPLATES = [
    # IT Complaints
    ("The Wi-Fi network keeps disconnecting every few minutes in Computer Lab 3.", "IT", "Medium"),
    ("Students are unable to log into the portal from the Library terminals.", "IT", "Medium"),
    ("The projector in Lecture Hall A is flickering and won't display the slides.", "IT", "Low"),
    ("All computers in Lab 204 are frozen and displaying a blue screen error.", "IT", "High"),
    ("Internet speed in the male dormitory is extremely slow since yesterday.", "IT", "Low"),
    ("The printer in the student center ran out of paper and toner.", "IT", "Low"),
    ("Smartboard in Room 402 is not responding to touch input.", "IT", "Medium"),
    ("Campus e-learning portal crashed right during the online assignment deadline.", "IT", "High"),
    ("Microphone sound in Auditorium B is corrupted with heavy static noise.", "IT", "Low"),
    ("Cannot access the university online library database from off-campus network.", "IT", "Medium"),
    ("The desktop PC in Room 108 will not power on at all.", "IT", "Low"),
    ("Network port in Professor Miller's office is physically broken.", "IT", "Low"),
    ("The campus wireless signal is completely dead in the science building basement.", "IT", "Medium"),
    ("Software license for MATLAB expired on all machines in Engineering Lab 2.", "IT", "Medium"),
    ("Audio speakers in Room 305 are distorting sound during lectures.", "IT", "Low"),
    ("Student ID card scanner at the library entrance is failing to read cards.", "IT", "High"),
    ("VPN access for remote research servers is throwing authorization errors.", "IT", "High"),
    ("The computer monitors in Graphics Lab 1 are showing distorted colors.", "IT", "Low"),
    ("Submitting assignments on the student portal gives HTTP 500 server error.", "IT", "High"),
    ("HDMI cable attached to the podium in Room 210 is damaged and snapped.", "IT", "Low"),
    ("The biometric attendance scanner at the main entrance is offline.", "IT", "High"),
    ("Overhead projector lamp exploded in Physics Lab 102.", "IT", "Medium"),
    ("Unable to reset my student portal password due to SMS gateway timeout.", "IT", "Low"),
    ("The computer lab mouse and keyboard in desk 14 are missing.", "IT", "Low"),
    ("Cloud storage drive for final year project submission is unaccessible.", "IT", "High"),
    ("The digital signage display in the main lobby is stuck on boot loop.", "IT", "Low"),

    # Maintenance Complaints
    ("The door lock in Room 304 is broken and the door won't latch properly.", "Maintenance", "Medium"),
    ("Window glass in Block C second floor corridor is cracked and loose.", "Maintenance", "Medium"),
    ("Air conditioning in Lecture Hall 2 stopped working and it is extremely hot inside.", "Maintenance", "Medium"),
    ("Elevator in the Administration building is making grinding noise and jerking.", "Maintenance", "High"),
    ("Ceiling panel near the faculty lounge is sagging and about to fall down.", "Maintenance", "High"),
    ("Desks and chairs in Room 102 are damaged and unstable for students.", "Maintenance", "Low"),
    ("Staircase handrail near Block B exit is loose and wobbly.", "Maintenance", "Medium"),
    ("Whiteboard in Room 205 has fallen off its wall mounting.", "Maintenance", "Low"),
    ("The main door of the Chemistry department is jammed shut.", "Maintenance", "Medium"),
    ("Window shutter in the library study room cannot be opened or closed.", "Maintenance", "Low"),
    ("Tile flooring in the central corridor is broken causing tripping hazard.", "Maintenance", "Medium"),
    ("Blinds in Room 410 are broken and stuck in down position.", "Maintenance", "Low"),
    ("Exhaust fan in the chemistry laboratory is making loud screeching noise.", "Maintenance", "Medium"),
    ("The automatic glass sliding door at the entrance is stuck half open.", "Maintenance", "Medium"),
    ("Corridor walls in Block A have peeling paint and plaster debris on floor.", "Maintenance", "Low"),
    ("Door handle of the girls rest room on 3rd floor came off completely.", "Maintenance", "Low"),
    ("Benches in the campus courtyard are rusted and broken.", "Maintenance", "Low"),
    ("Lab desk drawer lock in Biology Lab is stuck and cannot open.", "Maintenance", "Low"),
    ("Metal shutter of the cafeteria storage room is off its track.", "Maintenance", "Medium"),
    ("Roof tiles near the chapel building are loose after the storm.", "Maintenance", "Medium"),
    ("Partition wall in Seminar Hall 1 is damaged.", "Maintenance", "Low"),

    # Safety Complaints
    ("There is smoke coming from an electrical panel near Block A ground floor.", "Safety", "Critical"),
    ("Fire extinguisher in the Chemistry lab is missing from its wall bracket.", "Safety", "High"),
    ("Emergency exit door in Block C is padlocked shut from inside.", "Safety", "Critical"),
    ("Someone spotted a stray dog behaving aggressively near the playground.", "Safety", "Medium"),
    ("Dark pathway behind the sports complex has no street lights working.", "Safety", "High"),
    ("Chemical spill of unknown liquid reported in Organic Chemistry Lab 3.", "Safety", "Critical"),
    ("Unidentified suspicious package left unattended near the main entrance.", "Safety", "Critical"),
    ("Bare live copper electrical wires exposed in hallway near Room 105.", "Safety", "Critical"),
    ("Security guard was absent from the East Gate post during night hours.", "Safety", "Medium"),
    ("Gas leak smell detected near the chemistry laboratory storage area.", "Safety", "Critical"),
    ("A student slipped on oil spill near the mechanical workshop entrance.", "Safety", "High"),
    ("CCTV security camera near the girl hostel entrance is disconnected.", "Safety", "High"),
    ("Fire alarm sensor is continuously beeping and false alarming in Block B.", "Safety", "Medium"),
    ("Unauthorized person without ID badge found wandering around student dorms.", "Safety", "High"),
    ("Glass bottle shattered across the main walking pathway near cafeteria.", "Safety", "Medium"),
    ("Construction debris with sharp rusty nails left exposed on walkway.", "Safety", "High"),
    ("Tree branch fell and is hanging precariously over the main pedestrian path.", "Safety", "High"),
    ("Smoke detector in Room 201 has been covered with plastic wrap.", "Safety", "High"),
    ("Panic button inside the elevator is not responding when pressed.", "Safety", "Critical"),
    ("Speeding vehicle seen inside campus pedestrian zone near cafeteria.", "Safety", "Medium"),
    ("Balcony railing on 4th floor Block C is loose and unsafe.", "Safety", "Critical"),

    # Academic Complaints
    ("My learning platform is not showing my courses and I have an exam tomorrow, please fix it urgently.", "Academic", "High"),
    ("Student learning portal is not loading enrolled subjects before tomorrow's final exam.", "Academic", "High"),
    ("Cannot access course materials on portal and exam starts in 2 hours.", "Academic", "High"),
    ("Midterm exam timetable has overlapping schedules for Computer Science subjects.", "Academic", "High"),
    ("Course syllabus for Data Structures has not been uploaded to portal.", "Academic", "Low"),
    ("Professor was absent for 30 minutes without prior notice for Math lecture.", "Academic", "Medium"),
    ("Grade transcript generated on portal has incorrect letter marks for Semester 4.", "Academic", "High"),
    ("Textbooks required for Physics 101 are out of stock in the library.", "Academic", "Low"),
    ("Lab manual for Microprocessors course has outdated exercise instructions.", "Academic", "Low"),
    ("Faculty evaluation form submission deadline is not working on student portal.", "Academic", "Medium"),
    ("Attendance record showing false absence for yesterday's lecture.", "Academic", "Medium"),
    ("Classroom capacity is 30 but 50 students registered for Machine Learning.", "Academic", "Medium"),
    ("No teaching assistant assigned for the weekly programming lab sessions.", "Academic", "Low"),
    ("Final exam hall allocation lists have conflicting room assignments.", "Academic", "High"),
    ("Request for course drop hasn't been processed by dean office for 2 weeks.", "Academic", "Medium"),
    ("Prerequisite requirement block preventing registration for elective course.", "Academic", "Medium"),
    ("Project supervisor assignments have not been published for senior thesis.", "Academic", "Low"),
    ("Lecture recording links on course page are corrupted and won't play.", "Academic", "Low"),
    ("Re-evaluation application form link is missing on the academic portal.", "Academic", "Medium"),
    ("Library quiet study area is noisy and staff is not enforcing silence.", "Academic", "Low"),
    ("Degree certificate name spelling is wrong on official transcript draft.", "Academic", "High"),
    ("Office hours schedule of Professor Davis is never updated.", "Academic", "Low"),
    ("Lab assignment deadline was extended without notifying all student sections.", "Academic", "Low"),

    # Administration Complaints
    ("Refund process for duplicate fee payment taking more than four weeks.", "Administration", "Medium"),
    ("Long queues at financial services window due to only 1 counter open.", "Administration", "Low"),
    ("Student ID card issuance counter is closed during working hours.", "Administration", "Low"),
    ("Official transcript request status stuck on pending for 15 days.", "Administration", "Medium"),
    ("Scholarship disbursement check has not been deposited into student account.", "Administration", "High"),
    ("Discipline committee letter sent with wrong student roll number.", "Administration", "Medium"),
    ("NOC document for internship application is pending approval for 3 weeks.", "Administration", "Medium"),
    ("Admin office staff was unhelpful and refused to clear clearance slip.", "Administration", "Low"),
    ("Hostel allotment list has errors in room numbers.", "Administration", "Medium"),
    ("Parking permit fee charged twice on my university account balance.", "Administration", "Medium"),
    ("Late fee penalty charged even though payment was completed before deadline.", "Administration", "High"),
    ("Medical insurance card was not delivered to international students.", "Administration", "Medium"),
    ("University helpdesk phone lines are constantly busy and unanswered.", "Administration", "Low"),
    ("Certificate verification portal is rejecting valid graduation documents.", "Administration", "High"),
    ("Dormitory security deposit refund has not been processed post-graduation.", "Administration", "Medium"),
    ("Bus pass counter staff misbehaved with students waiting in line.", "Administration", "Low"),
    ("Annual fee breakdown receipt missing itemized laboratory charges.", "Administration", "Low"),
    ("Course registration clearance hold not removed despite clearing dues.", "Administration", "High"),

    # Transport Complaints
    ("Campus shuttle bus route 2 arrived 40 minutes late this morning.", "Transport", "Medium"),
    ("Student shuttle bus driver was driving rashly near the campus gate.", "Transport", "High"),
    ("Air conditioning inside university bus number 5 is broken.", "Transport", "Low"),
    ("Not enough seating capacity on morning shuttle for off-campus hostelers.", "Transport", "Medium"),
    ("Campus parking lot B is overcrowded with unauthorized private vehicles.", "Transport", "Low"),
    ("Bicycle sharing dock near library has no working bikes available.", "Transport", "Low"),
    ("Bus stop shed roof is leaking water during rainy days.", "Transport", "Low"),
    ("University transport app is not updating live GPS location of buses.", "Transport", "Low"),
    ("Evening shuttle service was cancelled without any prior announcement.", "Transport", "Medium"),
    ("Traffic congestion at main gate entry due to broken automated boom barrier.", "Transport", "Medium"),
    ("Electric vehicle charging station near Block D is out of service.", "Transport", "Low"),
    ("Shuttle bus door closing mechanism caught student backpack.", "Transport", "High"),
    ("Parking ticket machine is taking money but not issuing parking ticket.", "Transport", "Low"),
    ("Driver of Bus 3 was using mobile phone while driving with students.", "Transport", "High"),
    ("Handicapped parking spaces near main building occupied by illegal cars.", "Transport", "Medium"),
    ("Night shuttle frequency is too low for students leaving library late.", "Transport", "Low"),

    # Facilities Complaints
    ("No water supply in the washrooms of Block B 2nd floor.", "Facilities", "High"),
    ("Study room in library has broken chairs and no working power outlets.", "Facilities", "Low"),
    ("Water cooler on 3rd floor near Room 301 is dispensing hot water.", "Facilities", "Low"),
    ("Student cafeteria indoor seating area is overcrowded and lacks ventilation.", "Facilities", "Low"),
    ("Gymnasium weight equipment cable is frayed and snapped during workout.", "Facilities", "High"),
    ("Badminton court floor mats are torn and causing slippery footing.", "Facilities", "Medium"),
    ("Auditorium air conditioning system is blowing warm air.", "Facilities", "Medium"),
    ("Vending machine in Block A ate coins without dispensing snack.", "Facilities", "Low"),
    ("Library study cubicle lamps are burnt out and dim.", "Facilities", "Low"),
    ("Swimming pool water appears cloudy and unhygienic.", "Facilities", "High"),
    ("Lockers in the sports complex male changing room have rusted latches.", "Facilities", "Low"),
    ("Microwave oven in faculty lunchroom is sparking and smoking.", "Facilities", "High"),
    ("Outdoor basketball court floodlights are turned off at night.", "Facilities", "Low"),
    ("Sanitary napkin dispenser in girls restroom is empty and jammed.", "Facilities", "Medium"),
    ("Drinking water fountain filter indicator shows red dirty water warning.", "Facilities", "High"),
    ("Student lounge sofa cushions are torn and filthy.", "Facilities", "Low"),

    # Cleanliness Complaints
    ("Restroom near the main cafeteria has not been cleaned since yesterday.", "Cleanliness", "Medium"),
    ("Trash cans near Block A entrance are overflowing with food food waste.", "Cleanliness", "Low"),
    ("Pigeon droppings present on corridor windows and desks in Block C.", "Cleanliness", "Low"),
    ("Dust and cobwebs accumulated all over the ceiling of Room 204.", "Cleanliness", "Low"),
    ("Cafeteria tables are covered in greasy food stains and spilled drinks.", "Cleanliness", "Medium"),
    ("Foul smell coming from garbage dump behind the student canteen.", "Cleanliness", "Medium"),
    ("Staircase steps in science Block floor 3 are covered in mud dirt.", "Cleanliness", "Low"),
    ("Restroom floor is flooded with dirty water and slippery soap residue.", "Cleanliness", "High"),
    ("Cockroaches seen roaming around inside the hostel dining hall.", "Cleanliness", "High"),
    ("Disinfected smell missing and biohazard waste box open in medical clinic.", "Cleanliness", "High"),
    ("Dustbin in Computer Lab 1 has not been emptied for three days.", "Cleanliness", "Low"),
    ("Mosquitoes breeding in stagnant puddle near the hostel garden area.", "Cleanliness", "High"),
    ("Black mold spots visible on bathroom walls in dorm building 2.", "Cleanliness", "Medium"),
    ("Used coffee cups left scattered on library study tables.", "Cleanliness", "Low"),
    ("Janitor left dirty mop and bucket blocking the corridor pathway.", "Cleanliness", "Low"),

    # Electrical Complaints
    ("Power outage in Block B wing left all classrooms without electricity.", "Electrical", "High"),
    ("Light bulbs in Room 302 are flickering continuously causing eye strain.", "Electrical", "Low"),
    ("Electrical wall socket in Room 104 sparked when plugging in laptop.", "Electrical", "High"),
    ("Circuit breaker tripped in Physics Lab 2 shutting off experimental equipment.", "Electrical", "Medium"),
    ("Ceiling fan in Room 205 is making loud wobbling noise and shaking.", "Electrical", "Medium"),
    ("Outdoor streetlight pole base near library has exposed active wiring.", "Electrical", "Critical"),
    ("UPS battery backup in computer server room is emitting loud alarm beep.", "Electrical", "High"),
    ("Wall switch board in chemistry lab is loose and hot to touch.", "Electrical", "High"),
    ("Voltage fluctuation damaged monitor screen in Room 401.", "Electrical", "Medium"),
    ("Main electrical distribution box in basement is leaking sparks.", "Electrical", "Critical"),
    ("Emergency backup lights failed to turn on during campus blackout.", "Electrical", "High"),
    ("Exhaust fan wire short circuited in cafeteria kitchen.", "Electrical", "High"),
    ("Extension cord provided in seminar room has burnt insulation.", "Electrical", "High"),
    ("Air conditioner compressor wire caught fire outside Block D wall.", "Electrical", "Critical"),
    ("Light fixtures in ground floor corridor are dead and pitch dark.", "Electrical", "Medium"),

    # Plumbing Complaints
    ("Water is leaking from the ceiling near cafeteria floor is very slippery.", "Plumbing", "High"),
    ("Washroom sink pipe in Block A 2nd floor is burst and spraying water.", "Plumbing", "High"),
    ("Toilet bowl in male restroom Room 102 is clogged and overflowing.", "Plumbing", "High"),
    ("No water pressure coming out of taps in chemical engineering lab.", "Plumbing", "Medium"),
    ("Drain pipe under library washroom sink is disconnected and leaking onto floor.", "Plumbing", "Medium"),
    ("Hot water system in student dorm showers is completely cold.", "Plumbing", "Low"),
    ("Flush tank mechanism in girls bathroom floor 1 is broken and constantly running.", "Plumbing", "Low"),
    ("Main water supply pipe near central garden burst open forming huge puddle.", "Plumbing", "High"),
    ("Rusty brown tap water coming out of drinking fountain near Block B.", "Plumbing", "High"),
    ("Shower drain in hostel room 304 is blocked causing water pooling.", "Plumbing", "Medium"),
    ("Water heater in residential quarter blew pipe gasket.", "Plumbing", "High"),
    ("Sewer odor coming out of floor drain in ground floor corridor.", "Plumbing", "Medium"),
    ("Leaking pipe in server room ceiling threatens electronics.", "Plumbing", "Critical"),
    ("Outdoor garden tap broken and wasting gallons of fresh water.", "Plumbing", "Medium"),
    ("Water tank on roof of Block C is overflowing down the building facade.", "Plumbing", "Medium"),

    # Other Complaints
    ("Lost black leather wallet containing student ID near library entrance.", "Other", "Low"),
    ("Found set of keys with blue keychain on bench near cafeteria.", "Other", "Low"),
    ("Lost silver laptop charger left in Lecture Hall 3 after 2 PM class.", "Other", "Low"),
    ("Campus cat was injured near parking lot and needs veterinary help.", "Other", "Medium"),
    ("Noisy construction work outside library during examination hours.", "Other", "Medium"),
    ("Requesting permission to organize blood donation camp in student center.", "Other", "Low"),
    ("Lost prescription eyeglasses in case near Block A staircase.", "Other", "Low"),
    ("Found unclaimed prescription jacket in Auditorium seat 12.", "Other", "Low"),
    ("Loud music played late at night from adjacent hostel building.", "Other", "Low"),
    ("Inquiry regarding lost and found office opening timings.", "Other", "Low"),
]

LOCATION_VARIANTS = [
    "in Room 204", "near Block A", "in Computer Lab 3", "near the main cafeteria",
    "in the Library study section", "in Block C 2nd floor", "at the Student Center",
    "near Lecture Hall 102", "in the Sports Complex", "in the Chemistry Building",
    "near the main entrance gate", "in Dormitory Block B", "in Room 305", "near the food court"
]

TIME_PHRASES = [
    "for the past two days", "since yesterday morning", "and someone almost fell",
    "causing major inconvenience to students", "and exam starts in 20 minutes",
    "please fix this immediately", "reported multiple times already", "since this afternoon",
    "it has been broken for three weeks", "during peak lecture hours"
]

def generate_dataset():
    """Generates synthetic dataset of university complaints."""
    data = []
    
    for text, cat, urg in COMPLAINT_TEMPLATES:
        data.append({"text": text, "category": cat, "urgency": urg})

    for text, cat, urg in COMPLAINT_TEMPLATES:
        time_phrase = random.choice(TIME_PHRASES)
        v1 = f"{text.rstrip('.')} {time_phrase}."
        data.append({"text": v1, "category": cat, "urgency": urg})
        
        if "Room" in text or "Block" in text or "Lab" in text:
            loc = random.choice(LOCATION_VARIANTS)
            v2 = f"{text.split('.')[0]} {loc}."
            data.append({"text": v2, "category": cat, "urgency": urg})

    df = pd.DataFrame(data)
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    df.to_csv(COMPLAINTS_CSV_PATH, index=False)
    print(f"Dataset successfully created at {COMPLAINTS_CSV_PATH}")
    print(f"Total samples: {len(df)}")
    return df

if __name__ == "__main__":
    generate_dataset()
