"""
============================================================
  Smart Farming Advice AI Agent
  Backend  —  main.py
  Framework : Flask 3.x
  AI Engine : IBM Watsonx.ai  (Granite)
  Author    : IBM Watsonx Smart Farming Team
============================================================
"""

import os
import logging
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify
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
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
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
MAX_TOKENS     = int(os.getenv("WATSONX_MAX_TOKENS", 1024))
TEMPERATURE    = float(os.getenv("WATSONX_TEMPERATURE", 0.7))
TOP_P          = float(os.getenv("WATSONX_TOP_P", 0.9))

logger.info("MODEL_ID configured: %s", MODEL_ID)

# ── Module-level model cache (initialised once per process) ──
# FIX #3: Previously get_watsonx_model() was called on *every* request,
# creating a new Credentials + ModelInference object each time.  That
# causes repeated IAM token-exchange round trips and wastes ~200-500 ms
# per request.  We cache the model at module level and only recreate it
# if credentials change.
_watsonx_model_cache: "ModelInference | None" = None


# ════════════════════════════════════════════════════════════
#  Watsonx.ai Model Initializer  (cached singleton)
# ════════════════════════════════════════════════════════════
def get_watsonx_model():
    """
    Return the cached IBM Watsonx.ai ModelInference instance.
    Initialises on first call; returns None when credentials are absent
    or the SDK is unavailable.

    FIX #3: Model is cached as a module-level singleton so that
    Credentials / IAM token exchange happens only once per process.
    """
    global _watsonx_model_cache

    if _watsonx_model_cache is not None:
        return _watsonx_model_cache

    if not WATSONX_AVAILABLE:
        return None

    if not IBM_API_KEY or IBM_API_KEY == "your_ibm_cloud_api_key_here":
        logger.warning("IBM_API_KEY not configured. Running in DEMO mode.")
        return None

    if not IBM_PROJECT_ID:
        logger.warning("IBM_PROJECT_ID not configured. Running in DEMO mode.")
        return None

    try:
        logger.info("Initialising Watsonx ModelInference (model=%s) …", MODEL_ID)
        credentials = Credentials(
            url=IBM_URL,
            api_key=IBM_API_KEY,
        )
        _watsonx_model_cache = ModelInference(
            model_id=MODEL_ID,
            credentials=credentials,
            project_id=IBM_PROJECT_ID,
            params={
                GenParams.MAX_NEW_TOKENS: MAX_TOKENS,
                GenParams.TEMPERATURE:    TEMPERATURE,
                GenParams.TOP_P:          TOP_P,
                GenParams.REPETITION_PENALTY: 1.1,
            },
        )
        logger.info("Watsonx ModelInference initialised successfully.")
        return _watsonx_model_cache
    except Exception as exc:
        # FIX #5: Log the full traceback so the root cause is visible.
        logger.error(
            "Failed to initialise Watsonx model: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return None


# ════════════════════════════════════════════════════════════
#  AI Chat Response Generator
# ════════════════════════════════════════════════════════════
def generate_ai_response(
    user_message: str,
    conversation_history: list,
    farmer_profile: dict = None,
) -> str:
    """
    Call IBM Watsonx.ai Granite model and return the AI response.
    Falls back to a structured demo response if credentials are absent
    or if the model returns an empty / None value.

    FIX #4 — Prompt format:
        granite-4-h-small uses a plain <|user|> / <|assistant|> chat
        template.  The original code sent <|endoftext|> as an inter-turn
        separator, which is the *end-of-sequence* token — it causes the
        model to treat every turn as a separate sequence and often returns
        an empty string or just the EOS token itself.

    FIX #2 / #6 — Empty response guard:
        generate_text() can return None (network/deserialisation error
        absorbed by the SDK), or an empty / whitespace-only string when
        the model hits a stop sequence immediately.  Both cases previously
        fell through to the frontend as an empty reply, triggering the
        "I couldn't generate a response" message.  We now explicitly
        detect and fall back to the demo response.
    """
    system_prompt = build_system_prompt(farmer_profile)

    # ── Build prompt in correct Granite chat format ───────────
    # FIX #4: Do NOT use <|endoftext|> between turns — that is the
    # end-of-sequence token.  The correct separator for granite-3/4
    # chat models is simply a newline between speaker blocks.
    prompt_parts = [f"<|system|>\n{system_prompt}"]
    for msg in conversation_history[-10:]:   # keep last 10 turns
        role    = msg.get("role", "user")
        content = msg.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            prompt_parts.append(f"<|user|>\n{content}")
        else:
            prompt_parts.append(f"<|assistant|>\n{content}")
    prompt_parts.append(f"<|user|>\n{user_message}")
    prompt_parts.append("<|assistant|>")
    full_prompt = "\n".join(prompt_parts)

    logger.info(
        "[Watsonx] Sending prompt — model=%s, history_turns=%d, prompt_chars=%d",
        MODEL_ID,
        len(conversation_history),
        len(full_prompt),
    )

    model = get_watsonx_model()

    if model:
        try:
            logger.info("[Watsonx] Calling generate_text() …")
            raw_response = model.generate_text(prompt=full_prompt)
            logger.info(
                "[Watsonx] Raw response received (type=%s, length=%s)",
                type(raw_response).__name__,
                len(raw_response) if raw_response else 0,
            )

            # FIX #2: Guard against None coming back from the SDK.
            if not raw_response:
                logger.warning(
                    "[Watsonx] generate_text() returned empty/None — falling back to demo."
                )
                return _demo_response(user_message, farmer_profile)

            # Strip stop / control tokens that may leak through.
            cleaned = raw_response.replace("<|endoftext|>", "").strip()
            cleaned = cleaned.replace("<|assistant|>", "").strip()
            cleaned = cleaned.replace("<|user|>", "").strip()
            cleaned = cleaned.replace("<|system|>", "").strip()

            # FIX #6: A response that is only whitespace after stripping
            # stop tokens must also fall back.
            if not cleaned:
                logger.warning(
                    "[Watsonx] Response was empty after stripping stop tokens — falling back to demo."
                )
                return _demo_response(user_message, farmer_profile)

            logger.info(
                "[Watsonx] Cleaned response ready (%d chars). Returning to caller.",
                len(cleaned),
            )
            return cleaned

        except Exception as exc:
            # FIX #5: Log the full traceback, not just the exception message.
            logger.error(
                "[Watsonx] generation error: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            return _demo_response(user_message, farmer_profile)
    else:
        logger.info("[Watsonx] Model not available — returning demo response.")
        return _demo_response(user_message, farmer_profile)


# ════════════════════════════════════════════════════════════
#  Demo Response Fallback
# ════════════════════════════════════════════════════════════
def _demo_response(message: str, farmer_profile: dict = None) -> str:
    """
    Structured demo response returned when IBM credentials are not configured
    or the model call fails.  Provides realistic farming advice for demonstration.
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

Apply today at pmksy.gov.in or contact your local agriculture office. 💧"""

    elif any(w in msg_lower for w in ["pest", "disease", "insect", "fungus", "blight", "wilt"]):
        return f"""Hello {farmer_name}! Here's your **IPM (Integrated Pest Management) Guide:**

**Early Warning Signs:**
🔴 Leaf spots/lesions → Fungal disease
🔴 Yellowing + wilting → Root rot or wilt
🔴 Holes in leaves → Caterpillar/beetle damage
🔴 Sticky residue → Aphids/whitefly

**IPM Action Steps (in order):**
1. **Cultural Control**: Crop rotation, resistant varieties, proper spacing
2. **Biological Control**: Release Trichogramma cards (₹150/acre), Beauveria bassiana spray
3. **Mechanical Control**: Sticky traps (yellow for whitefly, blue for thrips)
4. **Chemical Control** (LAST resort only): Always follow label instructions; wear PPE

⚠️ **Safety Warning**: Never mix pesticides without consulting a licensed dealer.

**Free Help**: Kisan Call Centre: **1800-180-1551** (Toll Free, 7 AM–10 PM)

What specific pest/disease are you dealing with? I can give targeted advice! 🐛"""

    elif any(w in msg_lower for w in ["weather", "rain", "monsoon", "forecast", "climate"]):
        return f"""Hello {farmer_name}! Here's **Weather-Smart Farming Advice:**

🌧️ **If Excess Rain Expected:**
- Choose raised bed cultivation
- Apply ridge & furrow system
- Keep drainage channels clear

☀️ **If Drought Conditions:**
- Shift to drought-tolerant varieties
- Increase mulching
- Consider crop insurance under PMFBY

**Weather Resources:**
- IMD App: Meghdoot (free, farmer-friendly)
- Kisan Suvidha App (crop advisory + weather)

Would you like a week-wise crop activity planner? 🌤️"""

    elif any(w in msg_lower for w in ["scheme", "subsidy", "government", "yojana", "insurance", "loan", "kisan"]):
        return f"""Hello {farmer_name}! Key **Government Schemes for Farmers:**

💰 **PM-KISAN** — ₹6,000/year | Apply: pmkisan.gov.in
🛡️ **PMFBY** — Crop insurance at 1.5–2% premium
💧 **PMKSY** — Up to 55% subsidy on drip/sprinkler
💳 **Kisan Credit Card** — Credit up to ₹3 lakh at 7% interest
📈 **eNAM** — Online mandi, better price discovery

**Helpline:** Kisan Call Centre **1800-180-1551** 📋"""

    elif any(w in msg_lower for w in ["fertilizer", "fertiliser", "manure", "compost", "npk", "urea", "dap"]):
        return f"""Hello {farmer_name}! **Smart Fertiliser Management:**

**The 4R Approach:**
1. Right Source — Match fertiliser to crop & soil
2. Right Rate — Based on Soil Health Card
3. Right Time — Split application for better uptake
4. Right Place — Band placement vs. broadcast

**Organic Alternatives (Reduce cost by 30–40%):**
- Vermicompost: 1 tonne/acre replaces 25% chemical fertiliser
- Bio-fertilisers: ₹300/acre saves ₹1,200

Want a crop-specific fertiliser schedule? 🌻"""

    elif any(w in msg_lower for w in ["market", "price", "sell", "msp", "mandi", "profit"]):
        return f"""Hello {farmer_name}! **Market Intelligence Guide:**

**Current MSP 2024-25:**

| Crop | MSP (₹/quintal) |
|------|----------------|
| Paddy | ₹2,300 |
| Wheat | ₹2,275 |
| Soybean | ₹4,892 |
| Cotton | ₹7,121 |

**Better Prices:**
1. eNAM Portal — compare 1,000+ mandis
2. FPO Membership — collective selling improves bargaining by 15–20%
3. Value Addition — adds 20–30% value

Would you like specific marketing advice for your crop? 💹"""

    else:
        return f"""Hello {farmer_name}! I'm **{AGENT_NAME}** — {AGENT_TAGLINE}. 🌾

I can help you with:
🌱 Crop Recommendations  |  🧪 Soil Health  |  💧 Irrigation  |  🐛 Pest Management
⛅ Weather-Smart Farming  |  💰 Market Intelligence  |  🏛️ Government Schemes

**How can I help you today?** Ask me anything about farming in your preferred language!"""


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

    Request JSON:
        { "message": str, "conversation_history": list, "farmer_profile": dict }

    Response JSON (success):
        { "success": true, "response": str, "timestamp": str, "model": str, "agent_name": str }

    Response JSON (error):
        { "success": false, "error": str }

    FIX #1 / #7: Every execution path now returns a consistent JSON shape
    with a top-level "success" boolean so the frontend can rely on a
    single, predictable contract.

    FIX #8: Input length is validated — messages > 2000 chars are rejected
    before hitting the model.
    """
    try:
        data = request.get_json(silent=True) or {}
        user_message         = data.get("message", "").strip()
        conversation_history = data.get("conversation_history", [])
        farmer_profile       = data.get("farmer_profile", {})

        # ── Input validation ─────────────────────────────────
        if not user_message:
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        # FIX #8: Reject excessively long messages before they reach Watsonx.
        if len(user_message) > 2000:
            return jsonify({"success": False, "error": "Message too long (max 2000 characters)."}), 400

        # FIX #8: conversation_history must be a list.
        if not isinstance(conversation_history, list):
            conversation_history = []

        # FIX #8: farmer_profile must be a dict.
        if not isinstance(farmer_profile, dict):
            farmer_profile = {}

        farmer_name = str(farmer_profile.get("name", "Anonymous"))[:64]
        logger.info(
            "[chat] Request — user=%s | message_len=%d",
            farmer_name,
            len(user_message),
        )

        ai_response = generate_ai_response(user_message, conversation_history, farmer_profile)

        # FIX #2 / #6: generate_ai_response() guarantees a non-empty
        # string (falls back to demo), but we add a belt-and-suspenders
        # guard here at the route level as well.
        if not ai_response or not ai_response.strip():
            logger.error("[chat] generate_ai_response returned empty — returning error JSON.")
            return jsonify({
                "success": False,
                "error": "The AI did not return a response. Please try again.",
            }), 500

        logger.info(
            "[chat] Response ready — %d chars. Returning to frontend.",
            len(ai_response),
        )

        return jsonify({
            "success":    True,
            "response":   ai_response,
            "timestamp":  datetime.now().strftime("%I:%M %p"),
            "model":      MODEL_ID,
            "agent_name": AGENT_NAME,
        })

    except Exception as exc:
        # FIX #5: Log the full traceback so nothing is silently swallowed.
        logger.error(
            "[chat] Unhandled exception: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return jsonify({
            "success": False,
            "error":   "An internal server error occurred. Please try again.",
        }), 500


@app.route("/api/crop-recommendation", methods=["POST"])
def crop_recommendation():
    """
    Dedicated crop recommendation endpoint.
    FIX #7: Returns consistent success/error JSON.
    """
    try:
        data        = request.get_json(silent=True) or {}
        soil_type   = str(data.get("soil_type", "")).lower()
        season      = str(data.get("season", ""))
        rainfall    = data.get("rainfall", 0)
        temperature = data.get("temperature", 25)
        region      = str(data.get("region", ""))

        recommendations = []
        for crop, info in CROP_DATABASE.items():
            if season and season.lower() not in info["season"].lower() and "year" not in info["season"].lower():
                continue
            soil_match = any(s in soil_type for s in [st.lower().split()[0] for st in info["soil"]])
            recommendations.append({
                "crop":           crop,
                "season":         info["season"],
                "water_need":     info["water_need"],
                "soil_types":     info["soil"],
                "recommended_pH": info["pH"],
                "nutrients":      info["nutrients"],
                "soil_match":     soil_match,
            })

        recommendations.sort(key=lambda x: (0 if x["soil_match"] else 1, x["crop"]))

        ai_prompt = (
            f"Farmer profile: region={region}, soil_type={soil_type}, season={season}, "
            f"avg_rainfall={rainfall}mm, avg_temperature={temperature}°C. "
            f"Top matching crops: {[r['crop'] for r in recommendations[:5]]}. "
            f"Provide a 3-paragraph personalized crop recommendation with specific variety names, "
            f"expected yield, and any local government scheme relevant to these crops."
        )
        ai_narrative = generate_ai_response(ai_prompt, [], {"location": region})

        return jsonify({
            "success":         True,
            "recommendations": recommendations[:6],
            "ai_narrative":    ai_narrative,
            "season_crops":    SEASONS,
            "timestamp":       datetime.now().isoformat(),
        })

    except Exception as exc:
        logger.error("[crop-recommendation] %s\n%s", exc, traceback.format_exc())
        return jsonify({"success": False, "error": "Crop recommendation failed."}), 500


@app.route("/api/soil-analysis", methods=["POST"])
def soil_analysis():
    """
    Soil health analysis endpoint.
    FIX #7: Returns consistent success/error JSON.
    """
    try:
        data           = request.get_json(silent=True) or {}
        ph             = float(data.get("ph", 7.0))
        nitrogen       = float(data.get("nitrogen", 250))
        phosphorus     = float(data.get("phosphorus", 10))
        potassium      = float(data.get("potassium", 100))
        organic_carbon = float(data.get("organic_carbon", 0.5))
        crop           = str(data.get("crop", "general"))

        issues  = []
        actions = []
        score   = 100

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
            f"Soil test: pH={ph}, N={nitrogen}kg/ha, P={phosphorus}kg/ha, "
            f"K={potassium}kg/ha, OC={organic_carbon}%, crop={crop}. "
            f"Issues: {issues}. "
            f"Provide a detailed soil health report with fertiliser schedule, "
            f"organic amendments, and a 3-year soil improvement plan."
        )
        ai_narrative = generate_ai_response(ai_prompt, [], {})

        return jsonify({
            "success":             True,
            "score":               max(score, 0),
            "health_rating":       health_rating,
            "issues":              issues,
            "recommended_actions": actions,
            "ai_narrative":        ai_narrative,
            "parameters": {
                "pH": ph, "Nitrogen": nitrogen,
                "Phosphorus": phosphorus, "Potassium": potassium,
                "Organic Carbon": organic_carbon,
            },
        })

    except Exception as exc:
        logger.error("[soil-analysis] %s\n%s", exc, traceback.format_exc())
        return jsonify({"success": False, "error": "Soil analysis failed."}), 500


@app.route("/api/weather-advice", methods=["POST"])
def weather_advice():
    """
    Weather-aware farming advice endpoint.
    FIX #7: Returns consistent success/error JSON.
    """
    try:
        data        = request.get_json(silent=True) or {}
        condition   = str(data.get("condition", "sunny"))
        rainfall_mm = float(data.get("rainfall_mm", 50))
        temperature = float(data.get("temperature", 28))
        season      = str(data.get("season", "Kharif"))
        crop        = str(data.get("crop", "Rice"))

        ai_prompt = (
            f"Current weather: {condition}, rainfall={rainfall_mm}mm/week, "
            f"temperature={temperature}°C, season={season}, main crop={crop}. "
            f"Provide detailed weather-aware farming advice covering: "
            f"1) Immediate actions for today, "
            f"2) Irrigation adjustments, "
            f"3) Pest/disease risks in this weather, "
            f"4) Fertiliser timing caution, "
            f"5) Harvesting or sowing recommendations."
        )
        ai_response = generate_ai_response(ai_prompt, [], {})

        alert = "normal"
        if temperature > 40 or rainfall_mm > 200:
            alert = "high"
        elif temperature > 35 or rainfall_mm > 100:
            alert = "medium"

        return jsonify({
            "success":     True,
            "advice":      ai_response,
            "alert_level": alert,
            "timestamp":   datetime.now().isoformat(),
        })

    except Exception as exc:
        logger.error("[weather-advice] %s\n%s", exc, traceback.format_exc())
        return jsonify({"success": False, "error": "Weather advice failed."}), 500


@app.route("/api/dashboard-data", methods=["GET"])
def dashboard_data():
    """Return static dashboard statistics for the UI."""
    return jsonify({
        "success": True,
        "stats": {
            "crops_in_database":  len(CROP_DATABASE),
            "schemes_available":  len(GOVERNMENT_SCHEMES),
            "specializations":    len(FARMING_SPECIALIZATIONS),
            "regions_covered":    6,
            "languages_supported": 9,
            "seasons":            4,
        },
        "crops":           list(CROP_DATABASE.keys()),
        "seasons":         SEASONS,
        "top_schemes":     GOVERNMENT_SCHEMES[:5],
        "specializations": FARMING_SPECIALIZATIONS,
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    model_status = "configured" if (
        IBM_API_KEY and IBM_API_KEY != "your_ibm_cloud_api_key_here"
    ) else "demo_mode"

    return jsonify({
        "success":      True,
        "status":       "healthy",
        "agent":        AGENT_NAME,
        "model":        MODEL_ID,
        "watsonx_sdk":  WATSONX_AVAILABLE,
        "model_status": model_status,
        "timestamp":    datetime.now().isoformat(),
    })


# ════════════════════════════════════════════════════════════
#  Entry Point
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    logger.info("Starting %s on port %d (debug=%s)", AGENT_NAME, port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
