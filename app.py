"""
============================================================
  Smart Farming Advice AI Agent
  Backend  —  app.py
  Framework : Flask 3.x
  AI Engine : IBM Watsonx.ai  (Granite 13B Chat v2)
  Author    : IBM Watsonx Smart Farming Team
============================================================
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

# ── Load environment variables from .env ────────────────────
load_dotenv()

# ── Import agent configuration ───────────────────────────────
from agent_instructions import (
    AGENT_NAME,
    AGENT_TAGLINE,
    CROP_DATABASE,
    SEASONS,
    GOVERNMENT_SCHEMES,
    FARMING_SPECIALIZATIONS,
    REGIONAL_KNOWLEDGE,
    build_system_prompt,
)

# ── IBM Watsonx.ai SDK ───────────────────────────────────────
try:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False
    logging.warning("ibm-watsonx-ai not installed. Running in DEMO mode.")

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Flask App ─────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

# ── Watsonx Credentials ───────────────────────────────────────
IBM_API_KEY    = os.getenv("IBM_API_KEY", "")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
IBM_URL        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
MODEL_ID       = os.getenv("WATSONX_MODEL_ID", "ibm/granite-4-h-small")
print("Loaded MODEL_ID:", repr(MODEL_ID))
MAX_TOKENS     = int(os.getenv("WATSONX_MAX_TOKENS", 1024))
TEMPERATURE    = float(os.getenv("WATSONX_TEMPERATURE", 0.7))
TOP_P          = float(os.getenv("WATSONX_TOP_P", 0.9))


# ════════════════════════════════════════════════════════════
#  Watsonx.ai Model Initializer
# ════════════════════════════════════════════════════════════
def get_watsonx_model(farmer_profile: dict = None):
    """Initialise and return the IBM Watsonx.ai ModelInference instance."""
    if not WATSONX_AVAILABLE:
        return None
    if not IBM_API_KEY or IBM_API_KEY == "your_ibm_cloud_api_key_here":
        logger.warning("IBM_API_KEY not configured. Running in DEMO mode.")
        return None
    try:
        credentials = Credentials(
            url=IBM_URL,
            api_key=IBM_API_KEY,
        )
        model = ModelInference(
            model_id=MODEL_ID,
            credentials=credentials,
            project_id=IBM_PROJECT_ID,
            params={
                GenParams.MAX_NEW_TOKENS: MAX_TOKENS,
                GenParams.TEMPERATURE: TEMPERATURE,
                GenParams.TOP_P: TOP_P,
                GenParams.REPETITION_PENALTY: 1.1,
            },
        )
        return model
    except Exception as exc:
        logger.error("Failed to initialise Watsonx model: %s", exc)
        return None


# ════════════════════════════════════════════════════════════
#  AI Chat Response Generator
# ════════════════════════════════════════════════════════════
def generate_ai_response(user_message: str, conversation_history: list, farmer_profile: dict = None) -> str:
    """
    Call IBM Watsonx.ai Granite model and return the AI response.
    Falls back to a structured demo response if credentials are absent.
    """
    system_prompt = build_system_prompt(farmer_profile)

    # ── Build the prompt string for Granite Chat format ──────
    prompt_parts = [f"<|system|>\n{system_prompt}\n<|endoftext|>"]
    for msg in conversation_history[-10:]:          # keep last 10 turns
        role  = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            prompt_parts.append(f"<|user|>\n{content}\n<|endoftext|>")
        else:
            prompt_parts.append(f"<|assistant|>\n{content}\n<|endoftext|>")
    prompt_parts.append(f"<|user|>\n{user_message}\n<|endoftext|>")
    prompt_parts.append("<|assistant|>")
    full_prompt = "\n".join(prompt_parts)

    model = get_watsonx_model(farmer_profile)

    if model:
        try:
            response = model.generate_text(prompt=full_prompt)
            # Strip stop tokens if any leak through
            response = response.replace("<|endoftext|>", "").strip()
            return response
        except Exception as exc:
            logger.error("Watsonx generation error: %s", exc)
            return _demo_response(user_message, farmer_profile)
    else:
        return _demo_response(user_message, farmer_profile)


def _demo_response(message: str, farmer_profile: dict = None) -> str:
    """
    Structured demo response returned when IBM credentials are not configured.
    Provides realistic farming advice for demonstration purposes.
    """
    msg_lower = message.lower()
    farmer_name = farmer_profile.get("name", "Farmer") if farmer_profile else "Farmer"

    if any(w in msg_lower for w in ["crop", "grow", "plant", "sow", "cultivate", "recommend"]):
        return f"""Hello {farmer_name}! 🌾 Here are my crop recommendations:

