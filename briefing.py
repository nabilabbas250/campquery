import os
import sqlite3
from datetime import date
import pandas as pd
import anthropic
import streamlit as st

st.set_page_config(
    page_title="Camp Director Briefing",
    page_icon="☀️",
    layout="centered",
)

if not os.path.exists("camp.db"):
    import data_setup

# ── SQL queries (stored as constants for display + execution) ─────────────────

CAMP_SQL_A = """
SELECT ca.camp_name, ca.specialty, ca.state,
  ca.capacity, ca.is_accredited,
  COUNT(c.camper_id) as enrolled,
  SUM(CASE WHEN c.waiver_signed = 0 THEN 1 ELSE 0 END) as unsigned_waivers,
  SUM(CASE WHEN c.medical_flag = 1 THEN 1 ELSE 0 END)  as medical_flags,
  ROUND(AVG(e.attendance_rate) * 100) as avg_attendance
FROM camps ca
JOIN campers c ON ca.camp_id = c.camp_id
JOIN enrollments e ON c.camper_id = e.camper_id
WHERE ca.camp_id = ?
GROUP BY ca.camp_id
""".strip()

CAMP_SQL_B = """
SELECT c.first_name, c.last_name, c.cabin,
  c.waiver_signed, c.medical_flag,
  ROUND(e.attendance_rate * 100) as attendance_pct,
  e.activity
FROM campers c
JOIN enrollments e ON c.camper_id = e.camper_id
WHERE c.camp_id = ?
AND (c.waiver_signed = 0
  OR (c.medical_flag = 1 AND e.activity IN ('Swimming','Archery','Canoeing'))
  OR e.attendance_rate < 0.70)
ORDER BY e.attendance_rate ASC
LIMIT 10
""".strip()

CAMP_SQL_C = """
SELECT c.first_name, c.last_name, c.cabin,
  ROUND(e.attendance_rate * 100) as attendance_pct,
  e.re_enrolled_next_year
FROM campers c
JOIN enrollments e ON c.camper_id = e.camper_id
WHERE c.camp_id = ?
AND c.returning_camper = 0
AND e.attendance_rate < 0.75
LIMIT 8
""".strip()

CAMP_SQL_D = """
SELECT e.activity,
  ROUND(AVG(e.attendance_rate) * 100) as avg_attendance,
  COUNT(*) as enrollment_count
FROM enrollments e
WHERE e.camp_id = ?
GROUP BY e.activity
ORDER BY avg_attendance DESC
""".strip()

# ── CSS ───────────────────────────────────────────────────────────────────────

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

