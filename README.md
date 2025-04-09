# AI Job Applicant Bot

An autonomous agent that searches for jobs, matches them to your resume, and applies automatically.

## Features

- 🔍 Searches multiple job boards (LinkedIn, Indeed, Dice, RemoteOK, AngelList)
- 🤖 Uses NLP to match your resume to job descriptions
- ✍️ Generates tailored cover letters for each application
- 🚀 Automatically applies to jobs that match your criteria
- 📊 Dashboard to monitor application status and manage resume/cover letters

## Project Structure

- `/automation/` - Job site bots and application automation
- `/resume/` - Resume parsing and matching logic
- `/ui/` - Streamlit dashboard
- `/logs/` - Activity logs
- `/config/` - Configuration files
- `/utils/` - Utility functions

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip
- Node.js (if using Puppeteer as fallback)

### Installation

1. Clone this repository
```bash
git clone https://github.com/joelfuller2016/ai-job-applicant-bot.git
cd ai-job-applicant-bot
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Install browser for Playwright
```bash
python -m playwright install
```

5. Set up your configuration
```bash
cp config/config.example.json config/config.json
# Edit config.json with your details
```

6. Upload your resume
```bash
# Place your resume in the resume/data/ folder
```

### Running the Application

```bash
python -m streamlit run ui/app.py
```

## Configuration Example

Copy the example below to `config/config.json` and modify with your details:

```json
{
  "user": {
    "name": "Your Name",
    "email": "your.email@example.com",
    "phone": "(123) 456-7890",
    "location": "City, State",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "github": "https://github.com/yourusername"
  },
  "job_search": {
    "titles": [
      "Senior Software Developer",
      "Senior Software Engineer",
      "Full Stack Developer",
      "Project Manager"
    ],
    "remote_only": true,
    "locations": ["Remote"],
    "exclude_keywords": ["junior", "internship"],
    "min_salary": 100000
  },
  "application": {
    "auto_submit": false,
    "application_limit_per_day": 10
  },
  "job_boards": {
    "linkedin": {
      "enabled": true,
      "username": "",
      "password": ""
    },
    "indeed": {
      "enabled": true,
      "username": "",
      "password": ""
    },
    "dice": {
      "enabled": true
    },
    "remoteok": {
      "enabled": true
    },
    "angellist": {
      "enabled": false
    }
  }
}
```

## Screenshots

*[Dashboard screenshot to be added]*

## License

MIT