**Based on current Kharif season (June–October):**

| Crop | Expected Yield | Water Need | Market Price |
|------|---------------|------------|--------------|
| Soybean | 15–20 q/ha | Medium | ₹4,200/q |
| Cotton | 20–25 q/ha | Medium-High | ₹6,500/q |
| Maize | 40–50 q/ha | Medium | ₹2,000/q |
| Groundnut | 18–22 q/ha | Medium | ₹5,500/q |

**My Top Recommendation:** Soybean–Cotton intercropping for 5-acre plots.

**Why?** This combination optimises land use, reduces pest pressure, and maximises income by ₹18,000–₹25,000/acre.

**Next Steps:**
1. Get your Soil Health Card tested at your nearest KVK
2. Apply for PM-KISAN benefit (₹6,000/year) if not enrolled
3. Register on eNAM portal for better price discovery

Would you like a detailed planting calendar or fertiliser schedule? 🌱"""

    elif any(w in msg_lower for w in ["soil", "fertility", "nutrient", "ph", "health"]):
        return f"""Hello {farmer_name}! Here's your **Soil Health Analysis Guide:**

**Ideal Soil Parameters:**
- pH: 6.0–7.5 (slight acidic to neutral)
- Organic Carbon: >0.75%
- Available N: >280 kg/ha
- Available P: >10 kg/ha
- Available K: >108 kg/ha

**Signs Your Soil Needs Attention:**
⚠️ Yellowing leaves → Nitrogen deficiency
⚠️ Poor root growth → Phosphorus deficiency
⚠️ Leaf edge burn → Potassium deficiency
⚠️ Stunted growth → pH imbalance

**Recommended Actions:**
1. **Soil Test**: Visit your nearest KVK or use Soil Health Card scheme (FREE)
2. **Organic Matter**: Apply 5–8 tonnes FYM/ha before sowing
3. **Green Manure**: Grow Dhaincha/Sesbania for 45 days then incorporate
4. **Biofertilisers**: Use Rhizobium + PSB + Azospirillum to reduce chemical fertiliser by 25%

**Cost Savings Tip:** Neem-coated urea reduces nitrogen loss by 30% and costs only ₹20 more per bag.

Want me to create a custom fertiliser schedule for your specific crop? 🌿"""

    elif any(w in msg_lower for w in ["water", "irrigation", "drip", "sprinkler", "drought"]):
        return f"""Hello {farmer_name}! Here's your **Smart Irrigation Guide:**

**Water Requirement by Crop Stage:**
- Germination: Light, frequent irrigation
- Vegetative: Moderate — 40–50mm/week
- Flowering: Critical — never stress at this stage
- Grain filling: Reduce gradually
- Maturity: Stop 10 days before harvest

**Irrigation Methods Comparison:**

| Method | Water Saving | Cost/Acre | Suitable For |
|--------|-------------|-----------|--------------|
| Flood  | Baseline    | ₹0        | Paddy, Sugarcane |
| Sprinkler | 30–40% | ₹12,000  | Wheat, Vegetables |
| Drip   | 50–70%      | ₹35,000  | Cotton, Horticulture |
| Micro Drip | 60–75% | ₹28,000 | Sugarcane, Banana |

**Government Subsidy:** PMKSY provides up to **55% subsidy** on drip/sprinkler systems for small farmers.

**Water Conservation Tips:**
1. Mulching reduces water need by 25–30%
2. Land levelling saves 15–20% irrigation water
3. Check for canal water schedule from your irrigation department

Apply today at pmksy.gov.in or contact your local agriculture office. 💧"""

    elif any(w in msg_lower for w in ["pest", "disease", "insect", "fungus", "blight", "wilt"]):
        return f"""Hello {farmer_name}! Here's your **IPM (Integrated Pest Management) Guide:**

