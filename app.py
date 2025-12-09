import streamlit as st
import re
import pandas as pd
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Safety Assistant", page_icon="🚗", layout="centered")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { margin-top: -80px; }
    div.stChatInput { padding-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# NAME OF YOUR GOOGLE SHEET
SHEET_NAME = "Safety_Reports"

# --- 2. CONSTANTS ---
USER_FIELDS = [
    "Timestamp", "Make", "Model", "Model_Year", "VIN", "City", "State",
    "Speed", "Crash", "Fire", "Injured", "Deaths", "Description",

    # NEW FIELDS YOU REQUESTED
    "Component", "Mileage", "Technician_Notes",
    "Brake_Condition", "Engine_Temperature", "Date_Complaint",

    # UEBA FIELDS
    "Input_Length", "Suspicion_Score", "User_Risk_Level"
]

QUESTIONS = {
    "Make": "What is the vehicle brand? (e.g., Ford, Toyota)",
    "Model": "Which model is it? (e.g., Camry, Civic)",
    "Model_Year": "What is the model year? (e.g., 2022)",
    "VIN": "Do you have the VIN? (17 characters, or type 'skip')",
    "City": "Which city did this happen in?",
    "State": "Which state? (2 letter code like CA, NY)",
    "Speed": "How fast was the vehicle going? (e.g., 65 mph)",
    "Crash": "Was there a crash? (Yes/No)",
    "Fire": "Was there a fire? (Yes/No)",
    "Injured": "Were there any injuries? (Enter number)",
    "Deaths": "Were there any fatalities? (Enter number)",
    "Description": "Please describe exactly what happened.",

    # NEW QUESTIONS
    "Component": "Which component failed? (brakes, engine, transmission, etc.)",
    "Mileage": "What was the mileage at the time?",
    "Technician_Notes": "Any notes from a technician or mechanic?",
    "Brake_Condition": "How were the brakes? (Good / Worn / Failed)",
    "Engine_Temperature": "Engine temperature (if known)?",
    "Date_Complaint": "When did this issue occur? (YYYY-MM-DD)",

    # UEBA QUESTIONS ARE AUTO-CALCULATED → no user input
}

KNOWN_MAKES = {
    "FORD", "TOYOTA", "HONDA", "CHEVROLET", "TESLA", "BMW", "MERCEDES",
    "NISSAN", "HYUNDAI", "KIA", "VOLVO", "AUDI", "VOLKSWAGEN", "JEEP",
    "DODGE", "SUBARU", "MAZDA", "LEXUS", "ACURA", "INFINITI", "CADILLAC", "GMC"
}

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS",
    "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY",
    "NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
    "WI","WY","DC"
}

# --- UEBA FUNCTION ---
def analyze_user_behavior(text):
    score = 0
    length = len(text)

    # Short or extremely long messages
    if length < 5: score += 2
    if length > 500: score += 3

    # Excessive uppercase
    if text.isupper(): score += 2

    # Spam / repeated characters
    if re.search(r"(.)\\1{5,}", text): score += 3

    # Contradictions
    if ("no crash" in text.lower() and "accident" in text.lower()):
        score += 3

    # Profanity detection (simple)
    bad_words = ["fuck", "shit", "bitch", "crap"]
    if any(b in text.lower() for b in bad_words):
        score += 3

    # Risk level
    if score <= 2:
        risk = "LOW"
    elif score <= 5:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    return length, score, risk


# --- SAVE TO GOOGLE SHEETS ---
def save_to_google_sheet(record):
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )

        client = gspread.authorize(credentials)
        sheet = client.open(SHEET_NAME).sheet1

        row_data = [str(record[field]) if record[field] is not None else "" for field in USER_FIELDS]
        sheet.append_row(row_data)

        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False


