import base64
import json
import os
import sys
from pathlib import Path

import streamlit as st

from monster_mentor import progress as prog
from monster_mentor.gemma_client import DEFAULT_MODEL, MODELS, GemmaClient, GemmaError
from monster_mentor.loader import ROOT, TOPIC_NAMES, load_lessons, load_monsters
from monster_mentor.prompts import monster_system
from monster_mentor.quiz_engine import grade_quiz, shuffle_options

st.set_page_config(
    page_title="Monster Mentor · Halloween Concept Academy",
    page_icon="👾",
    layout="centered",
    initial_sidebar_state="expanded",
)

TOPIC_EMOJI = {"os": "🖥️", "dbms": "🗄️", "ml": "🧠"}
TOPIC_BADGES = {"os": "Operating Systems", "dbms": "Database Systems", "ml": "Machine Learning"}
TOPIC_BLURB = {
    "os": "Master deadlocks, memory paging, and process isolation through spooky Halloween analogies.",
    "dbms": "Conquer B-Tree indexing, normalization forms, and ACID transactions with friendly crypt creatures.",
    "ml": "Tackle bias-variance tradeoffs, gradient descent, and overfitting with playful Halloween habits.",
}


def render_html(html_str, *args, **kwargs):
    """Flushes each line to column 0 so CommonMark never misinterprets it as an indented code block."""
    clean = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean, unsafe_allow_html=True)


def get_bg_data_uri():
    """Retrieve base64 URI of the clean, text-free Halloween background image."""
    local_path = ROOT / "assets" / "halloween_bg.jpg"
    if local_path.exists():
        try:
            b64 = base64.b64encode(local_path.read_bytes()).decode()
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass
    return ""