**Early Warning Signs:**
🔴 Leaf spots/lesions → Fungal disease
🔴 Yellowing + wilting → Root rot or wilt
🔴 Holes in leaves → Caterpillar/beetle damage
🔴 Sticky residue → Aphids/whitefly
🔴 White powder → Powdery mildew

**IPM Action Steps (in order):**
1. **Cultural Control**: Crop rotation, resistant varieties, proper spacing
2. **Biological Control**: Release Trichogramma cards (₹150/acre), Beauveria bassiana spray
3. **Mechanical Control**: Sticky traps (yellow for whitefly, blue for thrips)
4. **Chemical Control** (LAST resort only):
   - Always follow label instructions
   - Use PPE: gloves, mask, goggles
   - Observe waiting period before harvest

⚠️ **Safety Warning**: Never mix pesticides without consulting a licensed dealer. Dispose of empty containers safely — DO NOT use for storing food or water.

**Free Help**: Call Kisan Call Centre: **1800-180-1551** (Toll Free, 7 AM–10 PM)

What specific pest/disease are you dealing with? I can give targeted advice! 🐛"""

    elif any(w in msg_lower for w in ["weather", "rain", "monsoon", "forecast", "climate"]):
        return f"""Hello {farmer_name}! Here's **Weather-Smart Farming Advice:**

**Current Season Outlook:**
Based on IMD forecasts, the Southwest Monsoon this year shows:
- Normal to above-normal rainfall in Central & South India
- Below-normal in Northwest India
- Onset likely 2nd week of June in Kerala

**Actionable Weather Planning:**

🌧️ **If Excess Rain Expected:**
- Choose raised bed cultivation
- Apply ridge & furrow system
- Keep drainage channels clear
- Avoid basal dose fertiliser until soil settles

☀️ **If Drought Conditions:**
- Shift to drought-tolerant varieties (e.g., MACS 6222 for soybean)
- Increase mulching
- Adopt conservation tillage
- Consider crop insurance under PMFBY

🌡️ **Heat Stress Management:**
- Irrigate in early morning or evening
- Apply potassium spray (2% KCl) to reduce heat stress
- Provide shade netting for nurseries

**Weather Resources:**
- IMD App: Meghdoot (free, farmer-friendly)
- Kisan Suvidha App (crop advisory + weather)
- Visit: mausam.imd.gov.in

Would you like a week-wise crop activity planner? 🌤️"""

    elif any(w in msg_lower for w in ["scheme", "subsidy", "government", "yojana", "insurance", "loan", "kisan"]):
        return f"""Hello {farmer_name}! Here are the key **Government Schemes for Farmers:**

**Immediate Action Items — Apply NOW:**

💰 **PM-KISAN** (₹6,000/year in 3 installments)
- Eligibility: All small & marginal farmers
- Apply: pmkisan.gov.in or nearest CSC

🛡️ **PMFBY — Crop Insurance**
- Premium: Only 1.5% for Rabi, 2% for Kharif
- Covers: Natural disasters, pest/disease
- Enroll before sowing season starts

💧 **PMKSY — Irrigation Subsidy**
- Up to 55% subsidy on drip/sprinkler
- Apply through State Horticulture Department

🌱 **Soil Health Card** (FREE)
- Detailed soil analysis & fertiliser recommendations
- Contact: Nearest Krishi Kendra

💳 **Kisan Credit Card (KCC)**
- Credit up to ₹3 lakh at 7% interest (4% with interest subvention)
- Apply at any nationalised bank

📈 **eNAM — Online Market**
- Sell directly to buyers, better price discovery
- Register: enam.gov.in

**Toll-Free Helplines:**
- Kisan Call Centre: **1800-180-1551**
- PM-KISAN Helpline: **155261**

Which scheme would you like detailed application guidance for? 📋"""

    elif any(w in msg_lower for w in ["fertilizer", "fertiliser", "manure", "compost", "npk", "urea", "dap"]):
        return f"""Hello {farmer_name}! Here's your **Smart Fertiliser Management Guide:**

