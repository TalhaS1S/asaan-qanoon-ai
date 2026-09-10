# Asaan Qanoon AI — Streamlit Starter

This starter follows the product loop:
**ASK → UNDERSTAND → VERIFY → ACT → GENERATE**

## Included
- futuristic Streamlit UI using the supplied Asaan Qanoon branding
- Roman Urdu / Urdu / English switch
- source-grounded local RAG starter
- intent routing
- OpenRouter + Groq + Gemini fallback adapters
- circuit-breaker cooldown
- retrieval-only fallback if every LLM fails
- PDF generation
- starter safety guardrails

## Important
`data/demo_knowledge.jsonl` is NOT a complete legal corpus. It is only a starter schema/policy corpus. Ingest and review authoritative legal/procedural material before presenting legal facts.

## Local setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run streamlit_app.py
```

## Provider configuration
In `.streamlit/secrets.toml`:
- OpenRouter: use `openrouter/free` as the default router if desired.
- Groq: set the API key and a currently available free-tier model ID.
- Gemini: set the API key and a currently available free-tier model ID.

Do not hard-code volatile free model IDs inside agent logic.

## GitHub
```bash
git init
git add .
git commit -m "Initial Asaan Qanoon AI MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/asaan-qanoon-ai.git
git push -u origin main
```

## Streamlit Community Cloud
1. Sign in with GitHub.
2. Create app.
3. Choose the repository.
4. Entrypoint: `streamlit_app.py`.
5. Add API keys under App Settings → Secrets.
6. Deploy.

## Recommended next phases
1. Build verified legal corpus.
2. Upgrade retrieval to BM25 + local embeddings + FAISS.
3. Add explicit multi-agent state graph.
4. Add citation verifier and jurisdiction gate.
5. Add document templates.
6. Add saved cases/auth only after the core demo is stable.
