import streamlit as st
from pathlib import Path
from datetime import date
#from core.rag import LocalRAG
from core.rag import search, format_context, ensure_index, collection_count, dataset_count
from core.model_router import ModelRouter
from core.agents import LegalSupervisor, detect_intent
from core.i18n import UI
from core.safety import LEGAL_DISCLAIMER
from core.pdf_generator import generate_simple_pdf
from core.database import Database

BASE = Path(__file__).parent
st.set_page_config(
    page_title="Asaan Qanoon AI",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
defaults = {
    "chat": [],
    "cases": [],
    "last_result": None,
    "language": "English",
    "theme": "light",
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# TRANSLATIONS
# ============================================================
TRANSLATIONS = {
    "English": {
        "nav": "Navigation",
        "dashboard": "Dashboard",
        "assistant": "AI Assistant",
        "plans": "Action Plans",
        "documents": "Documents",
        "cases": "My Cases",
        "sources": "Knowledge Sources",
        "settings": "Settings",
        "language_label": "Language",
        "theme_label": "Theme",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "sidebar_caption": "Pakistan legal and civic action platform",
        "workflow": "ASK -> UNDERSTAND -> VERIFY -> ACT -> GENERATE",
        "hero_kicker": "Pakistan - Legal + Civic Intelligence",
        "hero_title": "From confusion to clear action.",
        "hero_text": "Ask naturally in Roman Urdu, Urdu, or English. Get grounded information, a practical checklist, sources, and document drafts.",
        "start_common": "Start with a common issue",
        "recent_questions": "Recent questions",
        "active_plans": "Active plans",
        "documents_metric": "Documents",
        "users_metric": "Users",
        "stored_questions": "Stored assistant questions",
        "sqlite_cases": "SQLite-managed case workflows",
        "generated_drafts": "Generated drafts",
        "workspace_users": "Dashboard workspace users",
        "tenant_rent": "Tenant / rent",
        "tenant_rent_desc": "Security deposit, rent agreement, or landlord issue.",
        "cnic_nadra": "CNIC / NADRA",
        "cnic_nadra_desc": "Renewal, replacement, or identity document guidance.",
        "lost_docs": "Lost documents",
        "lost_docs_desc": "Safe steps for a missing document.",
        "view_plan": "View plan",
        "saved_in_cases": "Action plan saved in My Cases.",
        "assistant_kicker": "Grounded legal and civic assistant",
        "assistant_title": "How can I help?",
        "assistant_caption": "Try: Mera landlord security deposit wapis nahi kar raha, main kya karun?",
        "checking": "Checking grounded sources and selecting an available AI route...",
        "urgent_warn": "This may be urgent. Prioritise immediate safety and contact the appropriate emergency or professional authority.",
        "route": "Response route",
        "fallback_warn": "AI providers were unavailable; only the retrieval-safe fallback was shown.",
        "retrieved_sources": "Retrieved sources",
        "open_official": "Open official source",
        "knowledge_source": "Knowledge policy source",
        "relevance": "Relevance score",
        "create_plan": "Create action plan",
        "saved_to_cases": "Saved to My Cases.",
        "download_pdf": "Download guidance PDF",
        "plans_kicker": "Understand -> Act",
        "plans_title": "Action Blueprints",
        "select_workflow": "Select a supported workflow",
        "tenant_deposit": "Tenant / security deposit",
        "police_fir": "Police / FIR-related issue",
        "general_civic": "General civic issue",
        "save_plan": "Save this action plan",
        "plan_saved": "Plan saved.",
        "action_steps": "Your action steps",
        "prepare_these": "Prepare these",
        "relevant_authority": "Relevant authority",
        "plan_caption": "A practical checklist - confirm jurisdiction-specific details from official sources.",
        "step": "Step",
        "completed": "Completed",
        "important_notice": "Important:",
        "notice_body": "Procedures vary by province or territory. Do not rely on unverified fees, deadlines, or social-media instructions.",
        "docs_kicker": "Act -> Generate",
        "docs_title": "Document Studio",
        "docs_caption": "Create a standard draft from your own information. Review it before submitting or signing.",
        "choose_template": "Choose a template",
        "applicant_name": "Applicant / party name",
        "recipient": "Recipient / authority",
        "subject": "Subject",
        "facts": "Facts and details",
        "generate_draft": "Generate draft",
        "complete_all": "Please complete all fields.",
        "preview": "Preview",
        "download_draft": "Download PDF draft",
        "cases_kicker": "Your saved work",
        "cases_title": "My Cases",
        "no_cases": "No saved cases yet. Create an action plan from the Assistant or Action Plans page.",
        "open_checklist": "Open checklist",
        "mark_completed": "Mark completed",
        "saved": "saved",
        "sources_kicker": "Verify before acting",
        "sources_title": "Knowledge Sources",
        "sources_warn": "This MVP includes a deliberately small starter corpus. It is not a complete database of Pakistani law.",
        "visit_source": "Visit source",
        "source_standards": "Source standards",
        "source_standards_body": "Only curated sources should be ingested. Preserve source URL, title, jurisdiction, update date, section, and verification status for every knowledge item.",
        "settings_kicker": "Personal preferences",
        "preferred_language": "Preferred language",
        "simple_lang": "Prefer simple-language explanations",
        "source_reminders": "Show source and safety reminders",
        "save_prefs": "Save preferences",
        "system_status": "System status",
        "available": "Available",
        "cooling": "Cooling down",
        "seconds": "seconds",
    },
    "Roman Urdu": {
        "nav": "Navigation",
        "dashboard": "Dashboard",
        "assistant": "AI Assistant",
        "plans": "Action Plans",
        "documents": "Documents",
        "cases": "Mere Cases",
        "sources": "Knowledge Sources",
        "settings": "Settings",
        "language_label": "Zubaan",
        "theme_label": "Theme",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "sidebar_caption": "Pakistan ka legal aur civic action platform",
        "workflow": "POOCHO -> SAMJHO -> TASDEEQ -> AMAL -> TAYYAR",
        "hero_kicker": "Pakistan - Legal + Civic Intelligence",
        "hero_title": "Uljhan se saaf amal tak.",
        "hero_text": "Roman Urdu, Urdu, ya English mein aasani se poochein. Mustanad maloomat, amli checklist, sources aur document drafts hasil karein.",
        "start_common": "Aam masle se shuru karein",
        "recent_questions": "Haal ke sawalat",
        "active_plans": "Chalne wale plans",
        "documents_metric": "Documents",
        "users_metric": "Users",
        "stored_questions": "Mehfooz assistant sawalat",
        "sqlite_cases": "SQLite case workflows",
        "generated_drafts": "Tayyar kiye gaye drafts",
        "workspace_users": "Dashboard workspace users",
        "tenant_rent": "Kirayadar / Kiraya",
        "tenant_rent_desc": "Security deposit, rent agreement, ya landlord ka masla.",
        "cnic_nadra": "CNIC / NADRA",
        "cnic_nadra_desc": "Renewal, replacement, ya identity document ki rehnumai.",
        "lost_docs": "Gum shuda documents",
        "lost_docs_desc": "Gum shuda document ke liye mehfooz qadam.",
        "view_plan": "Plan dekhein",
        "saved_in_cases": "Action plan My Cases mein save ho gaya.",
        "assistant_kicker": "Mustanad legal aur civic assistant",
        "assistant_title": "Main kaise madad karun?",
        "assistant_caption": "Try karein: Mera landlord security deposit wapis nahi kar raha, main kya karun?",
        "checking": "Mustanad sources check kiye ja rahe hain aur AI route select ho raha hai...",
        "urgent_warn": "Yeh urgent ho sakta hai. Foran safety ko tarjeeh dein aur mutaliq emergency ya professional authority se rabta karein.",
        "route": "Response route",
        "fallback_warn": "AI providers available nahi thay; sirf retrieval-safe fallback dikhaya gaya.",
        "retrieved_sources": "Hasil kiye gaye sources",
        "open_official": "Official source kholein",
        "knowledge_source": "Knowledge policy source",
        "relevance": "Relevance score",
        "create_plan": "Action plan banayein",
        "saved_to_cases": "My Cases mein save ho gaya.",
        "download_pdf": "Guidance PDF download karein",
        "plans_kicker": "Samjho -> Amal karo",
        "plans_title": "Action Blueprints",
        "select_workflow": "Supported workflow select karein",
        "tenant_deposit": "Kirayadar / security deposit",
        "police_fir": "Police / FIR se mutaliq masla",
        "general_civic": "Aam civic masla",
        "save_plan": "Yeh action plan save karein",
        "plan_saved": "Plan save ho gaya.",
        "action_steps": "Aap ke action steps",
        "prepare_these": "Yeh tayyar karein",
        "relevant_authority": "Mutaliq authority",
        "plan_caption": "Aik amli checklist - jurisdiction ke details official sources se confirm karein.",
        "step": "Step",
        "completed": "Mukammal",
        "important_notice": "Ahem:",
        "notice_body": "Tareeqay province ya territory ke hisaab se badalte hain. Ghair tasdeeq shuda fees, deadlines, ya social-media hidayat par bharosa na karein.",
        "docs_kicker": "Amal -> Tayyar karo",
        "docs_title": "Document Studio",
        "docs_caption": "Apni maloomat se standard draft banayein. Submit ya sign karne se pehle review karein.",
        "choose_template": "Template chunein",
        "applicant_name": "Applicant / party ka naam",
        "recipient": "Recipient / authority",
        "subject": "Subject",
        "facts": "Facts aur tafseel",
        "generate_draft": "Draft tayyar karein",
        "complete_all": "Barah-e-karam tamam fields mukammal karein.",
        "preview": "Preview",
        "download_draft": "PDF draft download karein",
        "cases_kicker": "Aap ka mehfooz kaam",
        "cases_title": "Mere Cases",
        "no_cases": "Abhi koi case save nahi hua. Assistant ya Action Plans page se action plan banayein.",
        "open_checklist": "Checklist kholein",
        "mark_completed": "Mukammal mark karein",
        "saved": "save hua",
        "sources_kicker": "Amal se pehle tasdeeq karein",
        "sources_title": "Knowledge Sources",
        "sources_warn": "Is MVP mein jaan boojh kar chhota starter corpus shamil hai. Yeh Pakistani law ka mukammal database nahi hai.",
        "visit_source": "Source dekhein",
        "source_standards": "Source standards",
        "source_standards_body": "Sirf curated sources shamil kiye jayein. Har knowledge item ke liye source URL, title, jurisdiction, update date, section, aur verification status mehfooz rakhein.",
        "settings_kicker": "Zaati preferences",
        "preferred_language": "Pasandeeda zubaan",
        "simple_lang": "Aasaan zubaan mein wazahat pasand karein",
        "source_reminders": "Source aur safety reminders dikhayein",
        "save_prefs": "Preferences save karein",
        "system_status": "System status",
        "available": "Available",
        "cooling": "Cooling down",
        "seconds": "seconds",
    },
    "Urdu": {
        "nav": "نیویگیشن",
        "dashboard": "ڈیش بورڈ",
        "assistant": "اے آئی اسسٹنٹ",
        "plans": "ایکشن پلانز",
        "documents": "دستاویزات",
        "cases": "میرے کیسز",
        "sources": "علمی ذرائع",
        "settings": "سیٹنگز",
        "language_label": "زبان",
        "theme_label": "تھیم",
        "theme_light": "لائٹ",
        "theme_dark": "ڈارک",
        "sidebar_caption": "پاکستان کا قانونی اور شہری ایکشن پلیٹ فارم",
        "workflow": "پوچھیں -> سمجھیں -> تصدیق کریں -> عمل کریں -> تیار کریں",
        "hero_kicker": "پاکستان - قانونی اور شہری ذہانت",
        "hero_title": "الجھن سے واضح عمل تک۔",
        "hero_text": "رومن اردو، اردو یا انگریزی میں آسانی سے پوچھیں۔ مستند معلومات، عملی چیک لسٹ، ذرائع اور دستاویز کے ڈرافٹ حاصل کریں۔",
        "start_common": "عام مسئلے سے شروع کریں",
        "recent_questions": "حالیہ سوالات",
        "active_plans": "فعال پلانز",
        "documents_metric": "دستاویزات",
        "users_metric": "صارفین",
        "stored_questions": "محفوظ اسسٹنٹ سوالات",
        "sqlite_cases": "SQLite کیس ورک فلو",
        "generated_drafts": "تیار کردہ ڈرافٹس",
        "workspace_users": "ڈیش بورڈ ورک اسپیس صارفین",
        "tenant_rent": "کرایہ دار / کرایہ",
        "tenant_rent_desc": "سیکیورٹی ڈپازٹ، کرایہ معاہدہ، یا مالک مکان کا مسئلہ۔",
        "cnic_nadra": "شناختی کارڈ / نادرا",
        "cnic_nadra_desc": "تجدید، تبدیلی، یا شناختی دستاویز کی رہنمائی۔",
        "lost_docs": "گم شدہ دستاویزات",
        "lost_docs_desc": "گم شدہ دستاویز کے لیے محفوظ اقدامات۔",
        "view_plan": "پلان دیکھیں",
        "saved_in_cases": "ایکشن پلان میرے کیسز میں محفوظ ہو گیا۔",
        "assistant_kicker": "مستند قانونی اور شہری اسسٹنٹ",
        "assistant_title": "میں کیسے مدد کر سکتا ہوں؟",
        "assistant_caption": "آزمائیں: میرا مالک مکان سیکیورٹی ڈپازٹ واپس نہیں کر رہا، میں کیا کروں؟",
        "checking": "مستند ذرائع چیک کیے جا رہے ہیں اور اے آئی روٹ منتخب ہو رہا ہے...",
        "urgent_warn": "یہ فوری ہو سکتا ہے۔ فوری حفاظت کو ترجیح دیں اور متعلقہ ایمرجنسی یا پیشہ ور اتھارٹی سے رابطہ کریں۔",
        "route": "رسپانس روٹ",
        "fallback_warn": "اے آئی فراہم کنندگان دستیاب نہیں تھے؛ صرف ریٹریول سیف فال بیک دکھایا گیا۔",
        "retrieved_sources": "حاصل کردہ ذرائع",
        "open_official": "سرکاری ذریعہ کھولیں",
        "knowledge_source": "علمی پالیسی ذریعہ",
        "relevance": "متعلقہ اسکور",
        "create_plan": "ایکشن پلان بنائیں",
        "saved_to_cases": "میرے کیسز میں محفوظ ہو گیا۔",
        "download_pdf": "رہنمائی پی ڈی ایف ڈاؤن لوڈ کریں",
        "plans_kicker": "سمجھیں -> عمل کریں",
        "plans_title": "ایکشن بلیو پرنٹس",
        "select_workflow": "معاون ورک فلو منتخب کریں",
        "tenant_deposit": "کرایہ دار / سیکیورٹی ڈپازٹ",
        "police_fir": "پولیس / ایف آئی آر سے متعلق مسئلہ",
        "general_civic": "عام شہری مسئلہ",
        "save_plan": "یہ ایکشن پلان محفوظ کریں",
        "plan_saved": "پلان محفوظ ہو گیا۔",
        "action_steps": "آپ کے ایکشن مراحل",
        "prepare_these": "یہ تیار کریں",
        "relevant_authority": "متعلقہ اتھارٹی",
        "plan_caption": "ایک عملی چیک لسٹ - دائرہ اختیار کی تفصیلات سرکاری ذرائع سے تصدیق کریں۔",
        "step": "مرحلہ",
        "completed": "مکمل",
        "important_notice": "اہم:",
        "notice_body": "طریقہ کار صوبے یا علاقے کے مطابق مختلف ہوتے ہیں۔ غیر تصدیق شدہ فیس، آخری تاریخ، یا سوشل میڈیا ہدایات پر انحصار نہ کریں۔",
        "docs_kicker": "عمل -> تیار کریں",
        "docs_title": "دستاویز اسٹوڈیو",
        "docs_caption": "اپنی معلومات سے معیاری ڈرافٹ بنائیں۔ جمع کرانے یا دستخط سے پہلے جائزہ لیں۔",
        "choose_template": "ٹیمپلیٹ منتخب کریں",
        "applicant_name": "درخواست دہندہ / فریق کا نام",
        "recipient": "وصول کنندہ / اتھارٹی",
        "subject": "موضوع",
        "facts": "حقائق اور تفصیلات",
        "generate_draft": "ڈرافٹ تیار کریں",
        "complete_all": "براہ کرم تمام فیلڈز مکمل کریں۔",
        "preview": "پیش نظارہ",
        "download_draft": "پی ڈی ایف ڈرافٹ ڈاؤن لوڈ کریں",
        "cases_kicker": "آپ کا محفوظ کام",
        "cases_title": "میرے کیسز",
        "no_cases": "ابھی کوئی کیس محفوظ نہیں۔ اسسٹنٹ یا ایکشن پلانز صفحے سے ایکشن پلان بنائیں۔",
        "open_checklist": "چیک لسٹ کھولیں",
        "mark_completed": "مکمل نشان زد کریں",
        "saved": "محفوظ",
        "sources_kicker": "عمل سے پہلے تصدیق کریں",
        "sources_title": "علمی ذرائع",
        "sources_warn": "اس ایم وی پی میں جان بوجھ کر چھوٹا اسٹارٹر کارپس شامل ہے۔ یہ پاکستانی قانون کا مکمل ڈیٹا بیس نہیں ہے۔",
        "visit_source": "ذریعہ دیکھیں",
        "source_standards": "ذرائع کے معیارات",
        "source_standards_body": "صرف منتخب ذرائع شامل کیے جائیں۔ ہر علمی آئٹم کے لیے سورس یو آر ایل، عنوان، دائرہ اختیار، اپ ڈیٹ کی تاریخ، سیکشن، اور تصدیق کی حیثیت محفوظ رکھیں۔",
        "settings_kicker": "ذاتی ترجیحات",
        "preferred_language": "پسندیدہ زبان",
        "simple_lang": "آسان زبان میں وضاحت کو ترجیح دیں",
        "source_reminders": "ذرائع اور حفاظتی یاد دہانیاں دکھائیں",
        "save_prefs": "ترجیحات محفوظ کریں",
        "system_status": "سسٹم اسٹیٹس",
        "available": "دستیاب",
        "cooling": "کولنگ ڈاؤن",
        "seconds": "سیکنڈ",
    },
}


def t(key: str) -> str:
    """Translate a key using the current language."""
    lang = st.session_state.get("language", "English")
    return TRANSLATIONS.get(lang, TRANSLATIONS["English"]).get(key, key)


# ============================================================
# THEME CSS
# ============================================================
def build_css(theme: str) -> str:
    if theme == "dark":
        app_bg = "#0d1b2a"
        app_bg_accent = "#132c47"
        card_bg = "#152a42"
        card_border = "#2a5d92"
        text = "#ffffff"
        hero_bg = "#152a42"
        hero_title = "#ffffff"
        hero_text = "#d0dce8"
        source_bg = "#13304a"
        notice_bg = "#3a2f10"
        notice_text = "#ffe28a"
        notice_border = "#f4d887"
        input_bg = "#0f2338"
        input_text = "#ffffff"
    else:
        app_bg = "#f6fafc"
        app_bg_accent = "#dcefe8"
        card_bg = "#ffffff"
        card_border = "#dbe7ee"
        text = "#000000"
        hero_bg = "#ffffff"
        hero_title = "#0b315e"
        hero_text = "#333333"
        source_bg = "#f4faf2"
        notice_bg = "#fff7df"
        notice_text = "#6b5400"
        notice_border = "#f4d887"
        input_bg = "#ffffff"
        input_text = "#000000"

    return f"""<style>
:root{{--navy:#0b315e;--green:#5aa54e;--ink:#10243e;--muted:#687a8f;--line:#dbe7ee}}

[data-testid="stAppViewContainer"]{{
    background:radial-gradient(circle at 88% 5%,{app_bg_accent} 0,transparent 27%),{app_bg};
}}
[data-testid="stHeader"]{{background:transparent}}
.block-container{{padding-top:1.5rem;max-width:1420px}}

/* ---------- GLOBAL TEXT (main content) ---------- */
.stMarkdown, .stText, p, span, label, h1, h2, h3, h4, h5, h6, small, li{{
    color:{text} !important;
}}

/* ============================================================ */
/* SIDEBAR — Navy background, white text on plain labels ONLY    */
/* (NO wildcard '*' rule, so selectbox can have its own colors)  */
/* ============================================================ */
[data-testid="stSidebar"]{{
    background-color:#0b315e !important;
}}

/* Sidebar text elements — explicit list (no '*') */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] div.stMarkdown,
[data-testid="stSidebar"] div.stCaption,
[data-testid="stSidebar"] div[data-testid="stCaptionContainer"]{{
    color:#ffffff !important;
}}

/* Sidebar radio (theme + nav) — WHITE */
[data-testid="stSidebar"] [role="radiogroup"] label,
[data-testid="stSidebar"] [role="radiogroup"] label p,
[data-testid="stSidebar"] [role="radiogroup"] label span,
[data-testid="stSidebar"] [role="radiogroup"] label div{{
    color:#ffffff !important;
}}

/* ---------- SIDEBAR SELECTBOX (LANGUAGE) — WHITE BG + BLACK TEXT ---------- */
[data-testid="stSidebar"] div[data-baseweb="select"]{{
    background-color:#ffffff !important;
    border-radius:8px !important;
}}

[data-testid="stSidebar"] div[data-baseweb="select"] > div{{
    background-color:#ffffff !important;
    border:1px solid #2a5d92 !important;
    border-radius:8px !important;
}}

/* All text inside the selectbox — BLACK */
[data-testid="stSidebar"] div[data-baseweb="select"] *,
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] div,
[data-testid="stSidebar"] div[data-baseweb="select"] p{{
    color:#000000 !important;
    -webkit-text-fill-color:#000000 !important;
    background-color:transparent !important;
}}

/* Visible value text */
[data-testid="stSidebar"] div[data-baseweb="select"] div[aria-selected],
[data-testid="stSidebar"] div[data-baseweb="select"] div[role="button"]{{
    color:#000000 !important;
    -webkit-text-fill-color:#000000 !important;
}}

/* Input field */
[data-testid="stSidebar"] div[data-baseweb="select"] input{{
    color:#000000 !important;
    -webkit-text-fill-color:#000000 !important;
    background-color:#ffffff !important;
    caret-color:#000000 !important;
}}

/* Arrow icon — BLACK */
[data-testid="stSidebar"] div[data-baseweb="select"] svg,
[data-testid="stSidebar"] div[data-baseweb="select"] svg path{{
    fill:#000000 !important;
    color:#000000 !important;
}}

/* ---------- SIDEBAR DROPDOWN LIST — WHITE BG + BLACK TEXT ---------- */
[data-testid="stSidebar"] ul[role="listbox"]{{
    background-color:#ffffff !important;
}}
[data-testid="stSidebar"] ul[role="listbox"] li,
[data-testid="stSidebar"] ul[role="listbox"] li *{{
    color:#000000 !important;
    -webkit-text-fill-color:#000000 !important;
    background-color:#ffffff !important;
}}
[data-testid="stSidebar"] ul[role="listbox"] li:hover,
[data-testid="stSidebar"] ul[role="listbox"] li:hover *{{
    background-color:#e6eef5 !important;
    color:#000000 !important;
}}

/* ---------- HERO ---------- */
.hero{{
    padding:38px;
    border-radius:26px;
    background:{hero_bg};
    border:1px solid {card_border};
    box-shadow:0 12px 30px rgba(16,36,62,0.08);
}}
.hero *{{color:{text} !important;}}
.kicker{{
    color:#5aa54e !important;
    font-size:.76rem;
    font-weight:800;
    letter-spacing:.14em;
    text-transform:uppercase;
}}
.hero h1{{
    font-size:3rem;
    margin:.35rem 0 .7rem;
    color:{hero_title} !important;
}}
.hero p{{
    max-width:690px;
    color:{hero_text} !important;
    font-size:1.05rem;
}}

/* ---------- CARDS ---------- */
.card{{height:100%;padding:19px;border:1px solid {card_border};border-radius:18px;background:{card_bg};box-shadow:0 8px 22px #10243e0c}}
.card *{{color:{text} !important}}
.card h3{{color:{hero_title} !important;font-size:1rem;margin:0 0 .45rem}}
.metric{{font-size:1.7rem;font-weight:800;color:{hero_title} !important}}

/* ---------- SOURCES / PLANS / NOTICES / CASES ---------- */
.source{{border-left:4px solid var(--green);padding:12px 15px;background:{source_bg};border-radius:0 10px 10px 0;margin:9px 0}}
.source *{{color:{text} !important}}
.source a{{color:{hero_title} !important;font-weight:600}}

.plan-step{{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid {card_border}}}
.plan-step *{{color:{text} !important}}

.number{{background:var(--navy);color:#ffffff !important;border-radius:50%;min-width:27px;height:27px;text-align:center;padding-top:2px;font-weight:700}}

.notice{{padding:14px 16px;border-radius:12px;background:{notice_bg};border:1px solid {notice_border}}}
.notice *{{color:{notice_text} !important}}

.case{{padding:14px;border:1px solid {card_border};border-radius:12px;background:{card_bg};margin-bottom:10px}}
.case *{{color:{text} !important}}

/* ---------- INPUTS / TEXTAREAS (main area) ---------- */
.main input, .main textarea, .main select{{
    color:{input_text} !important;
    background-color:{input_bg} !important;
}}
[data-testid="stChatInput"] textarea{{
    color:{input_text} !important;
    background:{input_bg} !important;
}}

/* ---------- BUTTONS ---------- */
.stButton>button,
.stDownloadButton>button,
.stFormSubmitButton>button{{
    background-color:#5aa54e !important;
    color:#ffffff !important;
    border:1px solid #4a8f3f !important;
    border-radius:10px !important;
    font-weight:700 !important;
    padding:0.45rem 1rem !important;
    transition:all 0.2s ease-in-out;
}}
.stButton>button *,
.stDownloadButton>button *,
.stFormSubmitButton>button *{{
    color:#ffffff !important;
}}
.stButton>button:hover,
.stDownloadButton>button:hover,
.stFormSubmitButton>button:hover{{
    background-color:#4a8f3f !important;
    color:#ffffff !important;
    border-color:#3d7a33 !important;
    box-shadow:0 4px 12px rgba(90,165,78,0.35);
}}
.stButton>button:focus,
.stDownloadButton>button:focus,
.stFormSubmitButton>button:focus{{
    color:#ffffff !important;
    box-shadow:0 0 0 0.2rem rgba(90,165,78,0.4) !important;
}}
</style>"""


# ============================================================
# CORE BUILDS (cached)
# ============================================================
@st.cache_resource
def build_rag_index():
    """Initialize the Chroma RAG index once per Streamlit process."""
    try:
        ensure_index()
        return True
    except Exception as exc:
        st.error(f"RAG initialization failed: {exc}")
        return False


def blueprint(intent):
    library = {
        "rent": ("Tenant / security deposit", "Relevant rent authority or a qualified local legal professional",
                 ["Rent agreement", "Deposit/payment proof", "Messages or notices", "Handover evidence"],
                 ["Review the deposit, notice, and deduction terms in the agreement.",
                  "Collect receipts, transfers, messages, and photos.",
                  "Send a factual written request and retain proof of sending.",
                  "Ask for an itemised explanation of any deduction.",
                  "Check the applicable provincial procedure before escalating."]),
        "nadra": ("CNIC / NADRA procedure", "NADRA official service channel",
                  ["Existing identity document if available", "Current official requirements",
                   "Supporting records requested by NADRA"],
                  ["Choose the exact service: renewal, replacement, modification, NICOP, or POC.",
                   "Check official NADRA guidance before visiting or paying.",
                   "Prepare the information requested through the official channel.",
                   "Keep the application and tracking reference.",
                   "Verify collection or delivery steps directly with NADRA."]),
        "lost_document": ("Lost document", "Issuing authority; local police procedure where applicable",
                          ["Document details/copy", "When and where it was lost", "Identity evidence",
                           "Report/reference if required"],
                          ["Record the document type, number, location, and date last seen.",
                           "Protect connected accounts or services if relevant.",
                           "Check the official replacement procedure.",
                           "Obtain an incident reference only where the authority requires it.",
                           "Keep every receipt and tracking number."]),
        "police": ("Police / FIR-related issue", "Relevant provincial or territorial police authority",
                   ["Factual timeline", "Identity details", "Original messages, photos, or files",
                    "Prior reference numbers"],
                   ["Prioritise safety; contact emergency services if anyone is in immediate danger.",
                    "Write a factual timeline and preserve original evidence.",
                    "Identify the correct local jurisdiction.",
                    "Use the relevant official police procedure.",
                    "Keep your submission reference and all copies."]),
    }
    return library.get(intent, ("General civic action plan", "Relevant official authority",
                                ["Identification", "Factual written summary", "Relevant receipts or correspondence"],
                                ["Describe the issue and outcome you need.", "Identify the responsible authority.",
                                 "Check its official requirements.",
                                 "Prepare copies and retain a submission record."]))


def show_plan(intent, complete=False):
    title, authority, docs, steps = blueprint(intent)
    st.subheader(title)
    st.caption(t("plan_caption"))
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown(f"#### {t('action_steps')}")
        for i, step in enumerate(steps, 1):
            done = st.checkbox(step, key=f"{intent}-{i}") if complete else False
            label = t("completed") if done else f"{t('step')} {i}"
            st.markdown(
                f'<div class="plan-step"><span class="number">{i}</span>'
                f'<div><b>{label}</b><br>{step}</div></div>',
                unsafe_allow_html=True,
            )
    with right:
        st.markdown(f"#### {t('prepare_these')}")
        for item in docs:
            st.markdown(f"- {item}")
        st.markdown(f"#### {t('relevant_authority')}")
        st.info(authority)
        st.markdown(
            f'<div class="notice"><b>{t("important_notice")}</b> {t("notice_body")}</div>',
            unsafe_allow_html=True,
        )
    return title, authority, docs, steps


# ============================================================
# BUILD CORE SERVICES
# ============================================================
rag_ready = build_rag_index()
db = Database(str(BASE / "data" / "asaan_qanoon.db"))
db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")

@st.cache_resource
def build_router():
    return ModelRouter(st.secrets)

router = build_router()
supervisor = LegalSupervisor(router=router)


# ============================================================
# 1) SIDEBAR FIRST
# ============================================================
with st.sidebar:
    # --- LOGO ---
    logo_path = BASE / "static" / "assets" / "logo" / "logo 2.jpeg"
    if logo_path.exists():
        st.image(str(logo_path), width="stretch")
    else:
        st.warning(f"Logo not found at: {logo_path}")

    st.caption(t("sidebar_caption"))

    # --- THEME TOGGLE ---
    light_label = t("theme_light")
    dark_label = t("theme_dark")
    theme_choice = st.radio(
        t("theme_label"),
        [light_label, dark_label],
        index=0 if st.session_state.theme == "light" else 1,
        horizontal=True,
        key="theme_widget",
    )
    st.session_state.theme = "light" if theme_choice == light_label else "dark"

    # --- LANGUAGE SWITCHER ---
    lang_options = ["English", "Roman Urdu", "Urdu"]
    st.selectbox(
        t("language_label"),
        lang_options,
        index=lang_options.index(st.session_state.language),
        key="language",
    )

    # --- NAVIGATION ---
    nav_map = {
        "Dashboard": t("dashboard"),
        "AI Assistant": t("assistant"),
        "Action Plans": t("plans"),
        "Documents": t("documents"),
        "My Cases": t("cases"),
        "Knowledge Sources": t("sources"),
        "Settings": t("settings"),
    }
    page_label = st.radio(t("nav"), list(nav_map.values()), key="nav_radio")
    reverse = {v: k for k, v in nav_map.items()}
    page = reverse[page_label]

    st.divider()
    st.caption(t("workflow"))
    st.caption(LEGAL_DISCLAIMER)


# ============================================================
# 2) INJECT CSS (uses current theme from session_state)
# ============================================================
st.markdown(build_css(st.session_state.theme), unsafe_allow_html=True)


# ============================================================
# 3) RENDER MAIN PAGE
# ============================================================
if page == "Dashboard":
    st.markdown(
        f'<section class="hero"><div class="kicker">{t("hero_kicker")}</div>'
        f'<h1>{t("hero_title")}</h1><p>{t("hero_text")}</p></section>',
        unsafe_allow_html=True,
    )
    st.write("")
    cols = st.columns(4)
    dashboard = db.dashboard_data()
    metrics = [
        (t("recent_questions"), str(dashboard["metrics"]["questions"]), t("stored_questions")),
        (t("active_plans"), str(dashboard["metrics"]["cases"]), t("sqlite_cases")),
        (t("documents_metric"), str(dashboard["metrics"]["documents"]), t("generated_drafts")),
        (t("users_metric"), str(dashboard["metrics"]["users"]), t("workspace_users")),
    ]
    for col, (label, value, note) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="card"><h3>{label}</h3><div class="metric">{value}</div>'
                f'<small>{note}</small></div>',
                unsafe_allow_html=True,
            )
    st.write("")
    st.subheader(t("start_common"))
    items = [
        (t("tenant_rent"), t("tenant_rent_desc"), "rent"),
        (t("cnic_nadra"), t("cnic_nadra_desc"), "nadra"),
        (t("lost_docs"), t("lost_docs_desc"), "lost_document"),
    ]
    cols = st.columns(3)
    for col, (heading, text, intent) in zip(cols, items):
        with col:
            st.markdown(f'<div class="card"><h3>{heading}</h3><p>{text}</p></div>', unsafe_allow_html=True)
            if st.button(f'{t("view_plan")}: {heading}', key=f"start-{intent}"):
                db.create_case(heading, intent)
                db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
                st.success(t("saved_in_cases"))


elif page == "AI Assistant":
    st.markdown(f'<div class="kicker">{t("assistant_kicker")}</div>', unsafe_allow_html=True)
    st.title(t("assistant_title"))
    st.caption(t("assistant_caption"))
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    try:
        placeholder = UI[st.session_state.language]["placeholder"]
    except Exception:
        placeholder = "Ask your question..."

    prompt = st.chat_input(placeholder)
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner(t("checking")):
                result = supervisor.handle(prompt, st.session_state.language)
            st.markdown(result.answer)
            if result.high_risk:
                st.error(t("urgent_warn"))
            if result.used_llm:
                st.caption(f'{t("route")}: {result.provider} - {result.model}')
            else:
                st.warning(t("fallback_warn"))
            if result.sources:
                st.markdown(f'#### {t("retrieved_sources")}')
                for source in result.sources:
                    url = source["url"]
                    label = source["title"]
                    link_text = t("open_official") if url else t("knowledge_source")
                    link_html = f'<a href="{url}">{link_text}</a>' if url else link_text
                    st.markdown(
                        f'<div class="source"><b>{label}</b><br>{link_html}<br>'
                        f'<small>{t("relevance")}: {source["score"]}</small></div>',
                        unsafe_allow_html=True,
                    )
            if st.button(t("create_plan"), key="make-plan"):
                title, _, _, _ = blueprint(result.intent)
                db.create_case(title, result.intent)
                db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
                st.success(t("saved_to_cases"))
            pdf = generate_simple_pdf("Asaan Qanoon AI guidance", result.answer)
            st.download_button(t("download_pdf"), pdf, "asaan-qanoon-guidance.pdf", "application/pdf")
            st.session_state.last_result = result
            db.save_interaction(prompt[:120], st.session_state.language, prompt, result.answer)
            db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
        st.session_state.chat.append({"role": "assistant", "content": result.answer})


elif page == "Action Plans":
    st.markdown(f'<div class="kicker">{t("plans_kicker")}</div>', unsafe_allow_html=True)
    st.title(t("plans_title"))
    workflow_map = {
        t("tenant_deposit"): "rent",
        t("cnic_nadra"): "nadra",
        t("lost_docs"): "lost_document",
        t("police_fir"): "police",
        t("general_civic"): "general_civic",
    }
    choice_label = st.selectbox(t("select_workflow"), list(workflow_map.keys()))
    intent = workflow_map[choice_label]
    title, _, _, _ = show_plan(intent, complete=True)
    if st.button(t("save_plan")):
        db.create_case(title, intent)
        db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
        st.success(t("plan_saved"))


elif page == "Documents":
    st.markdown(f'<div class="kicker">{t("docs_kicker")}</div>', unsafe_allow_html=True)
    st.title(t("docs_title"))
    st.caption(t("docs_caption"))
    doc_type = st.selectbox(
        t("choose_template"),
        ["General Application", "Complaint Letter", "Undertaking",
         "Loss Affidavit (draft)", "Rent Agreement (draft)", "Basic Legal Notice (draft)"],
    )
    with st.form("document-form"):
        name = st.text_input(t("applicant_name"))
        recipient = st.text_input(t("recipient"))
        subject = st.text_input(t("subject"))
        facts = st.text_area(t("facts"), height=160)
        submitted = st.form_submit_button(t("generate_draft"))
    if submitted:
        if not all([name.strip(), recipient.strip(), subject.strip(), facts.strip()]):
            st.error(t("complete_all"))
        else:
            body = f"""DRAFT FOR REVIEW
Document type: {doc_type}
Date: {date.today()}

To: {recipient}
Subject: {subject}

Respected Sir/Madam,

I, {name}, submit the following factual statement/request:

{facts}

I request that this matter be considered according to the applicable procedure.

Sincerely,
{name}

Important: This standard draft is generated from user-provided details. It is not verified for legal sufficiency, stamp paper, attestation, jurisdiction-specific clauses, or filing requirements."""
            st.text_area(t("preview"), body, height=340)
            db.save_document(doc_type, subject, body)
            db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
            st.download_button(
                t("download_draft"),
                generate_simple_pdf(doc_type, body),
                "asaan-qanoon-draft.pdf",
                "application/pdf",
            )


elif page == "My Cases":
    st.markdown(f'<div class="kicker">{t("cases_kicker")}</div>', unsafe_allow_html=True)
    st.title(t("cases_title"))
    cases = db.list_cases()
    if not cases:
        st.info(t("no_cases"))
    for case in cases:
        st.markdown(
            f'<div class="case"><b>{case["title"]}</b><br>'
            f'<small>{case["status"]} - {t("saved")} {case["created_at"][:10]}</small></div>',
            unsafe_allow_html=True,
        )
        a, b = st.columns(2)
        with a:
            if st.button(t("open_checklist"), key=f"open-{case['id']}"):
                show_plan(case["intent"], complete=True)
        with b:
            if case["status"] != "Completed" and st.button(t("mark_completed"), key=f"done-{case['id']}"):
                db.update_case_status(case["id"], "Completed")
                db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
                st.rerun()


elif page == "Knowledge Sources":
    st.markdown(f'<div class="kicker">{t("sources_kicker")}</div>', unsafe_allow_html=True)
    st.title(t("sources_title"))
    st.warning(t("sources_warn"))
    try:
        total_dataset = dataset_count()
        total_indexed = collection_count()
        st.caption(f"Dataset records: {total_dataset} | Indexed RAG chunks: {total_indexed}")

        preview = search(
            query="Pakistan legal civic information",
            top_k=20,
        )
        source_items = preview.get("results", [])

        if not source_items:
            st.info("No indexed knowledge sources are currently available.")
        else:
            seen = set()
            for item in source_items:
                title = item.get("title", "Source")
                url = item.get("source_url", "")
                authority = item.get("authority", "")
                jurisdiction = item.get("jurisdiction", "")
                category = item.get("category", "")
                verified = item.get("verified", False)
                key = (title, url)

                if key in seen:
                    continue
                seen.add(key)

                st.markdown(f"**{title}**")
                details = " | ".join(
                    x for x in [authority, jurisdiction, category] if x
                )
                if details:
                    st.caption(details)
                st.caption("Verified source" if verified else "Verification status not confirmed")
                if url:
                    st.link_button(t("visit_source"), url, width="content")
                st.divider()

    except Exception as exc:
        st.error(f"Unable to load knowledge sources: {exc}")
    st.markdown(f'#### {t("source_standards")}')
    st.markdown(t("source_standards_body"))


else:  # Settings
    st.markdown(f'<div class="kicker">{t("settings_kicker")}</div>', unsafe_allow_html=True)
    st.title(t("settings"))
    with st.form("settings"):
        lang_options = ["English", "Roman Urdu", "Urdu"]
        preferred = st.selectbox(
            t("preferred_language"),
            lang_options,
            index=lang_options.index(st.session_state.language),
        )
        simple = st.checkbox(t("simple_lang"), value=True)
        notices = st.checkbox(t("source_reminders"), value=True)
        if st.form_submit_button(t("save_prefs")):
            st.session_state.language = preferred
            st.rerun()
    st.divider()
    st.subheader(t("system_status"))
    if hasattr(router, "status"):
        status = router.status()
        for provider, details in status.items():
            healthy = details.get("healthy", True)
            cooldown = details.get("cooldown_seconds", 0)
            state = (
                t("available")
                if healthy
                else f'{t("cooling")} ({cooldown} {t("seconds")})'
            )
            st.write(f"**{provider.title()}**: {state}")
    else:
        st.info("Provider status reporting is not available in the current model router.")