**The 4R Approach:**
1. ✅ **Right Source** — Match fertiliser to crop & soil need
2. ✅ **Right Rate** — Based on Soil Health Card recommendation
3. ✅ **Right Time** — Split application for better uptake
4. ✅ **Right Place** — Band placement vs. broadcast

**Cost-Effective Fertiliser Strategy:**

| Stage | Fertiliser | Qty/Acre | Cost |
|-------|------------|----------|------|
| Basal | DAP | 50 kg | ₹1,400 |
| Basal | MOP | 33 kg | ₹660 |
| 30 DAP | Urea | 55 kg | ₹770 |
| 60 DAP | Urea | 55 kg | ₹770 |

**Organic Alternatives (Reduce cost by 30–40%):**
- Vermicompost: 1 tonne/acre (₹2,500) replaces 25% chemical fertiliser
- Green manure: Dhaincha incorporation saves ₹800/acre in N cost
- Bio-fertilisers (Rhizobium + PSB + Azospirillum): ₹300/acre saves ₹1,200

**Remember:** Neem-coated urea is MANDATORY for non-paddy crops. It's available at all IFFCO outlets.

Want a crop-specific fertiliser schedule? Just tell me your crop! 🌻"""

    elif any(w in msg_lower for w in ["market", "price", "sell", "msp", "mandi", "profit"]):
        return f"""Hello {farmer_name}! Here's your **Market Intelligence Guide:**

**Current MSP (Minimum Support Prices) — 2024-25:**

| Crop | MSP (₹/quintal) | YoY Change |
|------|----------------|------------|
| Paddy (Common) | ₹2,300 | +5.3% |
| Wheat | ₹2,275 | +5.0% |
| Soybean | ₹4,892 | +3.8% |
| Cotton (Medium) | ₹7,121 | +8.3% |
| Maize | ₹2,090 | +5.8% |

**How to Get Better Prices:**
1. **eNAM Portal** (enam.gov.in) — Compare prices across 1,000+ mandis
2. **FPO Membership** — Collective selling improves bargaining by 15–20%
3. **Quality Grading** — Grade A produce fetches 10–15% premium
4. **Direct Marketing** — SAFAL, Reliance Fresh, ITC e-Choupal
5. **Value Addition** — Drying, cleaning, packaging adds 20–30% value

**Post-Harvest Storage:**
- Use NABARD-funded warehouses for 6-month storage
- Warehouse Receipt Financing: Get loans against stored produce at 7% interest

**Market Intelligence Apps:**
- Agmarknet (official mandi prices)
- Kisan Suvidha, IFFCO Kisan, DeHaat

Would you like specific marketing advice for your crop? 💹"""

    else:
        return f"""Hello {farmer_name}! I'm **{AGENT_NAME}** — {AGENT_TAGLINE}. 🌾

I'm your AI-powered farming companion, here to help you with:

🌱 **Crop Recommendations** — Best crops for your soil & season
🧪 **Soil Health Analysis** — Soil testing & fertility management
💧 **Irrigation Planning** — Smart water management
🐛 **Pest & Disease Management** — IPM strategies
⛅ **Weather-Smart Farming** — Climate-resilient agriculture
💰 **Market Intelligence** — MSP, eNAM, price forecasting
🏛️ **Government Schemes** — PM-KISAN, PMFBY, KCC & more
🌿 **Sustainable Practices** — Organic & regenerative farming

**How can I help you today?** Just ask me anything about farming in your preferred language — I support English, Hindi, Marathi, Punjabi, Tamil, Telugu, and more!

**Quick Questions to Get Started:**
- "What crop should I grow this season in my area?"
- "My cotton crop has yellowing leaves — what should I do?"
- "How can I apply for PM-KISAN?"
- "What is the current MSP for wheat?"