def inject_css(theme_mode="wallpaper"):
    """Inject rich, polished CSS styling supporting clean Halloween Wallpaper, Mystic Dark, and Studio Light themes."""
    bg_uri = get_bg_data_uri()

    if theme_mode == "clean":
        bg_app_css = """
        .stApp {
            background: linear-gradient(180deg, #faf9f6 0%, #f3f0e8 100%);
            color: #1e293b;
        }
        .hero-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            color: #0f172a;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        }
        .hero-title { color: #0f172a; }
        .hero-subtitle { color: #475569; }
        .story-card-monster {
            background: #ffffff;
            border: 1px solid #fed7aa;
            border-left: 5px solid #f97316;
            color: #1e293b;
            box-shadow: 0 4px 14px rgba(249, 115, 22, 0.06);
        }
        .story-card-tech {
            background: #ffffff;
            border: 1px solid #bfdbfe;
            border-left: 5px solid #3b82f6;
            color: #1e293b;
            box-shadow: 0 4px 14px rgba(59, 130, 246, 0.06);
        }
        .story-body-text { color: #334155; }
        
        /* Quiz Visibility - Clean Light Mode */
        div[data-testid="stForm"] {
            background: #ffffff !important;
            border: 1.5px solid #e2e8f0 !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04) !important;
        }
        div[data-testid="stRadio"] > label,
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"],
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"] p,
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"] span {
            color: #0f172a !important;
            font-family: 'Outfit', sans-serif !important;
            font-size: 1.15rem !important;
            font-weight: 800 !important;
            text-shadow: none !important;
            margin-bottom: 0.6rem !important;
            display: block !important;
        }
        div[data-testid="stRadio"] [role="radiogroup"] > label {
            background: #ffffff !important;
            border: 1.5px solid #e2e8f0 !important;
            color: #1e293b !important;
        }
        div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
            border-color: #f97316 !important;
            background: #fff7ed !important;
        }
        div[data-testid="stRadio"] [role="radiogroup"] > label p {
            color: #1e293b !important;
            font-weight: 600 !important;
        }
        """
    elif theme_mode == "dark":
        bg_app_css = """
        .stApp {
            background: radial-gradient(circle at 50% 0%, #1a1233 0%, #0c0f1d 55%, #070913 100%);
            color: #f1f5f9;
        }
        .hero-card {
            background: rgba(26, 32, 56, 0.95);
            border: 1px solid rgba(255, 117, 24, 0.35);
            color: #f8fafc;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(255, 117, 24, 0.12);
        }
        .hero-title { color: #ffffff; }
        .hero-subtitle { color: #cbd5e1; }
        .story-card-monster {
            background: rgba(26, 21, 38, 0.92);
            border: 1px solid rgba(255, 117, 24, 0.4);
            border-left: 5px solid #ff7518;
            color: #f8fafc;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        }
        .story-card-tech {
            background: rgba(16, 28, 48, 0.92);
            border: 1px solid rgba(56, 189, 248, 0.4);
            border-left: 5px solid #38bdf8;
            color: #f8fafc;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        }
        .story-body-text { color: #e2e8f0; }
        
        /* Quiz Visibility - Dark Mode */
        div[data-testid="stForm"] {
            background: rgba(20, 16, 38, 0.85) !important;
            border: 1.5px solid rgba(255, 117, 24, 0.35) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important;
        }
        div[data-testid="stRadio"] > label,
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"],
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"] p,
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"] span {
            color: #ffffff !important;
            font-family: 'Outfit', sans-serif !important;
            font-size: 1.15rem !important;
            font-weight: 800 !important;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8) !important;
            margin-bottom: 0.6rem !important;
            display: block !important;
        }
        div[data-testid="stRadio"] [role="radiogroup"] > label {
            background: #171d33 !important;
            border: 1.5px solid #283354 !important;
            color: #f1f5f9 !important;
        }
        div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
            border-color: #ff7518 !important;
            background: #232b45 !important;
        }
        div[data-testid="stRadio"] [role="radiogroup"] > label p {
            color: #f8fafc !important;
            font-weight: 600 !important;
        }
        """
    else:
        # Default: Clean text-free Halloween Wallpaper with Atmospheric Glassmorphism
        bg_rule = f"url('{bg_uri}') no-repeat center center fixed" if bg_uri else "none"
        bg_app_css = f"""
        .stApp {{
            background: linear-gradient(180deg, rgba(14, 9, 30, 0.82) 0%, rgba(8, 6, 18, 0.92) 100%),
                        {bg_rule};
            background-size: cover;
            color: #f8fafc;
        }}
        .hero-card {{
            background: rgba(24, 17, 48, 0.86);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 117, 24, 0.4);
            color: #f8fafc;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.55), 0 0 20px rgba(255, 117, 24, 0.15);
        }}
        .hero-title {{ color: #ffffff; text-shadow: 0 2px 12px rgba(0,0,0,0.6); }}
        .hero-subtitle {{ color: #e2e8f0; }}
        .story-card-monster {{
            background: rgba(28, 19, 52, 0.88);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 117, 24, 0.45);
            border-left: 5px solid #ff7518;
            color: #f8fafc;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 0 0 16px rgba(255, 117, 24, 0.15);
        }}
        .story-card-tech {{
            background: rgba(16, 25, 52, 0.88);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(56, 189, 248, 0.45);
            border-left: 5px solid #38bdf8;
            color: #f8fafc;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 0 0 16px rgba(56, 189, 248, 0.15);
        }}
        .story-body-text {{ color: #f1f5f9; }}
        
        /* Quiz Form Box - Prominent & Visible */
        div[data-testid="stForm"] {{
            background: rgba(22, 16, 44, 0.85) !important;
            backdrop-filter: blur(14px) !important;
            border: 1.5px solid rgba(255, 117, 24, 0.35) !important;
            border-radius: 20px !important;
            padding: 1.6rem !important;
            box-shadow: 0 10px 32px rgba(0, 0, 0, 0.5) !important;
        }}

        /* Quiz Question Title - 100% Bright & Visible */
        div[data-testid="stRadio"] > label,
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"],
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"] p,
        div[data-testid="stRadio"] [data-testid="stWidgetLabel"] span {{
            color: #ffffff !important;
            font-family: 'Outfit', sans-serif !important;
            font-size: 1.18rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.01em !important;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.9) !important;
            margin-bottom: 0.65rem !important;
            display: block !important;
            line-height: 1.45 !important;
        }}

        /* Quiz Option Choices */
        div[data-testid="stRadio"] [role="radiogroup"] > label {{
            background: rgba(28, 20, 56, 0.90) !important;
            backdrop-filter: blur(10px) !important;
            border: 1.5px solid rgba(255, 117, 24, 0.25) !important;
            border-radius: 12px !important;
            padding: 0.85rem 1.25rem !important;
            margin-bottom: 0.4rem !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
        }}
        div[data-testid="stRadio"] [role="radiogroup"] > label:hover {{
            border-color: #ff7518 !important;
            background: rgba(48, 30, 92, 0.98) !important;
            transform: translateX(4px) !important;
            box-shadow: 0 0 16px rgba(255, 117, 24, 0.35) !important;
        }}
        div[data-testid="stRadio"] [role="radiogroup"] > label p,
        div[data-testid="stRadio"] [role="radiogroup"] [data-testid="stMarkdownContainer"] p {{
            color: #ffffff !important;
            font-size: 1.02rem !important;
            font-weight: 600 !important;
        }}
        """

    render_html(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800;900&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

/* Sidebar - Matches Screenshot Reference */
[data-testid="stSidebar"] {{
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0;
    box-shadow: 2px 0 14px rgba(0, 0, 0, 0.05);
}}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {{
    font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif;
    color: #1e293b !important;
    font-weight: 700;
    font-size: 1.45rem;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: #64748b !important;
    font-size: 0.88rem;
    margin-bottom: 1rem;
}}
[data-testid="stSidebar"] label {{
    font-size: 0.92rem;
    font-weight: 600;
    color: #334155 !important;
}}

/* Status Badge - Mint Green */
.status-ready {{
    background: #e6f4ea !important;
    border: 1px solid #ceead6 !important;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    color: #137333 !important;
    font-size: 0.92rem;
    font-weight: 600;
    margin: 0.8rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
.status-warn {{
    background: #fef7e0 !important;
    border: 1px solid #feefc3 !important;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    color: #b06000 !important;
    font-size: 0.9rem;
    font-weight: 500;
    margin: 0.8rem 0;
}}

/* Hero Card Layout */
.hero-card {{
    border-radius: 20px;
    padding: 1.5rem 1.8rem;
    display: flex;
    align-items: center;
    gap: 1.6rem;
    margin-bottom: 1.2rem;
    transition: all 0.25s ease;
}}
.hero-card:hover {{
    transform: translateY(-2px);
}}
.hero-svg-box {{
    flex: 0 0 auto;
}}
.hero-text-box {{
    flex: 1 1 auto;
}}
.topic-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(255, 117, 24, 0.15);
    color: #ff7518;
    border: 1px solid rgba(255, 117, 24, 0.4);
    border-radius: 999px;
    padding: 0.22rem 0.85rem;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}}
.hero-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0 0 0.35rem 0;
    line-height: 1.25;
}}
.hero-subtitle {{
    font-size: 1.02rem;
    margin: 0;
    line-height: 1.45;
}}