# --- 4. BOT LOGIC ---
class SafetyBot:
    @staticmethod
    def get_next_question(record):
        for field in USER_FIELDS:
            if field == "Timestamp": continue
            if field in ["Input_Length", "Suspicion_Score", "User_Risk_Level"]:
                continue
            if record[field] is None:
                return field, QUESTIONS[field]
        return None, None

    @staticmethod
    def is_greeting(text):
        greetings = ["hi", "hello", "hey", "hola", "sup", "start", "yo", "good morning"]
        return text.lower().strip() in greetings

    @staticmethod
    def extract_data(text, record, current_field):
        clean_text = text.strip()
        upper_text = clean_text.upper()
        updates = {}

        # Auto-detect year
        year_match = re.search(r"\\b(19[89]\\d|20[0-2]\\d)\\b", text)
        if year_match and not record["Model_Year"]:
            updates["Model_Year"] = year_match.group(1)

        # Detect state
        for state in US_STATES:
            if clean_text.upper() == state or f" {state}" in upper_text:
                if not record["State"]:
                    updates["State"] = state

        # Detect make
        for make in KNOWN_MAKES:
            if make in upper_text and not record["Make"]:
                updates["Make"] = make.title()

        # Crash / Fire detection
        if not record["Crash"]:
            if "CRASH" in upper_text or "ACCIDENT" in upper_text:
                updates["Crash"] = "YES"
        if not record["Fire"]:
            if "FIRE" in upper_text or "SMOKE" in upper_text:
                updates["Fire"] = "YES"

        # Direct mapping
        if current_field and current_field not in updates:
            val = clean_text
            if val.lower() == "skip":
                updates[current_field] = "N/A"
            elif current_field in ["Crash", "Fire"]:
                updates[current_field] = "YES" if val.lower() in ["yes","y","yeah"] else "NO"
            elif current_field == "State":
                if len(val) == 2 and val.upper() in US_STATES:
                    updates[current_field] = val.upper()
            else:
                updates[current_field] = val

        return updates


# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 **Safety Assistant Online.**\n\nTell me what happened."
    }]

if "record" not in st.session_state:
    st.session_state.record = {k: None for k in USER_FIELDS}

if "finished" not in st.session_state:
    st.session_state.finished = False


# --- UI ---
st.title("🚗 Safety Assistant")
st.markdown("---")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# --- INPUT ---
if prompt := st.chat_input("Type here..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not st.session_state.finished:
        with st.spinner("Processing..."):
            time.sleep(0.3)
            current_missing, _ = SafetyBot.get_next_question(st.session_state.record)

            # Greeting
            if SafetyBot.is_greeting(prompt):
                response = "Hello! Please describe the incident."
            else:
                # UEBA analysis
                length, score, risk = analyze_user_behavior(prompt)
                st.session_state.record["Input_Length"] = length
                st.session_state.record["Suspicion_Score"] = score
                st.session_state.record["User_Risk_Level"] = risk

                # Extract data
                new_data = SafetyBot.extract_data(prompt, st.session_state.record, current_missing)

                if new_data:
                    for k, v in new_data.items():
                        st.session_state.record[k] = v

                    next_field, next_question = SafetyBot.get_next_question(st.session_state.record)

                    if next_field:
                        response = f"Recorded **{', '.join(new_data.keys())}**.\n\n{next_question}"
                    else:
                        st.session_state.finished = True
                        st.session_state.record["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        with st.spinner("Saving to cloud..."):
                            success = save_to_google_sheet(st.session_state.record)

                        response = "✅ **Report saved successfully!**" if success else "⚠️ Error while saving."

                else:
                    response = f"I didn't catch that. {QUESTIONS[current_missing]}"

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

        if st.session_state.finished:
            st.rerun()


# --- SUMMARY ---
if st.session_state.finished:
    st.divider()
    st.success("Report Submitted!")

    if st.button("Start New Report"):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 New report — tell me what happened."
        }]
        st.session_state.record = {k: None for k in USER_FIELDS}
        st.session_state.finished = False
        st.rerun()
