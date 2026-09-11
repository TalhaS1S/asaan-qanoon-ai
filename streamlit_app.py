import streamlit as st
from pathlib import Path
from datetime import date
from core.rag import LocalRAG
from core.model_router import ModelRouter
from core.agents import LegalSupervisor, detect_intent
from core.i18n import UI
from core.safety import LEGAL_DISCLAIMER
from core.pdf_generator import generate_simple_pdf
from core.database import Database

BASE = Path(__file__).parent
st.set_page_config(page_title="Asaan Qanoon AI", page_icon="A", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
:root{--navy:#0b315e;--green:#5aa54e;--ink:#10243e;--muted:#687a8f;--line:#dbe7ee}

/* ---------- MAIN APP BACKGROUND ---------- */
[data-testid="stAppViewContainer"]{
    background:radial-gradient(circle at 88% 5%,#dcefe8 0,transparent 27%),#f6fafc;
}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.5rem;max-width:1420px}

/* ---------- GLOBAL TEXT BLACK (main area) ---------- */
.stMarkdown, .stText, p, span, label, h1, h2, h3, h4, h5, h6, small, li{
    color:#000000;
}

/* ---------- SIDEBAR (dark bg + WHITE TEXT) ---------- */
[data-testid="stSidebar"] *{
    color:#ffffff !important;
}

/* Sidebar selectbox - dark bg + white text */
[data-testid="stSidebar"] div[data-baseweb="select"] > div{
    background-color:#123a68 !important;
    border:1px solid #2a5d92 !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] *{
    color:#ffffff !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] svg{
    fill:#ffffff !important;
}

/* Sidebar dropdown list */
[data-testid="stSidebar"] ul[role="listbox"]{
    background-color:#123a68 !important;
}
[data-testid="stSidebar"] ul[role="listbox"] li{
    color:#ffffff !important;
    background-color:#123a68 !important;
}
[data-testid="stSidebar"] ul[role="listbox"] li:hover{
    background-color:#1c4f8a !important;
}

/* Sidebar radio */
[data-testid="stSidebar"] [role="radiogroup"] label,
[data-testid="stSidebar"] [role="radiogroup"] label *{
    color:#ffffff !important;
}

/* ---------- HERO (WHITE BG + BLACK TEXT) ---------- */
.hero{
    padding:38px;
    border-radius:26px;
    background:#ffffff;
    border:1px solid #dbe7ee;
    box-shadow:0 12px 30px rgba(16,36,62,0.08);
}
.hero, .hero *{color:#000000 !important}
.kicker{
    color:#5aa54e !important;
    font-size:.76rem;
    font-weight:800;
    letter-spacing:.14em;
    text-transform:uppercase;
}
.hero h1{
    font-size:3rem;
    margin:.35rem 0 .7rem;
    color:#0b315e !important;
}
.hero p{
    max-width:690px;
    color:#333333 !important;
    font-size:1.05rem;
}

/* ---------- CARDS ---------- */
.card{height:100%;padding:19px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:0 8px 22px #10243e0c}
.card *{color:#000000 !important}
.card h3{color:var(--navy) !important;font-size:1rem;margin:0 0 .45rem}
.metric{font-size:1.7rem;font-weight:800;color:var(--navy) !important}

/* ---------- SOURCES / PLANS / NOTICES / CASES ---------- */
.source{border-left:4px solid var(--green);padding:12px 15px;background:#f4faf2;border-radius:0 10px 10px 0;margin:9px 0}
.source *{color:#000000 !important}
.source a{color:#0b315e !important;font-weight:600}

.plan-step{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid var(--line)}
.plan-step *{color:#000000 !important}

.number{background:var(--navy);color:#ffffff !important;border-radius:50%;min-width:27px;height:27px;text-align:center;padding-top:2px;font-weight:700}

.notice{padding:14px 16px;border-radius:12px;background:#fff7df;border:1px solid #f4d887}
.notice *{color:#6b5400 !important}

.case{padding:14px;border:1px solid var(--line);border-radius:12px;background:#fff;margin-bottom:10px}
.case *{color:#000000 !important}

/* ---------- INPUTS / TEXTAREAS ---------- */
input, textarea, select{
    color:#000000 !important;
    background-color:#ffffff !important;
}
[data-testid="stChatInput"] textarea{
    color:#000000 !important;
    background:#ffffff !important;
}

/* ---------- BUTTONS (GREEN BG + WHITE TEXT) ---------- */
.stButton>button,
.stDownloadButton>button,
.stFormSubmitButton>button{
    background-color:#5aa54e !important;
    color:#ffffff !important;
    border:1px solid #4a8f3f !important;
    border-radius:10px !important;
    font-weight:700 !important;
    padding:0.45rem 1rem !important;
    transition:all 0.2s ease-in-out;
}
.stButton>button *,
.stDownloadButton>button *,
.stFormSubmitButton>button *{
    color:#ffffff !important;
}
.stButton>button:hover,
.stDownloadButton>button:hover,
.stFormSubmitButton>button:hover{
    background-color:#4a8f3f !important;
    color:#ffffff !important;
    border-color:#3d7a33 !important;
    box-shadow:0 4px 12px rgba(90,165,78,0.35);
}
.stButton>button:focus,
.stDownloadButton>button:focus,
.stFormSubmitButton>button:focus{
    color:#ffffff !important;
    box-shadow:0 0 0 0.2rem rgba(90,165,78,0.4) !important;
}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def build_rag():
    return LocalRAG(str(BASE / "data" / "demo_knowledge.jsonl"))

def blueprint(intent):
    library = {
        "rent": ("Tenant / security deposit", "Relevant rent authority or a qualified local legal professional",
                 ["Rent agreement", "Deposit/payment proof", "Messages or notices", "Handover evidence"],
                 ["Review the deposit, notice, and deduction terms in the agreement.", "Collect receipts, transfers, messages, and photos.", "Send a factual written request and retain proof of sending.", "Ask for an itemised explanation of any deduction.", "Check the applicable provincial procedure before escalating."]),
        "nadra": ("CNIC / NADRA procedure", "NADRA official service channel",
                  ["Existing identity document if available", "Current official requirements", "Supporting records requested by NADRA"],
                  ["Choose the exact service: renewal, replacement, modification, NICOP, or POC.", "Check official NADRA guidance before visiting or paying.", "Prepare the information requested through the official channel.", "Keep the application and tracking reference.", "Verify collection or delivery steps directly with NADRA."]),
        "lost_document": ("Lost document", "Issuing authority; local police procedure where applicable",
                          ["Document details/copy", "When and where it was lost", "Identity evidence", "Report/reference if required"],
                          ["Record the document type, number, location, and date last seen.", "Protect connected accounts or services if relevant.", "Check the official replacement procedure.", "Obtain an incident reference only where the authority requires it.", "Keep every receipt and tracking number."]),
        "police": ("Police / FIR-related issue", "Relevant provincial or territorial police authority",
                   ["Factual timeline", "Identity details", "Original messages, photos, or files", "Prior reference numbers"],
                   ["Prioritise safety; contact emergency services if anyone is in immediate danger.", "Write a factual timeline and preserve original evidence.", "Identify the correct local jurisdiction.", "Use the relevant official police procedure.", "Keep your submission reference and all copies."]),
    }
    return library.get(intent, ("General civic action plan", "Relevant official authority",
        ["Identification", "Factual written summary", "Relevant receipts or correspondence"],
        ["Describe the issue and outcome you need.", "Identify the responsible authority.", "Check its official requirements.", "Prepare copies and retain a submission record."]))

def show_plan(intent, complete=False):
    title, authority, docs, steps = blueprint(intent)
    st.subheader(title)
    st.caption("A practical checklist - confirm jurisdiction-specific details from official sources.")
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("#### Your action steps")
        for i, step in enumerate(steps, 1):
            done = st.checkbox(step, key=f"{intent}-{i}") if complete else False
            label = "Completed" if done else f"Step {i}"
            st.markdown(f'<div class="plan-step"><span class="number">{i}</span><div><b>{label}</b><br>{step}</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown("#### Prepare these")
        for item in docs: st.markdown(f"- {item}")
        st.markdown("#### Relevant authority")
        st.info(authority)
        st.markdown('<div class="notice"><b>Important:</b> Procedures vary by province or territory. Do not rely on unverified fees, deadlines, or social-media instructions.</div>', unsafe_allow_html=True)
    return title, authority, docs, steps

for key, default in {"chat": [], "cases": [], "last_result": None, "language": "Roman Urdu"}.items():
    if key not in st.session_state: st.session_state[key] = default

rag = build_rag()
db = Database(str(BASE / "data" / "asaan_qanoon.db"))
db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
router = ModelRouter(st.secrets)
supervisor = LegalSupervisor(rag, router)

with st.sidebar:
    st.image(str(BASE / "assets" / "asaan_qanoon_logo.jpeg"), use_container_width=True)
    st.caption("Pakistan legal and civic action platform")
    page = st.radio("Navigation", ["Dashboard", "AI Assistant", "Action Plans", "Documents", "My Cases", "Knowledge Sources", "Settings"])
    st.session_state.language = st.selectbox("Language", ["Roman Urdu", "Urdu", "English"], index=["Roman Urdu", "Urdu", "English"].index(st.session_state.language))
    st.divider()
    st.caption("ASK -> UNDERSTAND -> VERIFY -> ACT -> GENERATE")
    st.caption(LEGAL_DISCLAIMER)

if page == "Dashboard":
    st.markdown("""<section class="hero"><div class="kicker">Pakistan - Legal + Civic Intelligence</div><h1>From confusion to clear action.</h1><p>Ask naturally in Roman Urdu, Urdu, or English. Get grounded information, a practical checklist, sources, and document drafts.</p></section>""", unsafe_allow_html=True)
    st.write("")
    cols = st.columns(4)
    dashboard = db.dashboard_data()
    metrics = [("Recent questions", str(dashboard["metrics"]["questions"]), "Stored assistant questions"), ("Active plans", str(dashboard["metrics"]["cases"]), "SQLite-managed case workflows"), ("Documents", str(dashboard["metrics"]["documents"]), "Generated drafts"), ("Users", str(dashboard["metrics"]["users"]), "Dashboard workspace users")]
    for col, (label, value, note) in zip(cols, metrics):
        with col: st.markdown(f'<div class="card"><h3>{label}</h3><div class="metric">{value}</div><small>{note}</small></div>', unsafe_allow_html=True)
    st.write("")
    st.subheader("Start with a common issue")
    items = [("Tenant / rent", "Security deposit, rent agreement, or landlord issue.", "rent"), ("CNIC / NADRA", "Renewal, replacement, or identity document guidance.", "nadra"), ("Lost documents", "Safe steps for a missing document.", "lost_document")]
    cols = st.columns(3)
    for col, (heading, text, intent) in zip(cols, items):
        with col:
            st.markdown(f'<div class="card"><h3>{heading}</h3><p>{text}</p></div>', unsafe_allow_html=True)
            if st.button(f"View plan: {heading}", key=f"start-{intent}"):
                db.create_case(heading, intent)
                db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
                st.success("Action plan saved in My Cases.")

elif page == "AI Assistant":
    st.markdown('<div class="kicker">Grounded legal and civic assistant</div>', unsafe_allow_html=True)
    st.title("How can I help?")
    st.caption("Try: Mera landlord security deposit wapis nahi kar raha, main kya karun?")
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    prompt = st.chat_input(UI[st.session_state.language]["placeholder"])
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking grounded sources and selecting an available AI route..."):
                result = supervisor.handle(prompt, st.session_state.language)
            st.markdown(result.answer)
            if result.high_risk: st.error("This may be urgent. Prioritise immediate safety and contact the appropriate emergency or professional authority.")
            if result.used_llm: st.caption(f"Response route: {result.provider} - {result.model}")
            else: st.warning("AI providers were unavailable; only the retrieval-safe fallback was shown.")
            if result.sources:
                st.markdown("#### Retrieved sources")
                for source in result.sources:
                    url = source["url"]
                    label = source["title"]
                    st.markdown(f'<div class="source"><b>{label}</b><br>{"<a href="+url+">Open official source</a>" if url else "Knowledge policy source"}<br><small>Relevance score: {source["score"]}</small></div>', unsafe_allow_html=True)
            if st.button("Create action plan", key="make-plan"):
                title, _, _, _ = blueprint(result.intent)
                db.create_case(title, result.intent)
                db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
                st.success("Saved to My Cases.")
            pdf = generate_simple_pdf("Asaan Qanoon AI guidance", result.answer)
            st.download_button("Download guidance PDF", pdf, "asaan-qanoon-guidance.pdf", "application/pdf")
            st.session_state.last_result = result
            db.save_interaction(prompt[:120], st.session_state.language, prompt, result.answer)
            db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
        st.session_state.chat.append({"role": "assistant", "content": result.answer})

elif page == "Action Plans":
    st.markdown('<div class="kicker">Understand -> Act</div>', unsafe_allow_html=True)
    st.title("Action Blueprints")
    choice = st.selectbox("Select a supported workflow", ["Tenant / security deposit", "CNIC / NADRA", "Lost document", "Police / FIR-related issue", "General civic issue"])
    intent = {"Tenant / security deposit": "rent", "CNIC / NADRA": "nadra", "Lost document": "lost_document", "Police / FIR-related issue": "police", "General civic issue": "general_civic"}[choice]
    title, _, _, _ = show_plan(intent, complete=True)
    if st.button("Save this action plan"):
        db.create_case(title, intent)
        db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
        st.success("Plan saved.")

elif page == "Documents":
    st.markdown('<div class="kicker">Act -> Generate</div>', unsafe_allow_html=True)
    st.title("Document Studio")
    st.caption("Create a standard draft from your own information. Review it before submitting or signing.")
    doc_type = st.selectbox("Choose a template", ["General Application", "Complaint Letter", "Undertaking", "Loss Affidavit (draft)", "Rent Agreement (draft)", "Basic Legal Notice (draft)"])
    with st.form("document-form"):
        name = st.text_input("Applicant / party name")
        recipient = st.text_input("Recipient / authority")
        subject = st.text_input("Subject")
        facts = st.text_area("Facts and details", height=160)
        submitted = st.form_submit_button("Generate draft")
    if submitted:
        if not all([name.strip(), recipient.strip(), subject.strip(), facts.strip()]):
            st.error("Please complete all fields.")
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
            st.text_area("Preview", body, height=340)
            db.save_document(doc_type, subject, body)
            db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
            st.download_button("Download PDF draft", generate_simple_pdf(doc_type, body), "asaan-qanoon-draft.pdf", "application/pdf")

elif page == "My Cases":
    st.markdown('<div class="kicker">Your saved work</div>', unsafe_allow_html=True)
    st.title("My Cases")
    cases = db.list_cases()
    if not cases:
        st.info("No saved cases yet. Create an action plan from the Assistant or Action Plans page.")
    for case in cases:
        st.markdown(f'<div class="case"><b>{case["title"]}</b><br><small>{case["status"]} - saved {case["created_at"][:10]}</small></div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            if st.button("Open checklist", key=f"open-{case['id']}"): show_plan(case["intent"], complete=True)
        with b:
            if case["status"] != "Completed" and st.button("Mark completed", key=f"done-{case['id']}"):
                db.update_case_status(case["id"], "Completed")
                db.export_dashboard_data(BASE / "static" / "Dashboard" / "dashboard-db.js")
                st.rerun()

elif page == "Knowledge Sources":
    st.markdown('<div class="kicker">Verify before acting</div>', unsafe_allow_html=True)
    st.title("Knowledge Sources")
    st.warning("This MVP includes a deliberately small starter corpus. It is not a complete database of Pakistani law.")
    for item in rag.docs:
        meta = item.get("metadata", {})
        title, url = meta.get("source_title", "Source"), meta.get("source_url", "")
        st.markdown(f'<div class="source"><b>{title}</b><br>{item["text"]}<br>{"<a href="+url+">Visit source</a>" if url else ""}</div>', unsafe_allow_html=True)
    st.markdown("#### Source standards")
    st.markdown("Only curated sources should be ingested. Preserve source URL, title, jurisdiction, update date, section, and verification status for every knowledge item.")

else:
    st.markdown('<div class="kicker">Personal preferences</div>', unsafe_allow_html=True)
    st.title("Settings")
    with st.form("settings"):
        preferred = st.selectbox("Preferred language", ["Roman Urdu", "Urdu", "English"], index=["Roman Urdu", "Urdu", "English"].index(st.session_state.language))
        simple = st.checkbox("Prefer simple-language explanations", value=True)
        notices = st.checkbox("Show source and safety reminders", value=True)
        if st.form_submit_button("Save preferences"):
            st.session_state.language = preferred
            st.success("Preferences saved for this session.")
    st.divider()
    st.subheader("System status")
    status = router.status()
    for provider, details in status.items():
        state = "Available" if details["healthy"] else f"Cooling down ({details['cooldown_seconds']} seconds)"
        st.write(f"**{provider.title()}**: {state}")