/* Footer */
.cq-footer {
    text-align: center;
    font-size: 12px;
    opacity: 0.4;
    color: inherit;
    padding: 28px 0 12px 0;
    margin-top: 32px;
    border-top: 1px solid rgba(128,128,128,0.2);
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = sqlite3.connect("camp.db")
    try:
        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()
    return df


def ask_claude(system: str, user: str) -> str:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split a markdown response into (header, body) pairs."""
    sections = []
    current_header = ""
    current_lines = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if current_header or current_lines:
                sections.append((current_header, "\n".join(current_lines).strip()))
            current_header = line
            current_lines = []
        else:
            current_lines.append(line)
    if current_header or current_lines:
        sections.append((current_header, "\n".join(current_lines).strip()))
    return sections


def disagree_toggle(key: str):
    """Render a subtle 'disagree' expander after a briefing section."""
    with st.expander("↩ Disagree with this assessment?"):
        st.markdown(
            '<span style="font-size:13px;opacity:0.7;">'
            "What did we get wrong? Your feedback helps improve future briefings."
            "</span>",
            unsafe_allow_html=True,
        )
        submitted_key = f"{key}_submitted"
        if st.session_state.get(submitted_key):
            st.markdown(
                '<span style="color:#2D6A4F;font-size:13px;font-weight:600;">'
                "✓ Noted. Thank you for the context."
                "</span>",
                unsafe_allow_html=True,
            )
        else:
            st.text_area(
                "Feedback",
                placeholder="e.g. Michele's attendance is low because she switched activities last week, not disengaged...",
                label_visibility="collapsed",
                key=f"{key}_text",
            )
            if st.button("Submit feedback", key=f"{key}_btn"):
                st.session_state[submitted_key] = True
                st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────

today = date.today().strftime("%A, %B %-d %Y")

st.title("☀️ Camp Director Daily Briefing")

st.markdown("""
<p style="font-size: 18px; line-height: 1.7;
color: inherit; max-width: 750px;">
AI-powered briefings that surface what needs attention —
no SQL, no dashboards, no manual report pulling. Select a
camp, generate a briefing, and see how Claude reads live
operational data to give directors a proactive,
data-backed daily summary.
</p>
""", unsafe_allow_html=True)

st.info(
    "⚠️ All camper records are fully synthetic and do not represent any real individuals. "
    "Camp schema is modeled after the ACA Find a Camp directory."
)

st.caption(today)

st.markdown(
    '<hr style="height:2px;background:linear-gradient(to right,#2D6A4F,#95D5B2,transparent);border:none;margin:8px 0 24px 0;">',
    unsafe_allow_html=True,
)

# ── Camp selector ─────────────────────────────────────────────────────────────

DISAGREE_SECTIONS = {"## Action Required Today", "## Campers to Check In With", "## Director's Priority"}

try:
    camps_df = run_query(
        "SELECT camp_id, camp_name, state, specialty FROM camps ORDER BY camp_name"
    )
    camp_options = {
        f"{row.camp_name} ({row.state} · {row.specialty})": row.camp_id
        for row in camps_df.itertuples()
    }

    selected_label = st.selectbox(
        "Camp",
        options=list(camp_options.keys()),
        label_visibility="collapsed",
    )
    selected_camp_id = camp_options[selected_label]
    selected_camp_name = selected_label.split(" (")[0]

    generate = st.button("Generate Camp Briefing →")

    if generate:
        TIER2_SYSTEM = f"""You are a chief of staff writing a morning briefing for \
the director of a single summer camp. Be specific, warm, and action-oriented. \
Use first names when referencing campers.

Ground every assessment in specific data points from the queries — attendance \
percentages, cabin numbers, first names, activity names. Never make a claim \
without a number behind it.

Structure with exactly these markdown headers:

## {selected_camp_name} — Morning Briefing
One sentence camp status summary.

## Action Required Today
Specific names, cabin numbers, and what needs to happen. Prioritized — most urgent first.

## Campers to Check In With
2-4 specific campers worth a personal conversation today and why. Use first names.

## Activity Pulse
One sentence on strongest and weakest activity with specific attendance percentages.

## Director's Priority
One sentence. The single most important thing to do before lunch today.

Keep under 300 words. Be a trusted advisor, not a report generator."""

        try:
            df_camp_a = run_query(CAMP_SQL_A, (selected_camp_id,))
            df_camp_b = run_query(CAMP_SQL_B, (selected_camp_id,))
            df_camp_c = run_query(CAMP_SQL_C, (selected_camp_id,))
            df_camp_d = run_query(CAMP_SQL_D, (selected_camp_id,))

            camp_context = f"""
Camp summary:
{df_camp_a.to_string(index=False)}

Campers needing action (unsigned waivers, medical flags in risky activities, low attendance):
{df_camp_b.to_string(index=False) if not df_camp_b.empty else "None flagged."}

At-risk campers (first-year, attendance below 75%):
{df_camp_c.to_string(index=False) if not df_camp_c.empty else "None flagged."}

Activity performance:
{df_camp_d.to_string(index=False) if not df_camp_d.empty else "No activity data."}
"""

            with st.spinner(f"Generating briefing for {selected_camp_name}..."):
                briefing_text = ask_claude(TIER2_SYSTEM, camp_context)

            # Render section by section, injecting disagree toggles
            sections = split_sections(briefing_text)
            for header, body in sections:
                if header:
                    st.markdown(header)
                if body:
                    st.markdown(body)
                if header in DISAGREE_SECTIONS:
                    section_key = f"{selected_camp_id}_{header.replace(' ', '_')}"
                    disagree_toggle(section_key)

            # Data expander
            with st.expander("📊 View data powering this briefing"):
                st.markdown("**Queries run against camp.db**")

                st.markdown("Camp summary")
                st.code(CAMP_SQL_A, language="sql")
                st.markdown("Campers needing action")
                st.code(CAMP_SQL_B, language="sql")
                st.markdown("At-risk campers")
                st.code(CAMP_SQL_C, language="sql")
                st.markdown("Activity performance")
                st.code(CAMP_SQL_D, language="sql")

                st.markdown("---")

                st.markdown("**Camp summary**")
                st.dataframe(df_camp_a, use_container_width=True)
                st.markdown("**Campers needing action**")
                st.dataframe(df_camp_b, use_container_width=True)
                st.markdown("**At-risk campers**")
                st.dataframe(df_camp_c, use_container_width=True)
                st.markdown("**Activity performance**")
                st.dataframe(df_camp_d, use_container_width=True)

                st.markdown(
                    "*Briefing generated by Claude claude-sonnet-4-5 using the above queries "
                    "against camp.db · Schema modeled after ACA Find a Camp directory*"
                )

        except Exception as e:
            st.error(f"Error: {str(e)}")

except Exception as e:
    st.error(f"Error: {str(e)}")

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="cq-footer">'
    "Built with Claude AI · Schema modeled after ACA Find a Camp · "
    "Synthetic records · github.com/nabilabbas250/campquery"
    "</div>",
    unsafe_allow_html=True,
)
