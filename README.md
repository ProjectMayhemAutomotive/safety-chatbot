# Vehicle Safety Reporting System

A professional, AI-powered complaint and feedback management system for vehicle safety incidents. Built with Streamlit and powered by Groq's Llama 3.1 AI model for natural, conversational interactions.

---

## Features

### Core Functionality
- **Intelligent Data Collection**: Automatically extracts vehicle information from natural language input
- **AI-Powered Responses**: Uses Groq's Llama 3.1 model to generate friendly, professional responses
- **User Behavior Analytics (UEBA)**: Monitors input patterns for quality assurance
- **Cloud Storage**: Automatically saves reports to Google Sheets
- **Multi-Field Validation**: Captures comprehensive incident data including vehicle details, location, and technical information

### User Experience
- **Conversational Interface**: Natural chat-based interaction
- **Auto-Detection**: Automatically identifies vehicle makes, model years, states, and incident types
- **Flexible Input**: Accepts free-form descriptions or structured responses
- **Professional Design**: Clean black and orange theme optimized for clarity

---

## Technical Stack

- **Frontend**: Streamlit
- **AI Model**: Llama 3.1 (8B Instant) via Groq API
- **Database**: Google Sheets via gspread
- **Authentication**: Google OAuth2 Service Account
- **Language**: Python 3.8+

---

## Installation

### Prerequisites
- Python 3.8 or higher
- Groq API account (free tier available)
- Google Cloud Platform account with Sheets API enabled

### Step 1: Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd vehicle-safety-reporting

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Create `requirements.txt`

```txt
streamlit>=1.28.0
gspread>=5.11.0
google-auth>=2.23.0
requests>=2.31.0
```

### Step 3: Configure Secrets

Create `.streamlit/secrets.toml` in your project root:

```toml
# Groq API Configuration
[groq]
api_key = "gsk_your_groq_api_key_here"

# Google Cloud Service Account
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project-id.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

---

## Configuration Guide

### 1. Get Groq API Key

1. Visit [Groq Console](https://console.groq.com/)
2. Sign up for a free account
3. Navigate to **API Keys** section
4. Click **Create API Key**
5. Copy the key (starts with `gsk_`)
6. Add to `secrets.toml` under `[groq]`

### 2. Set Up Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a **Service Account**:
   - Go to IAM & Admin → Service Accounts
   - Click **Create Service Account**
   - Grant **Editor** role
   - Create and download JSON key
5. Copy all fields from the JSON into `[gcp_service_account]` in secrets.toml

### 3. Create Google Sheet

1. Create a new Google Sheet named `Safety_Reports`
2. Share the sheet with your service account email
3. Grant **Editor** permissions

---

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### User Workflow

1. **Start Conversation**: User describes the incident naturally
2. **Data Extraction**: System automatically extracts relevant information
3. **Follow-up Questions**: Bot asks for missing required fields
4. **AI Enhancement**: Groq AI makes responses natural and friendly
5. **Validation**: UEBA system analyzes input quality
6. **Submission**: Report is saved to Google Sheets
7. **Confirmation**: User receives submission confirmation

### Example Interaction

```
Bot: Welcome to the Vehicle Safety Reporting System. Please describe the incident.

User: My 2022 Toyota Camry had brake failure in Los Angeles yesterday at 60 mph

Bot: Thank you for that information. I've recorded the vehicle details (Toyota Camry, 2022) 
     and location (Los Angeles). Was there a crash? (Yes/No)

User: No, but it was scary

Bot: Understood. Were there any injuries? (Enter number)

User: 0