/* Story Cards */
.story-card-monster, .story-card-tech {{
    border-radius: 16px;
    padding: 1.35rem 1.6rem;
    margin-bottom: 1.1rem;
    transition: transform 0.2s ease;
}}
.story-card-monster:hover, .story-card-tech:hover {{
    transform: translateY(-1px);
}}
.card-header-label {{
    font-family: 'Outfit', sans-serif;
    font-size: 0.88rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.55rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}}
.label-orange {{ color: #ff7518; }}
.label-blue {{ color: #38bdf8; }}
.story-body-text {{
    font-size: 1.05rem;
    line-height: 1.68;
    margin: 0;
}}

/* Radio Group Alignment */
div[data-testid="stRadio"] [role="radiogroup"] {{
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}}

/* Buttons */
.stButton > button, .stFormSubmitButton > button {{
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1.4rem !important;
    transition: all 0.25s ease !important;
}}
.stFormSubmitButton > button[kind="primary"], .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #ff7518 0%, #ea580c 100%) !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(255, 117, 24, 0.35) !important;
    color: #ffffff !important;
}}
.stFormSubmitButton > button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(255, 117, 24, 0.5) !important;
}}

/* Purple Accent Progress Bar */
div[data-testid="stProgressBar"] > div > div {{
    background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #ff7518 100%) !important;
}}

