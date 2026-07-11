# 🌾 KrishiMitra — Smart Farming Advice AI Agent

> **AI-powered smart farming advisor built on IBM Watsonx.ai Granite models + Python Flask**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![IBM Watsonx](https://img.shields.io/badge/IBM%20Watsonx.ai-Granite%2013B-0062FF)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Chat** | Conversational AI powered by IBM Watsonx.ai Granite 13B Chat |
| 🌱 **Crop Recommendations** | Soil, season, rainfall & region-based crop advisory |
| 🧪 **Soil Health Analysis** | Soil test analysis with fertiliser & amendment plans |
| ⛅ **Weather-Smart Farming** | Real-time weather-condition-based farming actions |
| 🧑‍🌾 **Farmer Profile** | Personalized advice based on saved farmer profile |
| 🏛️ **Government Schemes** | PM-KISAN, PMFBY, KCC, PMKSY guidance |
| 💰 **Market Intelligence** | MSP, eNAM, FPO, price forecasting advice |
| 🌍 **Multilingual** | English, Hindi, Marathi, Punjabi, Tamil, Telugu & more |
| 🌙 **Dark Mode** | Full dark/light theme toggle |
| 📱 **Mobile-First** | Fully responsive Bootstrap 5 design |

---

## 📁 Project Structure

```
smart-farming-ai-agent/
├── app.py                  # Flask backend + API endpoints
├── agent_instructions.py   # ⭐ AGENT CONFIGURATION — edit this!
├── requirements.txt        # Python dependencies
├── .env                    # Secrets (DO NOT commit to Git)
├── .env.example            # Environment template
├── .gitignore
├── templates/
│   └── index.html          # Main HTML (Jinja2)
└── static/
    ├── css/
    │   ├── style.css       # Main styles + dark mode
    │   └── animations.css  # Extra animation helpers
    └── js/
        └── app.js          # All frontend JavaScript
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or later
- IBM Cloud Account with Watsonx.ai access
- A Watsonx.ai project ID

### Step 1 — Clone / Create the Project

```bash
# If cloning from git:
git clone <your-repo-url>
cd smart-farming-ai-agent

# Or just navigate to the project folder:
cd "Smart Farming Advice AI Agent"
```

### Step 2 — Create a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure IBM Credentials

Copy `.env.example` to `.env` and fill in your IBM Cloud credentials:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env`:

```env
IBM_API_KEY=your_actual_ibm_cloud_api_key
IBM_PROJECT_ID=your_watsonx_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=a-random-long-string-change-this
```

#### How to get IBM Watsonx.ai credentials:

1. Log in to [IBM Cloud](https://cloud.ibm.com)
2. Go to **Watsonx** → **Launch** → Create/open a project
3. Copy your **Project ID** from Project Settings
4. Go to **Manage → Access (IAM)** → **API keys** → Create API key
5. Copy the API key into your `.env`

### Step 5 — Run the App

```bash
python app.py
```

Open your browser at → **http://localhost:5000**

---

## ⚙️ Customizing the AI Agent

All agent behavior is controlled in **`agent_instructions.py`**. No backend changes needed.

### Change Agent Persona & Tone

```python
# agent_instructions.py

AGENT_NAME = "AgroBot"          # Change agent name
AGENT_TAGLINE = "Your Farm AI"  # Change tagline

AGENT_PERSONA = """
You are AgroBot, a professional agronomist specializing in
organic and regenerative farming...
"""

AGENT_TONE = "professional, concise, data-driven"
```

### Add / Remove Farming Specializations

```python
FARMING_SPECIALIZATIONS = [
    "Crop Selection & Rotation Planning",
    "Organic Farming & Certification",
    # Add your own:
    "Aquaponics & Hydroponics",
    "Export Market & Global Standards",
]
```

### Customize Safety Rules

```python
SAFETY_RULES = """
1. Never recommend banned pesticides.
2. Always mention IPM before chemical solutions.
3. Add your custom safety rule here.
"""
```

### Add New Crops to the Database

```python
CROP_DATABASE["Quinoa"] = {
    "soil": ["sandy loam", "loam"],
    "pH": "6.0–7.5",
    "rainfall_mm": "300–500",
    "temp_C": "15–25",
    "season": "Rabi",
    "water_need": "Low",
    "nutrients": "N:80, P:40, K:60 kg/ha",
}
```

### Add Region-Specific Knowledge

```python
REGIONAL_KNOWLEDGE["Coastal Maharashtra"] = [
    "High humidity — focus on fungal disease prevention",
    "Cashew and coconut dominant — value-addition focus",
]
```

### Add Government Schemes

```python
GOVERNMENT_SCHEMES.append(
    "State-specific scheme: e.g. Maharashtra Agri Mission"
)
```

### Switch the Watsonx Model

Edit `.env`:

```env
WATSONX_MODEL_ID=ibm/granite-20b-multilingual
# or
WATSONX_MODEL_ID=ibm/granite-13b-instruct-v2
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Main application UI |
| `POST` | `/api/chat` | AI chat endpoint |
| `POST` | `/api/crop-recommendation` | Crop recommendation engine |
| `POST` | `/api/soil-analysis` | Soil health analyser |
| `POST` | `/api/weather-advice` | Weather-smart farming advice |
| `GET`  | `/api/dashboard-data` | Dashboard statistics |
| `GET`  | `/api/health` | Health check / model status |

### Sample: Chat API

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What crop should I grow this Kharif season?",
    "farmer_profile": {
      "name": "Ramesh",
      "location": "Nagpur, Maharashtra",
      "land_acres": 5,
      "soil_type": "Black Cotton Soil",
      "irrigation": "Drip",
      "crops": ["Cotton", "Soybean"],
      "language": "Marathi"
    }
  }'
```

### Sample: Crop Recommendation API

```bash
curl -X POST http://localhost:5000/api/crop-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "season": "Kharif",
    "soil_type": "black cotton soil",
    "rainfall": 750,
    "temperature": 30,
    "region": "West India"
  }'
```

---

## 🌍 Deployment

### Option A — Gunicorn (Linux/macOS Production)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option B — IBM Code Engine

```bash
# Install IBM Cloud CLI
ibmcloud login --apikey $IBM_API_KEY
ibmcloud target -g default
ibmcloud ce project create --name farming-ai

# Deploy
ibmcloud ce application create \
  --name krishimitra \
  --image <your-registry>/krishimitra:latest \
  --port 5000 \
  --env IBM_API_KEY=<key> \
  --env IBM_PROJECT_ID=<id>
```

### Option C — Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t krishimitra .
docker run -p 5000:5000 --env-file .env krishimitra
```

### Option D — Render / Railway

1. Push to GitHub (make sure `.env` is in `.gitignore`!)
2. Connect repository on [render.com](https://render.com) or [railway.app](https://railway.app)
3. Set environment variables in their dashboard
4. Deploy — Done!

---

## 🛡️ Security Notes

| Concern | Mitigation |
|---------|-----------|
| API Key exposure | Stored in `.env`, never in code. `.env` is gitignored. |
| Injection attacks | Flask's `request.get_json(silent=True)` handles malformed input |
| Session security | `FLASK_SECRET_KEY` should be a cryptographically random string |
| Production debug | Set `FLASK_DEBUG=False` in `.env` |

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ibm-watsonx-ai` install fails | Try `pip install ibm-watsonx-ai==1.1.2 --upgrade` |
| `401 Unauthorized` from Watsonx | Check `IBM_API_KEY` is correct and not expired |
| `403 Forbidden` from Watsonx | Verify `IBM_PROJECT_ID` matches your actual project |
| App runs in Demo Mode | Add valid credentials to `.env` and restart |
| Port 5000 in use | Change `FLASK_PORT=5001` in `.env` |

---

## 📞 Farmer Helplines (India)

| Service | Number |
|---------|--------|
| Kisan Call Centre | **1800-180-1551** (Toll Free) |
| PM-KISAN Helpline | **155261** |
| NABARD | **1800-22-0012** |
| IMD Weather | **1800-180-1717** |

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

*Built with ❤️ using IBM Watsonx.ai Granite Models & Python Flask*