Bot: Got it. Please describe exactly what happened.
```

---

## Data Fields Collected

### Vehicle Information
- Make, Model, Model Year
- VIN (optional)
- Component failure type
- Mileage
- Brake condition
- Engine temperature

### Incident Details
- Date and time
- Location (City, State)
- Speed at incident
- Crash occurrence
- Fire occurrence
- Injuries and fatalities
- Detailed description

### Technical Data
- Technician notes
- UEBA metrics (input length, suspicion score, risk level)

---

## Architecture

### Flow Diagram

```
User Input → UEBA Analysis → Data Extraction → AI Response Generation
                                    ↓
                              Missing Fields? 
                                    ↓
                           Yes → Ask Next Question
                           No  → Save to Google Sheets → Confirmation
```

### Key Components

#### `generate_friendly_reply()`
Calls Groq API to transform structured messages into natural conversation

#### `analyze_user_behavior()`
Scores input based on length, formatting, and content patterns

#### `ComplaintBot.extract_data()`
Uses regex and pattern matching to extract structured data from free text

#### `save_to_google_sheet()`
Authenticates and appends report data to Google Sheets

---

## Customization

### Modify Questions
Edit the `QUESTIONS` dictionary to change or add fields:

```python
QUESTIONS = {
    "YourField": "Your question text here?",
}
```

### Add Vehicle Makes
Update `KNOWN_MAKES` set:

```python
KNOWN_MAKES = {
    "FORD", "TOYOTA", "YOUR_BRAND"
}
```

### Change Theme
Modify CSS in the `st.markdown()` section:

```python
st.markdown("""
<style>
    .stApp { 
        background-color: #YourColor;
    }
</style>
""", unsafe_allow_html=True)
```

### Adjust AI Behavior
Modify the system prompt in `generate_friendly_reply()`:

```python
"content": "Your custom instructions here..."
```

---

## Troubleshooting

### Groq API Not Working
- **Check API Key**: Verify key in secrets.toml is correct
- **Check Quota**: Free tier has rate limits
- **Check Network**: Ensure internet connectivity
- **Fallback**: System automatically uses base messages if API fails

### Google Sheets Error
- **Check Permissions**: Ensure service account has Editor access
- **Check Sheet Name**: Verify `SHEET_NAME = "Safety_Reports"` matches your sheet
- **Check Credentials**: Validate all fields in `gcp_service_account`

### No Response from Bot
- **Check Console**: Look for error messages in terminal
- **Check Secrets**: Ensure `.streamlit/secrets.toml` exists
- **Restart App**: Stop and restart Streamlit

---

## Security Best Practices

- **Never commit** `.streamlit/secrets.toml` to version control
- Add to `.gitignore`:
  ```
  .streamlit/secrets.toml
  .env
  *.key
  ```
- Use environment variables in production
- Rotate API keys regularly
- Limit service account permissions to minimum required

---

## Deployment

### Streamlit Cloud

1. Push code to GitHub (exclude secrets.toml)
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your repository
4. Add secrets in Streamlit Cloud dashboard
5. Deploy

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

---

## Performance

- **Average Response Time**: 1-3 seconds (with Groq API)
- **Groq API Speed**: ~500 tokens/second
- **Concurrent Users**: Scales with Streamlit hosting
- **Data Storage**: Google Sheets (10 million cells limit)

---

## Roadmap

- [ ] Add multi-language support
- [ ] Implement file upload for photos/documents
- [ ] Add email notifications
- [ ] Create admin dashboard for report review
- [ ] Implement advanced analytics
- [ ] Add PDF report generation
- [ ] Mobile app version

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit changes (`git commit -m 'Add YourFeature'`)
4. Push to branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see LICENSE file for details.

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Contact: support@yourdomain.com
- Documentation: [Wiki](https://github.com/yourrepo/wiki)

---

## Acknowledgments

- **Groq**: For providing fast, reliable AI inference
- **Streamlit**: For the excellent web framework
- **Google**: For Sheets API and cloud services
- **Meta**: For the Llama 3.1 model

---

## Version History

### v1.0.0 (2024-12-09)
- Initial release
- Groq AI integration
- Google Sheets storage
- UEBA analytics
- Professional black/orange theme

---

**Built with ❤️ for vehicle safety**
