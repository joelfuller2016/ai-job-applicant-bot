# AI Job Applicant Bot

An autonomous agent that searches for jobs, matches them to your resume, and applies automatically using advanced AI and browser automation.

## 🚀 Project Evolution: browser-use Integration

We're enhancing this project with [browser-use](https://github.com/browser-use/browser-use) integration to create a more powerful and undetectable job application solution. The new version will feature:

- 🧠 **Advanced AI Integration** - Using ML and vision capabilities to understand job sites
- 🕵️ **Undetectable Automation** - Sophisticated browser automation that mimics human behavior
- 👁️ **Computer Vision** - AI vision for handling CAPTCHAs and complex page elements
- 🔄 **Profile Rotation** - Browser profile management to avoid detection
- 🤖 **Autonomous Decision Making** - AI-driven job evaluation and application decisions

See our [Project Plan](PROJECT_PLAN.md) and [Requirements Document](REQUIREMENTS.md) for implementation details.

## Features

- 🔍 Searches multiple job boards (LinkedIn, Indeed, Dice, RemoteOK)
- 🤖 Uses ML to match your resume to job descriptions
- ✍️ Generates tailored cover letters for each application
- 🚀 Automatically applies to jobs that match your criteria
- 📊 Dashboard to monitor application status and manage resume/cover letters
- 👤 Human-like browser interaction patterns
- 🛡️ Anti-detection mechanisms

## Project Structure

- `/automation/` - Job site bots and application automation
- `/resume/` - Resume parsing and matching logic
- `/ui/` - Streamlit dashboard
- `/logs/` - Activity logs
- `/config/` - Configuration files
- `/utils/` - Utility functions
- `/data/` - Job database and application history

## Setup Instructions

### Prerequisites

- Python 3.11+
- pip
- Chromium (installed via Playwright)

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
python -m playwright install chromium
```

5. Set up your configuration
```bash
cp config/config.example.json config/config.json
# Edit config.json with your details
```

6. Set up your environment variables
```bash
cp .env.example .env
# Add your API keys to .env file
```

7. Upload your resume
```bash
# Place your resume in the resume/data/ folder
```

### Running the Application

```bash
python -m streamlit run ui/app.py
```

Or for console mode:

```bash
python main.py --no-ui
```

## Configuration Example

Copy the example below to `config/config.json` and modify with your details:

```json
{
  "name": "AI Job Applicant Bot",
  "version": "2.0.0",
  
  "browser": {
    "headless": false,
    "slow_mo": 50,
    "screenshot_dir": "logs/screenshots"
  },
  
  "job_search": {
    "titles": [
      "Senior Software Developer",
      "Senior Software Engineer",
      "Full Stack Developer"
    ],
    "location": "Remote",
    "remote_only": true,
    "exclude_keywords": ["junior", "internship"],
    "required_skills": ["python", "javascript", "aws"],
    "experience_years": 5,
    "max_days_old": 30
  },
  
  "job_boards": {
    "linkedin": {
      "enabled": true,
      "url": "https://www.linkedin.com/jobs/"
    },
    "indeed": {
      "enabled": true,
      "url": "https://www.indeed.com/"
    },
    "dice": {
      "enabled": true,
      "url": "https://www.dice.com/"
    },
    "remoteok": {
      "enabled": true,
      "url": "https://remoteok.com/"
    }
  },
  
  "ai": {
    "llm_model": "gpt-4-turbo",
    "vision_model": "gpt-4-vision-preview",
    "temperature": 0.2,
    "match_threshold": 70
  },
  
  "application": {
    "daily_application_limit": 10,
    "auto_submit": false
  }
}
```

## Environment Variables

Create a `.env` file with:

```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  # Optional
BROWSERUSE_HEADLESS=false  # For debugging, set to true in production
```

## Development

See the [Project Plan](PROJECT_PLAN.md) for implementation timeline and milestones.

## Screenshots

*[Dashboard screenshot to be added]*

## License

MIT
