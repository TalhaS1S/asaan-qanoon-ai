HIGH_RISK_TERMS = {
    "domestic violence", "suicide", "murder", "kidnap", "kidnapped",
    "threat to life", "bomb", "terrorist", "rape", "sexual assault"
}

def detect_high_risk(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in HIGH_RISK_TERMS)

LEGAL_DISCLAIMER = (
    "Asaan Qanoon AI provides general legal and civic information and procedural "
    "guidance. It is not a substitute for a qualified lawyer, court, police authority, "
    "or government official. Verify important steps from the cited official source."
)
