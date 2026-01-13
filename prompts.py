CSAT_SCORING_PROMPT = """
Analyze this call and give ONLY:

Score: X/10
Reason: <max 15 words>
Tone: <1 word>
"""


TRANSCRIPTION_PROMPT = """
You are a professional transcriber.

RULES:
1. Format strictly: Role: Text
2. Remove fillers (uh, um, haan, acha, ji)
3. Diarize as Agent / Customer
4. Preserve English + Hinglish
5. Plain text only (no markdown)
"""


EXTRACT_CONTEXT_PROMPT = """
Identify presence of the following variables in the call.

For EACH variable found, return:
Variable | Sentence | Frequency

Frequency means number of times it appears in this call.

Variables:
Permission to Proceed, Mutual Agreement, Closing Confirmation, Polite Conclusion,
Intent to Re-engage, Agreement to Collaboration, Direct Positive Feedback,
Agreement on Fundamentals, Call-back Request, Flexibility Acknowledgment,
Confirmation of Interest, Openness to Expansion, Direct Confirmation of Service Need,
Future Openness, Future Outlook, Clear Intent to Start, Strategic Thinking,
Direct Request for Information, High Performance Metric, Significant Catalog Size,
Market Viability, Manufacturer Status, Business Scalability, Clear Product Identity,
Possession of Essentials, Commitment to Quality, Established Foundation,
Validation of Identity, Brand Identification, Pre-established Trust,
Validation of Authority, Acceptance of Technology, Direct Price Inquiry,
Technical Acknowledgment, Price Discussion, Specific Price Points,
Validation of Scope, Confirmation of Solution, Network Expansion,
Willingness for Deep Dive, Agreement to Next Steps
"""


FINAL_SYNTHESIS_PROMPT = """
You are a senior sales QA auditor.

You are analyzing MULTIPLE calls from:
1. ONE GOOD AGENT
2. ONE BAD AGENT

STRICT THINKING RULES:
• Think at AGENT LEVEL, not call level
• Identify CONSISTENT BEHAVIORS
• Do NOT mention URLs or individual calls
• Always justify frequency or assessment with a short behavioral reason
• Be crisp, factual, and audit-style

--------------------------------------------------

[CSAT_SUMMARY]
Provide ONE aggregated CSAT per agent.

Format strictly:

GOOD AGENT:
Score: X/10
Reason: <overall performance reason>
Tone: <dominant tone>

BAD AGENT:
Score: X/10
Reason: <overall performance reason>
Tone: <dominant tone>

--------------------------------------------------

[TABLE_DATA]
Create a comparison table with 3 columns:

Evaluation Variable | GOOD AGENT | BAD AGENT

For EACH cell:
• Start with assessment: Strong / Moderate / Weak
• Then add a SHORT justification (max 15 words)

Variables MUST appear in this order:

Agent Tone & Energy,
Agent Confidence,
Listening Quality,
Customer Empathy,
Discovery & Understanding,
Handling Customer Corrections,
Objection Handling,
Objection Framing,
Handling Financial Constraints,
Pricing Objection Response,
Solution Orientation,
Conversation Control,
Pacing of Call,
Escalation Handling,
Upsell / Add-on Handling,
Customer Trust Impact,
Trust Signals,
Agent Mindset,
Problem Ownership,
Customer Alignment,
Cost Sensitivity,
Decision Momentum,
Overall Call Outcome

--------------------------------------------------

[POSITIVE_CONTEXT_TABLE]
Create a 3-column table:

Context Variable | GOOD AGENT | BAD AGENT

For EACH agent cell:
• Format strictly as:
  Frequency (Total Count) – Short behavioral summary
• If absent:
  "Not Present (0) – Behavior not observed across calls"

Variables MUST appear in this order:

Permission to Proceed,
Validation of Identity,
Validation of Authority,
Brand Identification,
Pre-established Trust,
Direct Request for Information,
Agreement on Fundamentals,
Strategic Thinking,
Market Viability,
Manufacturer Status,
Business Scalability,
High Performance Metric,
Significant Catalog Size,
Possession of Essentials,
Established Foundation,
Mutual Agreement,
Direct Positive Feedback,
Commitment to Quality,
Acceptance of Technology,
Technical Acknowledgment,
Clear Product Identity,
Direct Confirmation of Service Need,
Direct Price Inquiry,
Price Discussion,
Specific Price Points,
Validation of Scope,
Confirmation of Solution,
Confirmation of Interest,
Openness to Expansion,
Willingness for Deep Dive,
Network Expansion,
Clear Intent to Start,
Agreement to Collaboration,
Intent to Re-engage,
Call-back Request,
Agreement to Next Steps,
Future Openness,
Future Outlook,
Flexibility Acknowledgment,
Closing Confirmation,
Polite Conclusion

--------------------------------------------------

[MISSING_ELEMENTS]
List 5 SYSTEMIC failures found repeatedly in BAD AGENT calls.

Rules:
• Must be behavioral
• Must explain impact
• No generic statements

--------------------------------------------------

[WINNING_PHRASES]
Extract 5 phrases used by GOOD AGENT.

Format strictly:
"Winning Phrase"
→ Where to use in Bad Agent call
→ Expected Impact on conversation
"""