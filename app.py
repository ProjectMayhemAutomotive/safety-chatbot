import streamlit as st
import re
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Vehicle Safety Reporting System", 
    page_icon="🔧", 
    layout="centered"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { 
        margin-top: -80px;
        background-color: #0a0a0a;
    }
    div.stChatInput { 
        padding-bottom: 20px;
    }
    .main-title {
        text-align: center;
        color: #ff6b35;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        color: #cccccc;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        background: #1a1a1a !important;
        border-left: 3px solid #ff6b35;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #ffffff !important;
    }
    .stChatMessage[data-testid="user-message"] {
        border-left: 3px solid #666666;
    }
    .success-box {
        background: #ff6b35;
        color: #0a0a0a;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        margin: 20px 0;
    }
    .stButton button {
        background-color: #ff6b35;
        color: #0a0a0a;
        border: none;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #ff8555;
    }
    hr {
        border-color: #333333;
    }
</style>
""", unsafe_allow_html=True)

# NAME OF YOUR GOOGLE SHEET
SHEET_NAME = "Safety_Reports"

# --- 2. CONSTANTS ---
USER_FIELDS = [
    "Timestamp", "Make", "Model", "Model_Year", "VIN", "City", "State",
    "Speed", "Crash", "Fire", "Injured", "Deaths", "Description",
    "Component", "Mileage", "Technician_Notes",
    "Brake_Condition", "Engine_Temperature", "Date_Complaint",
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
    "Component": "Which component failed? (brakes, engine, transmission, etc.)",
    "Mileage": "What was the mileage at the time?",
    "Technician_Notes": "Any notes from a technician or mechanic?",
    "Brake_Condition": "How were the brakes? (Good / Worn / Failed)",
    "Engine_Temperature": "Engine temperature (if known)?",
    "Date_Complaint": "When did this issue occur? (YYYY-MM-DD)",
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

# --- GROQ API INTEGRATION ---
def generate_friendly_reply(user_input: str, base_text: str) -> str:
    """
    Use Groq API with Llama 3.1 to make responses more natural and conversational.
    """
    if not base_text:
        base_text = "Thank you. Please continue with the details."

    try:
        # Get API key from Streamlit secrets
        api_key = st.secrets.get("groq", {}).get("api_key")
        
        if not api_key:
            st.warning("⚠️ Groq API key not found. Using default responses.")
            return base_text

        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional vehicle safety complaint assistant. "
                        "Rewrite the assistant's message to be natural and friendly while keeping "
                        "ALL important information intact. Be concise and professional. "
                        "Keep responses under 80 words. Do not add extra questions."
                    )
                },
                {
                    "role": "user",
                    "content": f"User said: '{user_input}'\n\nRewrite naturally: {base_text}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 120,
            "top_p": 0.9
        }
        
        # Debug: Show that we're calling Groq
        with st.spinner("🤖 Generating response with Groq AI..."):
            response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            friendly_text = result["choices"][0]["message"]["content"].strip()
            
            # Debug: show success
            st.success(f"✅ Groq API called successfully (Model: llama-3.1-8b-instant)")
            
            return friendly_text if friendly_text else base_text
        else:
            st.error(f"❌ Groq API Error {response.status_code}: {response.text}")
            return base_text
            
    except requests.exceptions.Timeout:
        st.error("❌ Groq API timeout - using fallback response")
        return base_text
    except Exception as e:
        st.error(f"❌ Error calling Groq: {str(e)}")
        return base_text


# --- UEBA FUNCTION ---
def analyze_user_behavior(text):
    score = 0
    length = len(text)

    if length < 5:
        score += 2
    if length > 500:
        score += 3

    if text.isupper():
        score += 2

    if re.search(r"(.)\1{5,}", text):
        score += 3

    if ("no crash" in text.lower() and "accident" in text.lower()):
        score += 3

    bad_words = ["fuck", "shit", "bitch", "crap"]
    if any(b in text.lower() for b in bad_words):
        score += 3

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


# --- BOT LOGIC ---
class ComplaintBot:
    @staticmethod
    def get_next_question(record):
        for field in USER_FIELDS:
            if field == "Timestamp":
                continue
            if field in ["Input_Length", "Suspicion_Score", "User_Risk_Level"]:
                continue
            if record[field] is None:
                return field, QUESTIONS[field]
        return None, None

    @staticmethod
    def is_greeting(text):
        greetings = ["hi", "hello", "hey", "hola", "sup", "start", "yo", "good morning", "good afternoon"]
        return text.lower().strip() in greetings

    @staticmethod
    def extract_data(text, record, current_field):
        clean_text = text.strip()
        upper_text = clean_text.upper()
        updates = {}

        # Auto-detect year
        year_match = re.search(r"\b(19[89]\d|20[0-2]\d)\b", text)
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

        # Direct mapping for the current question
        if current_field and current_field not in updates:
            val = clean_text
            if val.lower() == "skip":
                updates[current_field] = "N/A"
            elif current_field in ["Crash", "Fire"]:
                updates[current_field] = "YES" if val.lower() in ["yes", "y", "yeah"] else "NO"
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
        "content": "Welcome to the Vehicle Safety Reporting System. Please describe the incident or issue you experienced."
    }]

if "record" not in st.session_state:
    st.session_state.record = {k: None for k in USER_FIELDS}

if "finished" not in st.session_state:
    st.session_state.finished = False


# --- UI ---
st.markdown('<h1 class="main-title">Vehicle Safety Reporting</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Secure complaint and feedback system</p>', unsafe_allow_html=True)
st.markdown("---")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- INPUT ---
if prompt := st.chat_input("Type your response..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not st.session_state.finished:
        current_missing, _ = ComplaintBot.get_next_question(st.session_state.record)

        # Greeting
        if ComplaintBot.is_greeting(prompt):
            base_response = "Hello! Please describe the vehicle incident or safety concern in your own words."
            response = generate_friendly_reply(prompt, base_response)

        else:
            # UEBA analysis
            length, score, risk = analyze_user_behavior(prompt)
            st.session_state.record["Input_Length"] = length
            st.session_state.record["Suspicion_Score"] = score
            st.session_state.record["User_Risk_Level"] = risk

            # Extract data
            new_data = ComplaintBot.extract_data(prompt, st.session_state.record, current_missing)

            if new_data:
                for k, v in new_data.items():
                    st.session_state.record[k] = v

                next_field, next_question = ComplaintBot.get_next_question(st.session_state.record)

                if next_field:
                    recorded_fields = ", ".join(new_data.keys())
                    base_response = f"Recorded: {recorded_fields}.\n\n{next_question}"
                    response = generate_friendly_reply(prompt, base_response)

                else:
                    st.session_state.finished = True
                    st.session_state.record["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    with st.spinner("Submitting report..."):
                        success = save_to_google_sheet(st.session_state.record)

                    if success:
                        base_response = "Your report has been submitted successfully. Thank you for the detailed information."
                    else:
                        base_response = "There was an error submitting your report. Please contact support."

                    response = generate_friendly_reply(prompt, base_response)

            else:
                base_response = f"I didn't catch that. {QUESTIONS.get(current_missing, 'Could you clarify?')}"
                response = generate_friendly_reply(prompt, base_response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

        if st.session_state.finished:
            st.rerun()


# --- SUMMARY ---
if st.session_state.finished:
    st.markdown("---")
    st.markdown('<div class="success-box">Report Successfully Submitted</div>', unsafe_allow_html=True)
    
    if st.button("Submit Another Report", type="primary", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Welcome back. Please describe the new incident."
        }]
        st.session_state.record = {k: None for k in USER_FIELDS}
        st.session_state.finished = False
        st.rerun()
