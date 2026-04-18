import os
import subprocess
import sqlite3
import pandas as pd
import anthropic
import streamlit as st

st.set_page_config(page_title="CampQuery", page_icon="🏕️")

if not os.path.exists("camp.db"):
    subprocess.run(["python", "data_setup.py"], check=True)

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

st.markdown("""
<style>
/* Buttons */
div[data-testid="stButton"] > button,
div[data-testid="stFormSubmitButton"] > button {
    background-color: #2D6A4F !important;
    color: white !important;
    border: none !important;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #F4A261 !important;
    color: white !important;
}

/* Dataframe header row */
[data-testid="stDataFrame"] th {
    background-color: #2D6A4F !important;
    color: white !important;
}

/* Sidebar section headers */
.cq-sidebar-header {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #2D6A4F;
    margin: 4px 0 10px 0;
}

/* Sidebar footer — inherits theme text color, muted via opacity */
.cq-sidebar-footer {
    font-size: 12px;
    color: inherit;
    opacity: 0.5;
    margin-top: 8px;
    line-height: 1.5;
}
</style>
""", unsafe_allow_html=True)


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


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "CampQuery demonstrates how natural language querying can make camp management data "
        "accessible to non-technical staff — directors, counselors, and operations teams who "
        "need answers fast without knowing SQL."
    )

    st.divider()

    st.markdown('<div class="cq-sidebar-header">About the Data</div>', unsafe_allow_html=True)
    st.markdown("📁 150 camps, 500 campers, 1,100 enrollment records")
    st.markdown(
        "🏕️ Camp schema modeled after the ACA Find a Camp directory (acacamps.org) — "
        "the largest database of accredited summer camps in the U.S."
    )
    st.markdown(
        "🔒 Camper records are fully synthetic. Real camper-level data is not publicly "
        "available due to youth privacy protections — this is standard practice in camp "
        "management software."
    )
    st.markdown(
        "📊 Data distributions reflect real-world camp patterns: 65% returning campers, "
        "18% scholarship recipients, 60% ACA-accredited camps"
    )

    st.divider()

    st.markdown('<div class="cq-sidebar-header">Why This Matters</div>', unsafe_allow_html=True)
    st.markdown("⏱️ Directors spend hours pulling reports manually — natural language querying eliminates that bottleneck")
    st.markdown("🎯 Non-technical staff get self-service access to data without SQL training")
    st.markdown("🔍 Instant answers to operational questions: waivers, rosters, attendance, re-enrollment risk")
    st.markdown("📈 Mirrors capabilities being built into modern camp management platforms like Campminder")

    st.divider()

    st.markdown('<div class="cq-sidebar-header">Built With</div>', unsafe_allow_html=True)
    st.markdown("🤖 Claude AI (Anthropic) — natural language to SQL")
    st.markdown("🐍 Python + Streamlit")
    st.markdown("🗄️ SQLite")
    st.markdown("📐 Schema reference: ACA Find a Camp directory")

    st.divider()

    st.markdown(
        '<div class="cq-sidebar-footer">Built by Nabil Abbas · github.com/nabilabbas250/campquery</div>',
        unsafe_allow_html=True,
    )

# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🏕️ CampQuery")
st.subheader("Ask your camp data anything — powered by Claude AI")
st.info("⚠️ All camper records are fully synthetic and do not represent any real individuals. Camp schema is modeled after the ACA Find a Camp directory.")

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
