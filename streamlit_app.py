import streamlit as st
from pathlib import Path
from core.rag import LocalRAG
from core.model_router import ModelRouter
from core.agents import LegalSupervisor
from core.i18n import UI
from core.safety import LEGAL_DISCLAIMER
from core.pdf_generator import generate_simple_pdf

BASE=Path(__file__).parent
st.set_page_config(page_title="Asaan Qanoon AI",page_icon="⚖️",layout="wide",initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--navy:#0B315E;--green:#5AA54E;--ink:#10243E;--muted:#687A8F;--line:rgba(11,49,94,.12);--glass:rgba(255,255,255,.82)}
[data-testid="stAppViewContainer"]{
background:
radial-gradient(circle at 12% 8%,rgba(90,165,78,.13),transparent 28%),
radial-gradient(circle at 88% 14%,rgba(11,49,94,.14),transparent 30%),
linear-gradient(180deg,#FAFCFF 0%,#F2F7FB 100%);
}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.4rem;max-width:1450px}
.hero{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:28px;padding:34px;
background:linear-gradient(135deg,rgba(255,255,255,.95),rgba(236,245,251,.82));box-shadow:0 22px 64px rgba(20,50,80,.10)}
.hero:after{content:"";position:absolute;width:280px;height:280px;right:-80px;top:-130px;border-radius:50%;
background:radial-gradient(circle,rgba(90,165,78,.25),transparent 68%)}
.kicker{font-size:.75rem;letter-spacing:.16em;font-weight:800;color:var(--green);text-transform:uppercase}
.hero h1{color:var(--navy);font-size:2.55rem;line-height:1.02;margin:.45rem 0 .75rem;font-weight:850}
.hero p{color:var(--muted);font-size:1.05rem;max-width:820px}
.pill{display:inline-flex;padding:.42rem .72rem;border-radius:999px;border:1px solid rgba(90,165,78,.25);
background:rgba(90,165,78,.08);color:#315f2d;font-size:.78rem;font-weight:700;margin:.55rem .28rem 0 0}
.card{background:var(--glass);border:1px solid var(--line);border-radius:20px;padding:18px;box-shadow:0 12px 34px rgba(18,46,75,.07);height:100%}
.card h3{font-size:1rem;color:var(--navy);margin:.1rem 0 .45rem}.muted{color:var(--muted);font-size:.88rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#092849,#0B315E)}
[data-testid="stSidebar"] *{color:#F6FAFF}
div[data-testid="stChatMessage"]{background:rgba(255,255,255,.76);border:1px solid var(--line);border-radius:18px;box-shadow:0 8px 24px rgba(16,36,62,.05)}
.stButton>button,.stDownloadButton>button{border-radius:12px;font-weight:760}
</style>
""",unsafe_allow_html=True)

@st.cache_resource
def build_rag():
    return LocalRAG(str(BASE/"data"/"demo_knowledge.jsonl"))

if "chat" not in st.session_state:
    st.session_state.chat=[]

rag=build_rag()
router=ModelRouter(st.secrets)
supervisor=LegalSupervisor(rag,router)

with st.sidebar:
    st.image(str(BASE/"assets"/"asaan_qanoon_logo.jpeg"),use_container_width=True)
    st.markdown("### Navigation")
    page=st.radio("",["Dashboard","AI Assistant","Action Plans","Documents","Knowledge Sources","System Health"],label_visibility="collapsed")
    st.divider()
    language=st.selectbox("Language",["Roman Urdu","Urdu","English"])
    st.caption("ASK → UNDERSTAND → VERIFY → ACT → GENERATE")
    st.caption(LEGAL_DISCLAIMER)

if page=="Dashboard":
    st.markdown("""
    <div class="hero"><div class="kicker">Pakistan • Legal + Civic Intelligence</div>
    <h1>From legal confusion<br/>to clear action.</h1>
    <p>Ask in Roman Urdu, Urdu or English. The system retrieves grounded knowledge,
    explains the issue simply, creates an action blueprint and can generate a draft document.</p>
    <span class="pill">◉ Source-grounded RAG</span>
    <span class="pill">↻ Multi-model fallback</span>
    <span class="pill">⚡ Streamlit-ready</span></div>
    """,unsafe_allow_html=True)
    st.write("")
    cols=st.columns(4)
    cards=[("Languages","3","Roman Urdu • Urdu • English"),
           ("Core Loop","5 steps","Ask → Generate"),
           ("AI Resilience","3 adapters","OpenRouter • Groq • Gemini"),
           ("Knowledge","Verified first","No invented legal facts")]
    for col,(title,big,text) in zip(cols,cards):
        with col:
            st.markdown(f'<div class="card"><h3>{title}</h3><div style="font-size:1.4rem;font-weight:850;color:#0B315E">{big}</div><div class="muted">{text}</div></div>',unsafe_allow_html=True)
    st.write("")
    st.subheader("Popular legal & civic help")
    cols=st.columns(3)
    items=[("🏠 Tenant / Rent","Security deposit, agreements and rent-process guidance."),
           ("🪪 NADRA / CNIC","Identity-document questions grounded in official procedures."),
           ("🚓 Police / FIR","Province-aware procedural guidance with safety guardrails.")]
    for col,(title,text) in zip(cols,items):
        with col:
            st.markdown(f'<div class="card"><h3>{title}</h3><div class="muted">{text}</div></div>',unsafe_allow_html=True)

elif page=="AI Assistant":
    st.markdown('<div class="kicker">Grounded legal & civic assistant</div>',unsafe_allow_html=True)
    st.title("AI Assistant")
    st.caption("Legal/procedural facts should only be stated when supported by retrieved verified context.")
    for item in st.session_state.chat:
        with st.chat_message(item["role"]): st.markdown(item["content"])
    prompt=st.chat_input(UI[language]["placeholder"])
    if prompt:
        st.session_state.chat.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving verified context and selecting an available model..."):
                res=supervisor.handle(prompt,language)
            if res.high_risk: st.error(UI[language]["risk"])
            st.markdown(res.answer)
            if res.used_llm: st.caption(f"AI route: {res.provider} • {res.model}")
            else: st.warning("All configured AI providers were unavailable. Retrieval/rule fallback was used.")
            if res.sources:
                with st.expander("Retrieved sources"):
                    for s in res.sources:
                        if s["url"]: st.markdown(f"- [{s['title']}]({s['url']}) — score {s['score']}")
                        else: st.markdown(f"- {s['title']} — score {s['score']}")
            pdf=generate_simple_pdf("Asaan Qanoon AI Guidance",res.answer)
            st.download_button("Download guidance as PDF",pdf,"asaan_qanoon_guidance.pdf","application/pdf")
        st.session_state.chat.append({"role":"assistant","content":res.answer})

elif page=="Action Plans":
    st.markdown('<div class="kicker">Understand → Act</div>',unsafe_allow_html=True)
    st.title("Action Blueprints")
    st.info("Next build step: supported intents become deterministic, jurisdiction-aware checklists.")
    st.markdown("""**Blueprint contract**
1. Current issue
2. Jurisdiction / authority
3. Required information
4. Ordered actions
5. Evidence to keep
6. Important warnings
7. Official sources
8. Next action
""")

elif page=="Documents":
    st.markdown('<div class="kicker">Act → Generate</div>',unsafe_allow_html=True)
    st.title("Document Studio")
    doc_type=st.selectbox("Template",["General Application","Complaint Letter","Undertaking","Loss Affidavit (draft)","Rent Agreement (draft)"])
    name=st.text_input("Applicant / party name")
    subject=st.text_input("Subject")
    facts=st.text_area("Facts / details")
    if st.button("Generate safe draft"):
        if not (name and subject and facts): st.warning("Complete the required fields.")
        else:
            body=f"""DRAFT — FOR REVIEW

Document type: {doc_type}
Name: {name}
Subject: {subject}

Facts provided by user:
{facts}

Important:
This is a general draft generated from user-provided information. It has not been verified for legal sufficiency, stamp requirements, attestation, jurisdiction-specific clauses, or filing requirements.
"""
            st.code(body,language=None)
            pdf=generate_simple_pdf(doc_type,body)
            st.download_button("Generate PDF",pdf,"asaan_qanoon_draft.pdf","application/pdf")

elif page=="Knowledge Sources":
    st.markdown('<div class="kicker">Verify</div>',unsafe_allow_html=True)
    st.title("Knowledge Sources")
    st.warning("The included corpus is only a starter/demo corpus — not a complete Pakistani legal database.")
    st.markdown("""**Priority ingestion sources**
- Pakistan Code / Ministry of Law & Justice
- NADRA official guidance
- Provincial/territorial Police official guidance
- Applicable tenancy legislation
- Verified government complaint and civic procedure portals

Every chunk should retain **jurisdiction, source URL, title, effective/update date, section/heading, and verification status**.
""")

elif page=="System Health":
    st.markdown('<div class="kicker">Fault-tolerant AI routing</div>',unsafe_allow_html=True)
    st.title("System Health")
    status=router.status()
    cols=st.columns(3)
    for col,provider,key in zip(cols,["openrouter","groq","gemini"],["OPENROUTER_API_KEY","GROQ_API_KEY","GEMINI_API_KEY"]):
        s=status[provider]; configured=bool(st.secrets.get(key,""))
        with col:
            flag="Configured" if configured else "No API key"
            health="Healthy" if s["healthy"] else f"Cooldown {s['cooldown_seconds']}s"
            st.markdown(f'<div class="card"><h3>{provider.title()}</h3><div class="muted">{flag}</div><div style="margin-top:.5rem;font-weight:800">{health}</div><div class="muted">Failures: {s["failures"]}</div></div>',unsafe_allow_html=True)
    st.caption("Model IDs live in Streamlit secrets. When free model availability changes, update configuration rather than agent code.")
