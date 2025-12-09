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

# NAME OF YOUR GOOGLE SHEET (Must match exactly)
SHEET_NAME = "Safety_Reports"

# --- 2. CONSTANTS ---
USER_FIELDS = [
    "Timestamp", "Make", "Model", "Model_Year", "VIN", "City", "State",
    "Speed", "Crash", "Fire", "Injured", "Deaths", "Description"
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
    "Description": "Please describe exactly what happened."
}

KNOWN_MAKES = {
    "FORD", "TOYOTA", "HONDA", "CHEVROLET", "TESLA", "BMW", "MERCEDES", 
    "NISSAN", "HYUNDAI", "KIA", "VOLVO", "AUDI", "VOLKSWAGEN", "JEEP", 
    "DODGE", "SUBARU", "MAZDA", "LEXUS", "ACURA", "INFINITI", "CADILLAC", "GMC"
}

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", 
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", 
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", 
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", 
    "WI", "WY", "DC"
}

# --- 3. GOOGLE SHEETS FUNCTION ---
def save_to_google_sheet(record):
    """
    Connects to Google Sheets and appends the record as a new row.
    """
    try:
        # Define the scope
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Authenticate using secrets
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )
        
        client = gspread.authorize(credentials)
        
        # Open the sheet
        # Make sure you have created a sheet with this EXACT name 
        # and shared it with the client_email from your JSON file
        sheet = client.open(SHEET_NAME).sheet1 
        
        # Prepare the row data in the correct order
        row_data = [str(record[field]) if record[field] is not None else "" for field in USER_FIELDS]
        
        # Append the row
        sheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

# --- 4. BOT LOGIC ---
class SafetyBot:
    @staticmethod
    def get_next_question(record):
        # Skip Timestamp, look for next None field
        for field in USER_FIELDS:
            if field == "Timestamp": continue
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
        
        # --- SMART SCAN ---
        year_match = re.search(r"\b(19[89]\d|20[0-2]\d)\b", text)
        if year_match and not record["Model_Year"]: updates["Model_Year"] = year_match.group(1)

        for state in US_STATES:
            is_standalone = clean_text.upper() == state
            is_in_text = f" IN {state}" in upper_text or f", {state}" in upper_text
            if (is_standalone or is_in_text) and not record["State"]:
                updates["State"] = state

        for make in KNOWN_MAKES:
            if make in upper_text and not record["Make"]:
                updates["Make"] = make.title()

        if not record["Crash"]:
            if "CRASH" in upper_text or "ACCIDENT" in upper_text: updates["Crash"] = "YES"
        if not record["Fire"]:
            if "FIRE" in upper_text or "SMOKE" in upper_text: updates["Fire"] = "YES"

        # --- DIRECT ANSWER ---
        if current_field and current_field not in updates:
            val = clean_text
            if val.lower() == "skip":
                updates[current_field] = "N/A"
            elif current_field in ["Crash", "Fire"]:
                updates[current_field] = "YES" if val.lower() in ["yes", "y", "yeah"] else "NO"
            elif current_field == "Make":
                if not SafetyBot.is_greeting(val): updates[current_field] = val.title()
            elif current_field == "State":
                if len(val) == 2 and val.upper() in US_STATES: updates[current_field] = val.upper()
            else:
                updates[current_field] = val

        return updates

# --- 5. STATE MANAGEMENT ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 **Safety Assistant Online.**\n\nI can help you file a report. Just tell me what happened in your own words."}]
if "record" not in st.session_state:
    st.session_state.record = {k: None for k in USER_FIELDS}
if "finished" not in st.session_state:
    st.session_state.finished = False

# --- 6. APP LAYOUT ---
st.title("🚗 Safety Assistant")
st.markdown("---")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle Input
if prompt := st.chat_input("Type here..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not st.session_state.finished:
        with st.spinner("Thinking..."):
            time.sleep(0.4)
            current_missing, _ = SafetyBot.get_next_question(st.session_state.record)

            if SafetyBot.is_greeting(prompt):
                response = "Hello! Please describe the incident. For example: *'My 2020 Ford crashed in CA'*."
            else:
                new_data = SafetyBot.extract_data(prompt, st.session_state.record, current_missing)
                
                if new_data:
                    for k, v in new_data.items():
                        st.session_state.record[k] = v
                    
                    next_field, next_question = SafetyBot.get_next_question(st.session_state.record)
                    
                    if next_field:
                        # Continue flow
                        found_list = [k for k in new_data.keys()]
                        intro = f"Got it, recorded: **{', '.join(found_list)}**.\n\n" if len(found_list) > 1 or (len(found_list) == 1 and found_list[0] != current_missing) else ""
                        response = f"{intro}{next_question}"
                    else:
                        # --- FINISH & SAVE ---
                        st.session_state.finished = True
                        
                        # Add timestamp
                        st.session_state.record["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # SAVE TO GOOGLE SHEETS
                        with st.spinner("Saving report to cloud database..."):
                            success = save_to_google_sheet(st.session_state.record)
                        
                        if success:
                            response = "✅ **All done! Your report has been securely saved to the cloud.**"
                        else:
                            response = "⚠️ **Error saving report.** Please check the connection."
                else:
                    response = f"I didn't catch that. {QUESTIONS[current_missing]}" if current_missing else "Could you provide more details?"

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
        
        if st.session_state.finished:
            st.rerun()

# --- 7. FINAL SUMMARY ---
if st.session_state.finished:
    st.divider()
    st.success("Report Submitted Successfully")
    
    if st.button("Start New Report"):
        st.session_state.messages = [{"role": "assistant", "content": "👋 Ready for a new report. What happened?"}]
        st.session_state.record = {k: None for k in USER_FIELDS}
        st.session_state.finished = False
        st.rerun()