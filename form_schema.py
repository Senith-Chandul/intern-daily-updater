"""
Google Form Schema and Entry IDs for:
Daily Intern Progress Update: LeapGen IIT Accelerator
Form URL: https://docs.google.com/forms/d/e/1FAIpQLSclwYWri8MXXTa9wHDyn3fuBopn33F-eyi_Oi2aF7WUJCRE_g/viewform
"""

FORM_VIEW_URL = "https://docs.google.com/forms/d/e/1FAIpQLSclwYWri8MXXTa9wHDyn3fuBopn33F-eyi_Oi2aF7WUJCRE_g/viewform"
FORM_SUBMIT_URL = "https://docs.google.com/forms/d/e/1FAIpQLSclwYWri8MXXTa9wHDyn3fuBopn33F-eyi_Oi2aF7WUJCRE_g/formResponse"

STARTUP_OPTIONS = [
    "Yamu Car Rentals",
    "Trivista Labs",
    "The Astryd Labs",
    "QuickBrix",
    "Axacrate Technologies",
    "Alertrix",
    "Dectave",
    "Clovio",
]

INTERN_NAMES = [
    "Vihanga Randima",
    "Danuka Dulanjan",
    "Yasira Asanjith",
    "Esala Gamage",
    "Umesh Isuranga",
    "Dulaj Yuthsara Jayasingha",
    "Vihara Senanayake",
    "Jalitha Tharindu de Silva",
    "Venuja Ransika",
    "Waseem Kaleel",
    "Chanith Thewnaka",
    "B A Daniru R Senarathne",
    "Sevin Kawsika",
    "Thivina Hettiaraachchi",
    "Bhadrash Chandramohan",
    "Sashrika Vidanagama",
    "Punsara Rajapaksa",
    "Senith Sagarage",
]

TASK_STATUS_OPTIONS = [
    "Not started",
    "In progress",
    "Completed",
]

CONTINUATION_OPTIONS = [
    "Yes",
    "No",
]

# Google Form Entry Mapping
ENTRIES = {
    # Email
    "email": "emailAddress",

    # Basic Info
    "startup_name": "entry.1157714591",
    "intern_name": "entry.301083567",
    "designation": "entry.2111390916",

    # Date components (submitted as year, month, day)
    "today_date": "entry.460983191",

    # Tasks
    "tasks_yesterday": "entry.1620462389",
    "tasks_today": "entry.396642985",

    # Continuation of previous task (Tasks 1 to 4)
    "continuation": {
        1: "entry.1937633194",
        2: "entry.901296339",
        3: "entry.1309620659",
        4: "entry.1991070496",
    },

    # Task Status today (Tasks 1 to 4)
    "status": {
        1: "entry.660495431",
        2: "entry.874995830",
        3: "entry.1355718802",
        4: "entry.474599095",
    },

    # Time spent on today's task in hours (Tasks 1 to 4)
    "time_spent": {
        1: "entry.256173977",
        2: "entry.849628567",
        3: "entry.1133223653",
        4: "entry.1246716996",
    },

    # Completion date of today's task (Tasks 1 to 4)
    "completion_date": {
        1: "entry.1696734376",
        2: "entry.788445200",
        3: "entry.862690682",
        4: "entry.604676135",
    },

    # Problems/challenges faced
    "challenges": "entry.349978638",
}
