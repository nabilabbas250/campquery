import sqlite3
import random
from datetime import date, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

DB_PATH = "camp.db"

STATES_WEIGHTED = (
    ["NY"] * 20 + ["NJ"] * 15 + ["PA"] * 15 + ["CT"] * 10 + ["MA"] * 10 +
    ["CA", "TX", "FL", "IL", "OH", "MI", "VA", "NC", "GA", "WA",
     "CO", "AZ", "MN", "WI", "MD", "TN", "IN", "MO", "OR", "SC"]
)

SPECIALTIES = ["Arts", "Sports", "STEM", "General", "Religious", "Special Needs"]

ACTIVITY_POOLS = {
    "Sports":        ["Soccer", "Basketball", "Swimming", "Archery", "Tennis", "Flag Football"],
    "Arts":          ["Drama", "Painting", "Music", "Dance", "Ceramics", "Film"],
    "STEM":          ["Robotics", "Coding", "Rocketry", "Nature Science", "Engineering"],
    "General":       ["Swimming", "Hiking", "Arts & Crafts", "Campfire Skills", "Canoeing"],
    "Religious":     ["Scripture Study", "Community Service", "Nature Hikes", "Sports"],
    "Special Needs": ["Adaptive Swimming", "Sensory Arts", "Life Skills", "Music Therapy"],
}


def generate_camps(n=150):
    camps = []
    for i in range(1, n + 1):
        specialty = random.choice(SPECIALTIES)
        age_min = random.randint(5, 10)
        age_max = random.randint(age_min + 3, 18)
        camps.append({
            "camp_id": i,
            "camp_name": fake.company().replace(",", "") + " Camp",
            "camp_type": random.choices(["Day", "Overnight", "Both"], weights=[30, 45, 25])[0],
            "state": random.choice(STATES_WEIGHTED),
            "city": fake.city(),
            "zip_code": fake.zipcode(),
            "age_min": age_min,
            "age_max": age_max,
            "gender_focus": random.choices(["Coed", "Boys", "Girls"], weights=[70, 15, 15])[0],
            "specialty": specialty,
            "capacity": random.randint(50, 400),
            "is_accredited": random.choices([1, 0], weights=[60, 40])[0],
            "weekly_cost": round(random.uniform(500, 4000), 2),
            "founded_year": random.randint(1950, 2010),
        })
    return camps


def generate_campers(camps, n=500):
    camp_map = {c["camp_id"]: c for c in camps}
    camp_ids = [c["camp_id"] for c in camps]
    campers = []
    for i in range(1, n + 1):
        camp_id = random.choice(camp_ids)
        camp = camp_map[camp_id]
        age = random.randint(camp["age_min"], camp["age_max"])
        gender_focus = camp["gender_focus"]
        if gender_focus == "Boys":
            gender = "Male"
        elif gender_focus == "Girls":
            gender = "Female"
        else:
            gender = random.choice(["Male", "Female"])
        campers.append({
            "camper_id": i,
            "camp_id": camp_id,
            "first_name": fake.first_name_male() if gender == "Male" else fake.first_name_female(),
            "last_name": fake.last_name(),
            "age": age,
            "gender": gender,
            "home_state": random.choice(STATES_WEIGHTED),
            "session_year": random.choices([2022, 2023, 2024], weights=[25, 35, 40])[0],
            "returning_camper": random.choices([1, 0], weights=[65, 35])[0],
            "scholarship_recipient": random.choices([1, 0], weights=[18, 82])[0],
            "medical_flag": random.choices([1, 0], weights=[14, 86])[0],
            "waiver_signed": random.choices([1, 0], weights=[91, 9])[0],
            "cabin": f"Cabin {random.randint(1, 10)}",
        })
    return campers


def session_start_for_year(year):
    # June or July start
    month = random.choice([6, 7])
    day = random.randint(1, 28)
    return date(year, month, day)


def generate_enrollments(campers, camps, n=1100):
    camp_map = {c["camp_id"]: c for c in camps}
    camper_map = {c["camper_id"]: c for c in campers}
    camper_ids = [c["camper_id"] for c in campers]
    enrollments = []
    for i in range(1, n + 1):
        camper = camper_map[random.choice(camper_ids)]
        camp = camp_map[camper["camp_id"]]
        specialty = camp["specialty"]
        activity = random.choice(ACTIVITY_POOLS[specialty])
        year = camper["session_year"]
        start = session_start_for_year(year)
        end = start + timedelta(weeks=random.randint(4, 8))
        attendance_rate = round(random.uniform(0.5, 1.0), 3)
        completed = 1 if attendance_rate > 0.75 else 0
        re_enrolled = 1 if (attendance_rate > 0.80 and camper["returning_camper"] == 1) else 0
        enrollments.append({
            "enrollment_id": i,
            "camper_id": camper["camper_id"],
            "camp_id": camper["camp_id"],
            "activity": activity,
            "session_start": start.isoformat(),
            "session_end": end.isoformat(),
            "attendance_rate": attendance_rate,
            "completed": completed,
            "counselor_rating": random.randint(1, 5),
            "re_enrolled_next_year": re_enrolled,
        })
    return enrollments


def create_tables(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS enrollments;
        DROP TABLE IF EXISTS campers;
        DROP TABLE IF EXISTS camps;

        CREATE TABLE camps (
            camp_id       INTEGER PRIMARY KEY,
            camp_name     TEXT,
            camp_type     TEXT,
            state         TEXT,
            city          TEXT,
            zip_code      TEXT,
            age_min       INTEGER,
            age_max       INTEGER,
            gender_focus  TEXT,
            specialty     TEXT,
            capacity      INTEGER,
            is_accredited INTEGER,
            weekly_cost   REAL,
            founded_year  INTEGER
        );

        CREATE TABLE campers (
            camper_id           INTEGER PRIMARY KEY,
            camp_id             INTEGER REFERENCES camps(camp_id),
            first_name          TEXT,
            last_name           TEXT,
            age                 INTEGER,
            gender              TEXT,
            home_state          TEXT,
            session_year        INTEGER,
            returning_camper    INTEGER,
            scholarship_recipient INTEGER,
            medical_flag        INTEGER,
            waiver_signed       INTEGER,
            cabin               TEXT
        );

        CREATE TABLE enrollments (
            enrollment_id       INTEGER PRIMARY KEY,
            camper_id           INTEGER REFERENCES campers(camper_id),
            camp_id             INTEGER REFERENCES camps(camp_id),
            activity            TEXT,
            session_start       TEXT,
            session_end         TEXT,
            attendance_rate     REAL,
            completed           INTEGER,
            counselor_rating    INTEGER,
            re_enrolled_next_year INTEGER
        );
    """)


def insert_rows(conn, table, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in keys)
    cols = ", ".join(keys)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(r[k] for k in keys) for r in rows])


def main():
    camps = generate_camps(150)
    campers = generate_campers(camps, 500)
    enrollments = generate_enrollments(campers, camps, 1100)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    insert_rows(conn, "camps", camps)
    insert_rows(conn, "campers", campers)
    insert_rows(conn, "enrollments", enrollments)
    conn.commit()
    conn.close()

    print("Database created:", DB_PATH)
    print(f"  camps       → {len(camps):>5} rows")
    print(f"  campers     → {len(campers):>5} rows")
    print(f"  enrollments → {len(enrollments):>5} rows")


main()