*Type your question below* 👇"""


# ════════════════════════════════════════════════════════════
#  Flask Routes
# ════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the main application page."""
    return render_template(
        "index.html",
        agent_name=AGENT_NAME,
        agent_tagline=AGENT_TAGLINE,
        crops=list(CROP_DATABASE.keys()),
        seasons=SEASONS,
        specializations=FARMING_SPECIALIZATIONS,
        schemes=GOVERNMENT_SCHEMES,
        regional_knowledge=REGIONAL_KNOWLEDGE,
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Expects JSON: {
        "message": str,
        "conversation_history": list,
        "farmer_profile": dict (optional)
    }
    """
    data = request.get_json(silent=True) or {}
    user_message         = data.get("message", "").strip()
    conversation_history = data.get("conversation_history", [])
    farmer_profile       = data.get("farmer_profile", {})

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    logger.info("Chat request — user: %s | msg: %s", farmer_profile.get("name", "Anonymous"), user_message[:80])

    ai_response = generate_ai_response(user_message, conversation_history, farmer_profile)

    return jsonify({
        "response": ai_response,
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "model": MODEL_ID,
        "agent_name": AGENT_NAME,
    })


@app.route("/api/crop-recommendation", methods=["POST"])
def crop_recommendation():
    """
    Dedicated crop recommendation endpoint.
    Expects JSON: { "soil_type", "season", "rainfall", "temperature", "region" }
    """
    data        = request.get_json(silent=True) or {}
    soil_type   = data.get("soil_type", "").lower()
    season      = data.get("season", "")
    rainfall    = data.get("rainfall", 0)
    temperature = data.get("temperature", 25)
    region      = data.get("region", "")

    recommendations = []
    for crop, info in CROP_DATABASE.items():
        # Season match
        if season and season.lower() not in info["season"].lower() and "year" not in info["season"].lower():
            continue
        # Soil match (loose)
        soil_match = any(s in soil_type for s in [st.lower().split()[0] for st in info["soil"]])
        recommendations.append({
            "crop": crop,
            "season": info["season"],
            "water_need": info["water_need"],
            "soil_types": info["soil"],
            "recommended_pH": info["pH"],
            "nutrients": info["nutrients"],
            "soil_match": soil_match,
        })

    # Sort: soil matches first
    recommendations.sort(key=lambda x: (0 if x["soil_match"] else 1, x["crop"]))

    # Build AI narrative
    ai_prompt = (
        f"Farmer profile: region={region}, soil_type={soil_type}, season={season}, "
        f"avg_rainfall={rainfall}mm, avg_temperature={temperature}°C. "
        f"Top matching crops from database: {[r['crop'] for r in recommendations[:5]]}. "
        f"Provide a 3-paragraph personalized crop recommendation with specific variety names, "
        f"expected yield, and any local government scheme relevant to these crops."
    )
    ai_narrative = generate_ai_response(ai_prompt, [], {"location": region})

    return jsonify({
        "recommendations": recommendations[:6],
        "ai_narrative": ai_narrative,
        "season_crops": SEASONS,
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/soil-analysis", methods=["POST"])
def soil_analysis():
    """
    Soil health analysis endpoint.
    Expects JSON: { "ph", "nitrogen", "phosphorus", "potassium", "organic_carbon", "crop" }
    """
    data           = request.get_json(silent=True) or {}
    ph             = float(data.get("ph", 7.0))
    nitrogen       = float(data.get("nitrogen", 250))
    phosphorus     = float(data.get("phosphorus", 10))
    potassium      = float(data.get("potassium", 100))
    organic_carbon = float(data.get("organic_carbon", 0.5))
    crop           = data.get("crop", "general")

    issues   = []
    actions  = []
    score    = 100

    if ph < 6.0:
        issues.append("Soil is acidic (pH < 6.0)")
        actions.append("Apply agricultural lime @ 2–3 tonnes/ha to raise pH")
        score -= 20
    elif ph > 7.5:
        issues.append("Soil is alkaline (pH > 7.5)")
        actions.append("Apply gypsum @ 5 tonnes/ha or sulphur @ 400 kg/ha")
        score -= 15

    if nitrogen < 280:
        issues.append("Low available nitrogen")
        actions.append("Apply 25% extra urea dose; use biofertiliser Azospirillum")
        score -= 15

    if phosphorus < 10:
        issues.append("Phosphorus deficient")
        actions.append("Apply DAP or SSP; use PSB (Phosphate Solubilising Bacteria)")
        score -= 15

    if potassium < 108:
        issues.append("Potassium deficient")
        actions.append("Apply MOP (Muriate of Potash) @ 40 kg K₂O/ha")
        score -= 10

    if organic_carbon < 0.5:
        issues.append("Very low organic carbon — poor soil structure")
        actions.append("Apply 8–10 tonnes FYM/ha; grow green manure crop")
        score -= 25
    elif organic_carbon < 0.75:
        issues.append("Low organic carbon")
        actions.append("Apply 5 tonnes vermicompost/ha annually")
        score -= 10

    health_rating = (
        "Excellent 🟢" if score >= 85 else
        "Good 🟡"      if score >= 70 else
        "Fair 🟠"      if score >= 50 else
        "Poor 🔴"
    )

    ai_prompt = (
        f"Soil test results: pH={ph}, N={nitrogen}kg/ha, P={phosphorus}kg/ha, "
        f"K={potassium}kg/ha, Organic Carbon={organic_carbon}%, crop={crop}. "
        f"Issues detected: {issues}. "
        f"Provide a detailed soil health report with fertiliser schedule, "
        f"organic amendments, and a 3-year soil improvement plan."
    )
    ai_narrative = generate_ai_response(ai_prompt, [], {})

    return jsonify({
        "score": max(score, 0),
        "health_rating": health_rating,
        "issues": issues,
        "recommended_actions": actions,
        "ai_narrative": ai_narrative,
        "parameters": {
            "pH": ph, "Nitrogen": nitrogen,
            "Phosphorus": phosphorus, "Potassium": potassium,
            "Organic Carbon": organic_carbon,
        },
    })


@app.route("/api/weather-advice", methods=["POST"])
def weather_advice():
    """
    Weather-aware farming advice endpoint.
    Expects JSON: { "condition", "rainfall_mm", "temperature", "season", "crop" }
    """
    data        = request.get_json(silent=True) or {}
    condition   = data.get("condition", "sunny")
    rainfall_mm = float(data.get("rainfall_mm", 50))
    temperature = float(data.get("temperature", 28))
    season      = data.get("season", "Kharif")
    crop        = data.get("crop", "Rice")

    ai_prompt = (
        f"Current weather: {condition}, rainfall={rainfall_mm}mm this week, "
        f"temperature={temperature}°C, season={season}, main crop={crop}. "
        f"Provide detailed weather-aware farming advice covering: "
        f"1) Immediate actions for today, "
        f"2) Irrigation adjustments, "
        f"3) Pest/disease risks in this weather, "
        f"4) Fertiliser timing caution, "
        f"5) Harvesting or sowing recommendations."
    )
    ai_response = generate_ai_response(ai_prompt, [], {})

    # Determine alert level
    alert = "normal"
    if temperature > 40 or rainfall_mm > 200:
        alert = "high"
    elif temperature > 35 or rainfall_mm > 100:
        alert = "medium"

    return jsonify({
        "advice": ai_response,
        "alert_level": alert,
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/dashboard-data", methods=["GET"])
def dashboard_data():
    """Return static dashboard statistics for the UI."""
    return jsonify({
        "stats": {
            "crops_in_database": len(CROP_DATABASE),
            "schemes_available": len(GOVERNMENT_SCHEMES),
            "specializations": len(FARMING_SPECIALIZATIONS),
            "regions_covered": 6,
            "languages_supported": 9,
            "seasons": 4,
        },
        "crops": list(CROP_DATABASE.keys()),
        "seasons": SEASONS,
        "top_schemes": GOVERNMENT_SCHEMES[:5],
        "specializations": FARMING_SPECIALIZATIONS,
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    model_status = "configured" if (
        IBM_API_KEY and IBM_API_KEY != "your_ibm_cloud_api_key_here"
    ) else "demo_mode"

    return jsonify({
        "status": "healthy",
        "agent": AGENT_NAME,
        "model": MODEL_ID,
        "watsonx_sdk": WATSONX_AVAILABLE,
        "model_status": model_status,
        "timestamp": datetime.now().isoformat(),
    })


# ════════════════════════════════════════════════════════════
#  Entry Point
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    logger.info("Starting %s on port %d (debug=%s)", AGENT_NAME, port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
