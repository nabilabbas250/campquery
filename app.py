import sqlite3
import pandas as pd
import anthropic
import streamlit as st

DB_PATH = "camp.db"

SYSTEM_PROMPT = """You are a SQL expert. Given a SQLite database with these tables:
camps(camp_id, camp_name, camp_type, state, city, zip_code, age_min, age_max, gender_focus, specialty, capacity, is_accredited, weekly_cost, founded_year)
campers(camper_id, camp_id, first_name, last_name, age, gender, home_state, session_year, returning_camper, scholarship_recipient, medical_flag, waiver_signed, cabin)
enrollments(enrollment_id, camper_id, camp_id, activity, session_start, session_end, attendance_rate, completed, counselor_rating, re_enrolled_next_year)
Return ONLY a valid SQLite SELECT query. No explanation, no markdown, no backticks. Just the SQL."""

EXAMPLE_QUERIES = [
    "Which campers haven't signed their waiver?",
    "Show me all returning campers in New York",
    "Which activities have the highest attendance rates?",
    "How many scholarship recipients enrolled in 2024?",
    "Which camp specialties have the highest re-enrollment rates?",
    "Show campers with a medical flag enrolled in Swimming",
    "Which states send the most campers to accredited camps?",
    "Show campers at risk of not returning — low attendance, first year",
]


def run_query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df


def ask_claude(question: str) -> str:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    return message.content[0].text.strip()


def handle_question(question: str):
    if not question.strip():
        return

    with st.spinner("Generating SQL and running query..."):
        try:
            sql = ask_claude(question)
        except Exception as e:
            st.error(f"Claude API error: {e}")
            return

        try:
            df = run_query(sql)
        except Exception:
            st.warning("I couldn't generate a valid query for that question. Try rephrasing it.")
            with st.expander("View generated SQL"):
                st.code(sql, language="sql")
            return

    st.dataframe(df, use_container_width=True)
    with st.expander("View generated SQL"):
        st.code(sql, language="sql")


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("CampQuery")
st.subheader("Ask your camp data anything — powered by Claude AI")
st.caption("Camp schema modeled after ACA Find a Camp directory | Camper records are synthetic")

st.divider()

# Example query buttons — two rows of 4
for row_start in [0, 4]:
    cols = st.columns(4)
    for col, label in zip(cols, EXAMPLE_QUERIES[row_start:row_start + 4]):
        if col.button(label, use_container_width=True):
            handle_question(label)

st.divider()

# Free-text input
with st.form("query_form", clear_on_submit=False):
    question = st.text_input(
        "Ask a question about your campers, activities, or programs...",
        placeholder="e.g. Which camps in New Jersey have availability for teenagers?",
    )
    submitted = st.form_submit_button("Ask", type="primary")

if submitted:
    handle_question(question)