/* Score Feedback Banners */
.score-banner-pass {{
    background: rgba(16, 185, 129, 0.2) !important;
    border: 1px solid #10b981 !important;
    border-radius: 14px;
    padding: 1rem 1.3rem;
    color: #34d399 !important;
    font-weight: 700;
    font-size: 1.15rem;
    margin: 1rem 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.score-banner-try {{
    background: rgba(245, 158, 11, 0.2) !important;
    border: 1px solid #f59e0b !important;
    border-radius: 14px;
    padding: 1rem 1.3rem;
    color: #fbbf24 !important;
    font-weight: 700;
    font-size: 1.15rem;
    margin: 1rem 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.answer-feedback {{
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    margin: 0.5rem 0;
    font-size: 0.98rem;
    line-height: 1.5;
}}
.feedback-ok {{
    background: rgba(16, 185, 129, 0.15) !important;
    border: 1px solid #059669 !important;
    color: #6ee7b7 !important;
}}
.feedback-no {{
    background: rgba(239, 68, 68, 0.18) !important;
    border: 1px solid #dc2626 !important;
    color: #fca5a5 !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.5rem;
    margin-bottom: 1.2rem;
    border-bottom: 2px solid rgba(255, 255, 255, 0.1);
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.98rem;
    padding: 0.65rem 1.1rem;
    border-radius: 10px 10px 0 0;
    color: #cbd5e1;
}}
.stTabs [aria-selected="true"] {{
    color: #ff7518 !important;
    border-bottom: 2px solid #ff7518 !important;
}}

/* Halloween Animation Keyframes */
@keyframes candleFlicker {{
    0%, 100% {{ opacity: 1; filter: drop-shadow(0 0 8px #ff9f1c); }}
    25% {{ opacity: 0.85; filter: drop-shadow(0 0 4px #f97316); }}
    50% {{ opacity: 0.96; filter: drop-shadow(0 0 10px #fbbf24); }}
    75% {{ opacity: 0.8; filter: drop-shadow(0 0 5px #ea580c); }}
}}

@keyframes floatGhost {{
    0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
    50% {{ transform: translateY(-8px) rotate(2deg); }}
}}

@keyframes boltSpark {{
    0%, 100% {{ filter: drop-shadow(0 0 2px #22c55e); }}
    50% {{ filter: drop-shadow(0 0 9px #4ade80); }}
}}

@keyframes spiderDangle {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(6px); }}
}}

@keyframes batWingFlap {{
    0%, 100% {{ transform: scaleX(1); }}
    50% {{ transform: scaleX(0.85); }}
}}

@keyframes batFlyBanner {{
    0% {{ transform: translate(-30px, 15px) scale(0.75); }}
    50% {{ transform: translate(140px, 0px) scale(0.95); }}
    100% {{ transform: translate(320px, 18px) scale(0.8); }}
}}

{bg_app_css}
</style>
        """
    )


def realistic_pumpkin_svg(width=300):
    """Render a 3D-shaded vector Jack-o'-Lantern with glowing flame inside and stem."""
    return (
        f'<svg width="{width}" height="{width}" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg">'
        f'<defs>'
        f'<filter id="flameGlow" x="-30%" y="-30%" width="160%" height="160%">'
        f'<feGaussianBlur stdDeviation="8" result="blur"/>'
        f'<feComposite in="SourceGraphic" in2="blur" operator="over"/>'
        f'</filter>'
        f'<radialGradient id="pSkin" cx="50%" cy="40%" r="55%">'
        f'<stop offset="0%" stop-color="#ff9933"/>'
        f'<stop offset="65%" stop-color="#ff7518"/>'
        f'<stop offset="100%" stop-color="#c2410c"/>'
        f'</radialGradient>'
        f'<linearGradient id="pStem" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="#65a30d"/>'
        f'<stop offset="100%" stop-color="#14532d"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<ellipse cx="180" cy="335" rx="110" ry="16" fill="rgba(0,0,0,0.3)"/>'
        f'<path d="M174 95 C170 55 195 40 190 25 C178 30 172 55 160 92 Z" fill="url(#pStem)"/>'
        f'<path d="M185 45 Q210 40 215 55 Q218 65 208 65" fill="none" stroke="#65a30d" stroke-width="4" stroke-linecap="round"/>'
        f'<ellipse cx="110" cy="205" rx="72" ry="105" fill="url(#pSkin)"/>'
        f'<ellipse cx="250" cy="205" rx="72" ry="105" fill="url(#pSkin)"/>'
        f'<ellipse cx="140" cy="210" rx="72" ry="112" fill="url(#pSkin)"/>'
        f'<ellipse cx="220" cy="210" rx="72" ry="112" fill="url(#pSkin)"/>'
        f'<ellipse cx="180" cy="215" rx="68" ry="115" fill="url(#pSkin)"/>'
        f'<g style="animation: candleFlicker 2.5s infinite ease-in-out;" filter="url(#flameGlow)">'
        f'<polygon points="135,170 110,205 160,205" fill="#fef08a"/>'
        f'<polygon points="225,170 200,205 250,205" fill="#fef08a"/>'
        f'<polygon points="180,210 168,226 192,226" fill="#fef08a"/>'
        f'<path d="M115 245 L138 260 L158 248 L180 262 L202 248 L222 260 L245 245 L228 280 L205 268 L180 282 L155 268 L132 280 Z" fill="#fef08a"/>'
        f'</g>'
        f'</svg>'
    )


def cute_3d_ghost_svg():
    """Render a friendly, floating 3D glowing ghost."""
    return (
        f'<svg width="84" height="96" viewBox="0 0 100 115" xmlns="http://www.w3.org/2000/svg" style="animation: floatGhost 3s infinite ease-in-out;">'
        f'<defs>'
        f'<radialGradient id="ghostShade" cx="35%" cy="30%" r="65%">'
        f'<stop offset="0%" stop-color="#ffffff"/>'
        f'<stop offset="70%" stop-color="#f1f5f9"/>'
        f'<stop offset="100%" stop-color="#cbd5e1"/>'
        f'</radialGradient>'
        f'</defs>'
        f'<path d="M20 55 C20 25 35 12 50 12 C65 12 80 25 80 55 C80 82 85 96 78 98 C72 95 67 101 62 96 C57 101 52 95 47 99 C42 95 37 101 32 96 C26 100 20 94 20 55 Z" fill="url(#ghostShade)" filter="drop-shadow(0 4px 10px rgba(0,0,0,0.15))"/>'
        f'<ellipse cx="38" cy="45" rx="5" ry="7" fill="#0f172a"/>'
        f'<ellipse cx="62" cy="45" rx="5" ry="7" fill="#0f172a"/>'
        f'<circle cx="39" cy="43" r="2" fill="#ffffff"/>'
        f'<circle cx="63" cy="43" r="2" fill="#ffffff"/>'
        f'<circle cx="30" cy="54" r="4" fill="#f43f5e" opacity="0.4"/>'
        f'<circle cx="70" cy="54" r="4" fill="#f43f5e" opacity="0.4"/>'
        f'<ellipse cx="50" cy="58" rx="4" ry="5" fill="#0f172a"/>'
        f'</svg>'
    )


def haunted_landscape_svg():
    """Render a sleek panoramic Halloween night landscape with animated flying bats and harvest moon."""
    return (
        f'<svg class="banner-svg" width="100%" height="90" viewBox="0 0 1140 120" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<defs>'
        f'<linearGradient id="skyGrad" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="#140f2d"/>'
        f'<stop offset="50%" stop-color="#241442"/>'
        f'<stop offset="100%" stop-color="#120c24"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<rect width="1140" height="120" rx="16" fill="url(#skyGrad)"/>'
        f'<circle cx="980" cy="48" r="32" fill="#fef08a" opacity="0.9" filter="drop-shadow(0 0 15px rgba(254,240,138,0.5))"/>'
        f'<circle cx="992" cy="44" r="30" fill="url(#skyGrad)" opacity="0.8"/>'
        f'<path d="M0 120 L0 102 Q120 85 240 102 T480 96 T720 104 T960 92 T1140 102 L1140 120 Z" fill="#080711"/>'
        f'<path d="M780 120 L780 72 L792 60 L804 72 L804 120 M804 80 L824 68 L844 80 L844 120" fill="#090814"/>'
        f'<g style="animation: batFlyBanner 14s infinite linear;">'
        f'<path d="M120 38 Q130 28 136 34 Q142 28 152 38 Q144 42 136 38 Q128 42 120 38 Z" fill="#f8fafc" opacity="0.7"/>'
        f'<path d="M165 48 Q172 40 177 44 Q182 40 190 48 Q183 51 177 48 Q171 51 165 48 Z" fill="#cbd5e1" opacity="0.5"/>'
        f'</g>'
        f'<text x="42" y="70" fill="#f97316" font-family="Outfit, sans-serif" font-size="24" font-weight="800" letter-spacing="1.5">🎃 MONSTER MENTOR · HALLOWEEN ACADEMY 👾</text>'
        f'<text x="44" y="94" fill="#94a3b8" font-family="Plus Jakarta Sans, sans-serif" font-size="13">Demystifying OS, DBMS & Machine Learning with playful monster tales</text>'
        f'</svg>'
    )


def monster_svg(m, width=128):
    """Render crisp, friendly vector avatars with custom Halloween themes and animations."""
    c = m.get("color", "#ff7518")
    name = m.get("name", "").lower()

    if "gobbler" in name or "jack" in name:
        # Jack-o'-Gobbler (Glowing animated Jack-o'-Lantern)
        return (
            f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">'
            f'<ellipse cx="60" cy="112" rx="36" ry="6" fill="rgba(0,0,0,0.12)"/>'
            f'<path d="M57 26 C56 16 66 12 65 8 C61 10 59 18 53 26 Z" fill="#15803d"/>'
            f'<ellipse cx="60" cy="68" rx="46" ry="40" fill="{c}"/>'
            f'<ellipse cx="60" cy="68" rx="34" ry="40" fill="#f97316"/>'
            f'<ellipse cx="60" cy="68" rx="20" ry="40" fill="#fb923c"/>'
            f'<g style="animation: candleFlicker 2.2s infinite ease-in-out;">'
            f'<polygon points="44,56 36,68 52,68" fill="#fef08a"/>'
            f'<polygon points="76,56 68,68 84,68" fill="#fef08a"/>'
            f'<polygon points="60,70 56,76 64,76" fill="#fef08a"/>'
            f'<path d="M38 82 L46 88 L54 82 L62 88 L70 82 L78 88 L84 82 L76 94 L68 88 L60 94 L52 88 L44 94 Z" fill="#fef08a"/>'
            f'</g>'
            f'</svg>'
        )

    if "panda" in name or "phantom" in name:
        # Phantom Panda (Ghost panda with gentle float)
        return (
            f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" style="animation: floatGhost 3.2s infinite ease-in-out;">'
            f'<ellipse cx="60" cy="112" rx="32" ry="6" fill="rgba(0,0,0,0.1)"/>'
            f'<circle cx="38" cy="38" r="12" fill="#475569"/>'
            f'<circle cx="82" cy="38" r="12" fill="#475569"/>'
            f'<path d="M32 64 C32 38 44 26 60 26 C76 26 88 38 88 64 C88 88 90 104 86 106 C80 102 76 108 72 104 C66 108 62 102 58 106 C52 102 48 108 44 104 C38 108 34 102 32 106 Z" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>'
            f'<ellipse cx="48" cy="56" rx="9" ry="12" fill="#475569" transform="rotate(-15 48 56)"/>'
            f'<ellipse cx="72" cy="56" rx="9" ry="12" fill="#475569" transform="rotate(15 72 56)"/>'
            f'<circle cx="49" cy="56" r="4" fill="#ffffff"/>'
            f'<circle cx="71" cy="56" r="4" fill="#ffffff"/>'
            f'<circle cx="50" cy="56" r="2" fill="#0f172a"/>'
            f'<circle cx="70" cy="56" r="2" fill="#0f172a"/>'
            f'<circle cx="36" cy="65" r="4" fill="#f43f5e" opacity="0.4"/>'
            f'<circle cx="84" cy="65" r="4" fill="#f43f5e" opacity="0.4"/>'
            f'<ellipse cx="60" cy="72" rx="4" ry="5" fill="#475569"/>'
            f'</svg>'
        )

    if "quokka" in name or "franken" in name:
        # Franken-Quokka (Stitched creature with sparking bolts)
        return (
            f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">'
            f'<ellipse cx="60" cy="112" rx="34" ry="6" fill="rgba(0,0,0,0.12)"/>'
            f'<g style="animation: boltSpark 1.8s infinite ease-in-out;">'
            f'<rect x="20" y="72" width="12" height="8" rx="2" fill="#94a3b8"/>'
            f'<rect x="88" y="72" width="12" height="8" rx="2" fill="#94a3b8"/>'
            f'</g>'
            f'<rect x="30" y="28" width="60" height="68" rx="14" fill="{c}"/>'
            f'<path d="M30 40 L30 28 C30 22 36 18 42 18 L78 18 C84 18 90 22 90 28 L90 40 L84 34 L78 42 L72 34 L66 42 L60 34 L54 42 L48 34 L42 42 Z" fill="#1e293b"/>'
            f'<line x1="42" y1="42" x2="58" y2="38" stroke="#0f172a" stroke-width="2"/>'
            f'<line x1="46" y1="37" x2="46" y2="43" stroke="#0f172a" stroke-width="1.5"/>'
            f'<line x1="52" y1="37" x2="52" y2="43" stroke="#0f172a" stroke-width="1.5"/>'
            f'<circle cx="46" cy="60" r="6" fill="#ffffff"/>'
            f'<circle cx="74" cy="60" r="6" fill="#ffffff"/>'
            f'<circle cx="48" cy="60" r="3" fill="#0f172a"/>'
            f'<circle cx="72" cy="60" r="3" fill="#0f172a"/>'
            f'<line x1="44" y1="80" x2="76" y2="80" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round"/>'
            f'<line x1="50" y1="76" x2="50" y2="84" stroke="#0f172a" stroke-width="1.5"/>'
            f'<line x1="60" y1="76" x2="60" y2="84" stroke="#0f172a" stroke-width="1.5"/>'
            f'<line x1="70" y1="76" x2="70" y2="84" stroke="#0f172a" stroke-width="1.5"/>'
            f'</svg>'
        )

    if "witch" in name or "norm" in name:
        # Witch Norm (Witch hat and magic aura)
        return (
            f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">'
            f'<ellipse cx="60" cy="112" rx="34" ry="6" fill="rgba(0,0,0,0.12)"/>'
            f'<rect x="28" y="44" width="64" height="62" rx="20" fill="{c}"/>'
            f'<ellipse cx="60" cy="46" rx="42" ry="8" fill="#4c1d95"/>'
            f'<path d="M36 46 L60 8 L84 46 Z" fill="#6d28d9"/>'
            f'<rect x="46" y="38" width="28" height="6" fill="#fbbf24"/>'
            f'<circle cx="48" cy="68" r="7" fill="#ffffff"/>'
            f'<circle cx="72" cy="68" r="7" fill="#ffffff"/>'
            f'<circle cx="49" cy="68" r="3" fill="#0f172a"/>'
            f'<circle cx="71" cy="68" r="3" fill="#0f172a"/>'
            f'<path d="M52 86 Q60 94 68 86" stroke="#0f172a" stroke-width="3" fill="none" stroke-linecap="round"/>'
            f'</svg>'
        )

    if "spider" in name or "imp" in name:
        # Crypt-Spider Imp (Hanging on bobbing web thread)
        return (
            f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" style="animation: spiderDangle 2.4s infinite ease-in-out;">'
            f'<line x1="60" y1="0" x2="60" y2="40" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="3,2"/>'
            f'<path d="M38 56 Q20 48 16 66 M38 64 Q16 64 12 78 M38 72 Q18 80 18 94" stroke="{c}" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
            f'<path d="M82 56 Q100 48 104 66 M82 64 Q104 64 108 78 M82 72 Q102 80 102 94" stroke="{c}" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
            f'<circle cx="60" cy="68" r="28" fill="{c}"/>'
            f'<circle cx="48" cy="62" r="5" fill="#fef08a"/>'
            f'<circle cx="60" cy="58" r="4" fill="#fef08a"/>'
            f'<circle cx="72" cy="62" r="5" fill="#fef08a"/>'
            f'<circle cx="49" cy="62" r="2.5" fill="#0f172a"/>'
            f'<circle cx="60" cy="58" r="2" fill="#0f172a"/>'
            f'<circle cx="71" cy="62" r="2.5" fill="#0f172a"/>'
            f'<path d="M52 78 Q60 86 68 78" stroke="#0f172a" stroke-width="2.5" fill="none"/>'
            f'</svg>'
        )

    if "bat" in name or "gremlin" in name:
        # Bat Gremlin (Flapping bat wings)
        return (
            f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">'
            f'<ellipse cx="60" cy="112" rx="34" ry="6" fill="rgba(0,0,0,0.12)"/>'
            f'<g style="animation: batWingFlap 1.4s infinite ease-in-out; transform-origin: center;">'
            f'<path d="M35 60 Q10 40 4 64 Q20 68 35 76 Z" fill="#9d174d"/>'
            f'<path d="M85 60 Q110 40 116 64 Q100 68 85 76 Z" fill="#9d174d"/>'
            f'</g>'
            f'<circle cx="60" cy="68" r="28" fill="{c}"/>'
            f'<polygon points="40,44 48,24 54,42" fill="{c}"/>'
            f'<polygon points="80,44 72,24 66,42" fill="{c}"/>'
            f'<circle cx="48" cy="64" r="6" fill="#fef08a"/>'
            f'<circle cx="72" cy="64" r="6" fill="#fef08a"/>'
            f'<circle cx="50" cy="64" r="3" fill="#0f172a"/>'
            f'<circle cx="70" cy="64" r="3" fill="#0f172a"/>'
            f'<path d="M50 82 Q60 90 70 82" stroke="#0f172a" stroke-width="2.5" fill="none"/>'
            f'<polygon points="54,82 56,88 58,82" fill="#ffffff"/>'
            f'<polygon points="62,82 64,88 66,82" fill="#ffffff"/>'
            f'</svg>'
        )

    # Trick-or-Treat Ogre (with candy bucket)
    return (
        f'<svg width="{width}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">'
        f'<ellipse cx="60" cy="112" rx="36" ry="6" fill="rgba(0,0,0,0.12)"/>'
        f'<path d="M54 26 L60 12 L66 26 Z" fill="#d97706"/>'
        f'<rect x="24" y="28" width="72" height="74" rx="24" fill="{c}"/>'
        f'<circle cx="46" cy="56" r="10" fill="#ffffff"/>'
        f'<circle cx="74" cy="56" r="10" fill="#ffffff"/>'
        f'<circle cx="48" cy="56" r="4.5" fill="#1e293b"/>'
        f'<circle cx="72" cy="56" r="4.5" fill="#1e293b"/>'
        f'<path d="M46 78 Q60 90 74 78" stroke="#1e293b" stroke-width="3" fill="none" stroke-linecap="round"/>'
        f'<ellipse cx="60" cy="94" rx="14" ry="10" fill="#f97316"/>'
        f'<polygon points="56,92 54,95 58,95" fill="#451a03"/>'
        f'<polygon points="64,92 62,95 66,95" fill="#451a03"/>'
        f'</svg>'
    )


def cheer(score, total):
    """Return celebratory and encouraging Halloween feedback based on quiz performance."""
    if total == 0:
        return "Ready when you are."
    ratio = score / total
    if ratio == 1:
        return "Spooktacular! 100% mastery!"
    if ratio >= 0.6:
        return "Passed! You got the key ideas."
    return "Tough round. Read the notes below and try a quick retry!"


@st.cache_data
def get_content():
    return load_lessons(), load_monsters()


def init_state():
    st.session_state.setdefault("progress", prog.load())
    st.session_state.setdefault("chats", {})
    st.session_state.setdefault("ai_quiz", {})
    st.session_state.setdefault("extra", [])
    st.session_state.setdefault("quiz_round", {})


def quiz_block(key, lesson, questions, client, ai_ok, monster_name):
    rnd = st.session_state["quiz_round"].get(key, 0)
    shuffled_key = f"shuf_{key}_{rnd}"
    if shuffled_key not in st.session_state:
        st.session_state[shuffled_key] = [shuffle_options(q) for q in questions]
    quiz = st.session_state[shuffled_key]
    result_key = f"result_{key}_{rnd}"

    with st.form(f"form_{key}_{rnd}"):
        picks = []
        for i, q in enumerate(quiz):
            picks.append(
                st.radio(
                    f"🎃 Question {i + 1}: {q['q']}",
                    q["options"],
                    index=None,
                    key=f"q_{key}_{rnd}_{i}",
                )
            )
        submitted = st.form_submit_button("Check answers 🎃", type="primary")

    if submitted:
        if any(p is None for p in picks):
            st.warning("Please select an answer for every question before submitting.")
            return
        answers = [q["options"].index(p) for q, p in zip(quiz, picks)]
        res = grade_quiz(quiz, answers)
        st.session_state[result_key] = (res, quiz, picks)
        if not key.startswith("ai_"):
            prog.record(
                st.session_state["progress"],
                lesson["id"],
                res["score"],
                res["total"],
            )

    if result_key in st.session_state:
        res, saved_quiz, saved_picks = st.session_state[result_key]
        score_class = "score-banner-pass" if res["passed"] else "score-banner-try"
        badge_icon = "🏆" if res["passed"] else "🎃"

        render_html(
            f"""
<div class="{score_class}">
  <span>{badge_icon} Score: {res["score"]} / {res["total"]} &mdash; {cheer(res["score"], res["total"])}</span>
  <span>{"PASSED" if res["passed"] else "KEEP PRACTICING"}</span>
</div>
            """
        )

        wrong = []
        for i, (q, ok, pick_text) in enumerate(zip(saved_quiz, res["results"], saved_picks)):
            right_text = q["options"][q["answer"]]
            if ok:
                render_html(
                    f"""
<div class="answer-feedback feedback-ok">
  <strong>✓ Question {i + 1}:</strong> Correct! <em>{q["why"]}</em>
</div>
                    """
                )
            else:
                render_html(
                    f"""
<div class="answer-feedback feedback-no">
  <strong>✗ Question {i + 1}:</strong> You picked <code>{pick_text}</code>.
  Correct: <strong>{right_text}</strong>. <em>{q["why"]}</em>
</div>
                    """
                )
                wrong.append({"q": q["q"], "picked": pick_text, "correct": right_text})

        cols = st.columns(2)
        if cols[0].button("Try another round 🔄", key=f"retry_{key}_{rnd}"):
            st.session_state["quiz_round"][key] = rnd + 1
            st.session_state.pop(result_key, None)
            st.session_state.pop(shuffled_key, None)
            st.rerun()
        if wrong and cols[1].button(
            f"Explain my mistakes ({monster_name}) 🧙",
            key=f"explain_{key}_{rnd}",
            disabled=not ai_ok,
        ):
            try:
                with st.spinner(f"{monster_name} is brewing a spooky explanation..."):
                    st.info(client.explain_mistakes(lesson, wrong))
            except GemmaError as e:
                st.error(str(e))


def main():
    init_state()
    lessons, monsters = get_content()
    lessons = lessons + st.session_state["extra"]

    # --- SIDEBAR (Exact Match to User Reference & Clean Layout) ---
    with st.sidebar:
        st.title("👾 Monster Mentor")
        st.caption("Gemma 4 settings")

        model = st.selectbox(
            "Model",
            MODELS,
            index=MODELS.index(DEFAULT_MODEL) if DEFAULT_MODEL in MODELS else 0,
        )

        try:
            secret_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            secret_key = ""

        api_key = st.text_input(
            "Gemini API key",
            type="password",
            value=secret_key,
            help="Free key: aistudio.google.com/apikey. Never saved to disk.",
        )

        client = GemmaClient(api_key=api_key or None, model=model)
        ai_ok, msg = client.status()

        if ai_ok:
            render_html(f'<div class="status-ready">Ready: {model}</div>')
        else:
            render_html(f'<div class="status-warn">ℹ {msg}</div>')

        topic = st.selectbox("Topic", list(TOPIC_NAMES), format_func=TOPIC_NAMES.get)
        pool = [l for l in lessons if l["topic"] == topic]
        lesson = st.selectbox("Lesson", pool, format_func=lambda l: l["title"]) if pool else None

        done = len(st.session_state["progress"])
        st.progress(done / max(len(lessons), 1), text=f"{done}/{len(lessons)} lessons attempted")

        st.divider()
        theme_choice = st.selectbox(
            "Theme Style",
            ["🎃 Halloween Wallpaper (Clean)", "🔮 Mystic Dark", "🍬 Clean Studio"],
            index=0,
            help="Switch between the clean Halloween vector wallpaper, mystic dark glow, or studio clean light.",
        )

    # Apply Selected Theme
    if "Clean Studio" in theme_choice:
        inject_css("clean")
    elif "Mystic" in theme_choice:
        inject_css("dark")
    else:
        inject_css("wallpaper")

    if lesson is None:
        st.info("No lessons in this topic yet. Open **New lesson** to generate one.")
        return

    monster = monsters[lesson["monster"]]
    badge_label = TOPIC_BADGES.get(lesson["topic"], TOPIC_NAMES[lesson["topic"]])
    emoji = TOPIC_EMOJI.get(lesson["topic"], "🎃")

    # --- TOP PANORAMIC HALLOWEEN BANNER ---
    render_html(haunted_landscape_svg())
    st.write("")

    # --- HERO CARD ---
    render_html(
        f"""
<div class="hero-card">
  <div class="hero-svg-box">
    {monster_svg(monster, 118)}
  </div>
  <div class="hero-text-box">
    <div class="topic-pill">{emoji} {badge_label}</div>
    <h1 class="hero-title">{lesson["title"]}</h1>
    <p class="hero-subtitle">Guided by <strong>{monster["name"]}</strong> &mdash; <em>"{monster["trait"]}"</em></p>
  </div>
</div>
        """
    )
    st.caption(f"💡 *{TOPIC_BLURB.get(lesson['topic'], '')}*")

    # --- TABS INTERFACE ---
    t_lesson, t_quiz, t_ask, t_fresh, t_new = st.tabs(
        ["Lesson", "Quick quiz", "Ask the monster", "Fresh quiz", "New lesson"]
    )

    with t_lesson:
        render_html(
            f"""
<div class="story-card-monster">
  <div class="card-header-label label-orange">🎃 The Monster Tale</div>
  <p class="story-body-text">{lesson["analogy"]}</p>
</div>
<div class="story-card-tech">
  <div class="card-header-label label-blue">🔬 The Real-World Engineering Concept</div>
  <p class="story-body-text">{lesson["concept"]}</p>
</div>
            """
        )
        st.caption("When the concept clicks, jump to **Quick quiz** to test your spooky mastery.")

    with t_quiz:
        st.write(f"Test your understanding of **{lesson['title']}** with **{monster['name']}**:")
        quiz_block(lesson["id"], lesson, lesson["quiz"], client, ai_ok, monster["name"])

    with t_ask:
        if not ai_ok:
            st.info(f"Chat is optional. {msg} The built-in Lesson and Quick quiz work offline without an API key.")
        history = st.session_state["chats"].setdefault(lesson["id"], [])
        for m in history:
            st.chat_message(m["role"], avatar="👾" if m["role"] == "assistant" else None).write(
                m["content"]
            )
        if prompt := st.chat_input(
            f"Ask {monster['name']} anything about {lesson['title']}...",
            disabled=not ai_ok,
        ):
            history.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            try:
                with st.chat_message("assistant", avatar="👾"):
                    reply = st.write_stream(
                        client.stream_chat(history, system=monster_system(monster, lesson))
                    )
                history.append({"role": "assistant", "content": reply})
            except GemmaError as e:
                history.pop()
                st.error(str(e))
        if history and st.button("Clear chat history"):
            st.session_state["chats"][lesson["id"]] = []
            st.rerun()

    with t_fresh:
        st.write(f"**{monster['name']}** can summon fresh multiple-choice questions for this lesson via Gemma 4.")
        n = st.slider("Number of questions", 1, 5, 3)
        if st.button("Summon new quiz 🧙", disabled=not ai_ok, type="primary"):
            try:
                with st.spinner(f"{monster['name']} is conjuring new questions..."):
                    st.session_state["ai_quiz"][lesson["id"]] = client.generate_quiz(lesson, n)
                    key = f"ai_{lesson['id']}"
                    st.session_state["quiz_round"][key] = st.session_state["quiz_round"].get(key, 0) + 1
            except GemmaError as e:
                st.error(str(e))
        if not ai_ok:
            st.caption("Requires a free Gemini API key in the sidebar.")
        if lesson["id"] in st.session_state["ai_quiz"]:
            quiz_block(
                f"ai_{lesson['id']}",
                lesson,
                st.session_state["ai_quiz"][lesson["id"]],
                client,
                ai_ok,
                monster["name"],
            )

    with t_new:
        st.write("Type any technical concept and Gemma will brew a new Halloween monster lesson with an analogy and quiz.")
        new_topic = st.text_input(
            "Concept to explain",
            placeholder="e.g. Semaphores, B+ trees, Backpropagation, Cryptography",
        )
        if st.button("Brew lesson 🧪", disabled=not (ai_ok and new_topic.strip()), type="primary"):
            try:
                with st.spinner("Brewing lesson with monster analogy..."):
                    new = client.generate_lesson(new_topic.strip(), TOPIC_NAMES[topic], list(monsters))
                new["topic"] = topic
                st.session_state["pending_lesson"] = new
            except GemmaError as e:
                st.error(str(e))
        pending = st.session_state.get("pending_lesson")
        if pending:
            st.success(f"Generated: {pending['title']}")
            render_html(
                f"""
<div class="story-card-monster">
  <div class="card-header-label label-orange">🎃 Monster Version</div>
  <p class="story-body-text">{pending["analogy"]}</p>
</div>
<div class="story-card-tech">
  <div class="card-header-label label-blue">🔬 Real Version</div>
  <p class="story-body-text">{pending["concept"]}</p>
</div>
                """
            )
            c = st.columns(2)
            if c[0].button("Keep for this session"):
                st.session_state["extra"].append(pending)
                st.session_state.pop("pending_lesson")
                st.rerun()
            if c[1].button("Save into content/ folder"):
                out = {k: v for k, v in pending.items() if k != "topic"}
                path = ROOT / "content" / pending["topic"] / f"{pending['id']}.json"
                path.write_text(json.dumps(out, indent=2), encoding="utf-8")
                get_content.clear()
                st.session_state.pop("pending_lesson")
                st.rerun()


if __name__ == "__main__" or "unittest" not in sys.modules:
    main()
