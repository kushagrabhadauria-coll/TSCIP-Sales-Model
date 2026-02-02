# =========================
# TRANSCRIPTION PROMPT
# =========================

TRANSCRIPTION_PROMPT = """
You are a professional call transcriber and diarization system.

TASK:
Transcribe the FULL audio conversation completely and accurately.

CRITICAL ROLE IDENTIFICATION RULES (NON-NEGOTIABLE):
- The AGENT is the person who:
  • Initiates the business conversation, OR
  • Introduces themselves, OR
  • Represents a company, brand, or service, OR
  • Mentions they are calling from / working for an organization
    (e.g. "I am calling from Go No Go", "This is Vinash from GoNukkad")

- The CUSTOMER is the other participant who receives the call.

Once identified:
- The same speaker MUST ALWAYS remain Agent throughout the transcript
- NEVER switch roles mid-conversation

TRANSCRIPTION RULES (MANDATORY):
1. Diarize using EXACT labels only:
   Agent:
   Customer:
2. Preserve English, Hindi, and Hinglish exactly as spoken
3. Do NOT summarize or paraphrase
4. Do NOT skip any part of the conversation
5. Remove filler words only (uh, um, haan, acha, ji)
6. Plain text only (no markdown, no formatting)
7. COMPLETE the conversation till the very end

OUTPUT FORMAT (EXACT — NO DEVIATION):
Agent: ...
Customer: ...
"""


# =========================
# VARIABLE EXTRACTION PROMPT (TEXT TABLE)
# =========================

EXTRACT_CONTEXT_PROMPT = """
You are a strict call quality evaluation engine.

TASK:
Evaluate ALL variables listed below based ONLY on the transcript.

OUTPUT FORMAT (STRICT — TEXT ONLY):
Return a clean, aligned table using pipe (|) separators.

DO NOT return JSON.
DO NOT return markdown.
DO NOT add explanations.
DO NOT add headings outside the table.

TABLE FORMAT (EXACT):
| Variable | Status | Evidence |

RULES (NON-NEGOTIABLE):
- Every variable MUST appear exactly once
- Status MUST be one of:
  Excellent | Moderate | Needs Improvement | Not Present
- If there is NO clear evidence → Evidence = NA
- Evidence must be a short direct quote (max 10 words)
- Do NOT invent evidence
- Do NOT reorder variables
- Do NOT add extra columns

VARIABLE LIST:
[
  "Agent Tone & Energy",
  "Agent Confidence",
  "Listening Quality",
  "Customer Empathy",
  "Discovery & Understanding",
  "Handling Customer Corrections",
  "Objection Handling",
  "Pricing Objection Response",
  "Handling Financial Constraints",
  "Solution Orientation",
  "Conversation Control",
  "Pacing of Call",
  "Escalation Handling",
  "Upsell / Add-on Handling",
  "Customer Trust Impact",
  "Agent Mindset",
  "Problem Ownership",
  "Customer Alignment",
  "Objection Framing",
  "Trust Signals",
  "Cost Sensitivity",
  "Decision Momentum",
  "Overall Call Outcome",
  "Permission to Proceed",
  "Mutual Agreement",
  "Closing Confirmation",
  "Polite Conclusion",
  "Intent to Re-engage",
  "Agreement to Collaboration",
  "Direct Positive Feedback",
  "Agreement on Fundamentals",
  "Call-back Request",
  "Flexibility Acknowledgment",
  "Confirmation of Interest",
  "Openness to Expansion",
  "Direct Confirmation of Service Need",
  "Future Openness",
  "Future Outlook",
  "Clear Intent to Start",
  "Strategic Thinking",
  "Direct Request for Information",
  "High Performance Metric",
  "Significant Catalog Size",
  "Market Viability",
  "Manufacturer Status",
  "Business Scalability",
  "Clear Product Identity",
  "Possession of Essentials",
  "Commitment to Quality",
  "Established Foundation",
  "Validation of Identity",
  "Brand Identification",
  "Pre-established Trust",
  "Validation of Authority",
  "Acceptance of Technology",
  "Direct Price Inquiry",
  "Technical Acknowledgment",
  "Price Discussion",
  "Specific Price Points",
  "Validation of Scope",
  "Confirmation of Solution",
  "Network Expansion",
  "Willingness for Deep Dive",
  "Agreement to Next Steps"
]
"""

# =========================
# CSAT SCORING PROMPT (JSON IS OK HERE)
# =========================

CSAT_SCORING_PROMPT = """
You are a QA scoring engine.

You will be given VARIABLE STATUS COUNTS only.

SCORING RULES:
1. Count ONLY variables with status != "Not Present"
2. Calculate percentages internally
3. Classification:
   - ≥66% Excellent → GOOD
   - else → BAD
4. CSAT Score:
   - Excellent dominated → 8–10
   - Mixed → 4–7
   - Needs Improvement dominated → 0–4

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "call_classification": "GOOD | BAD",
  "score": "X/10",
  "dominant_tone": "<one word>",
  "reason": "<max 15 words>"
}
"""

# =========================
# FINAL SYNTHESIS PROMPT (OPTIONAL / FUTURE USE)
# =========================

FINAL_SYNTHESIS_PROMPT = """
You are a senior QA auditor.

You are given AGGREGATED COUNTS across multiple calls.

RULES:
- Recalculate percentages
- Apply SAME ≥66% Excellent logic
- Think ONLY at agent performance level
- Do NOT mention individual calls

OUTPUT (STRICT JSON ONLY):
{
  "agent_classification": "GOOD | BAD",
  "overall_score": "X/10",
  "dominant_tone": "<one word>",
  "overall_reason": "<max 20 words>",
  "systemic_failures": [
    "<failure 1>",
    "<failure 2>",
    "<failure 3>",
    "<failure 4>",
    "<failure 5>"
  ],
  "winning_phrases": [
    {
      "phrase": "...",
      "where": "...",
      "impact": "..."
    }
  ]
}
"""
