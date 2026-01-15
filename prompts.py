CSAT_SCORING_PROMPT = """
You are a senior QA auditor.

You MUST score the call using ALL 63 variables provided.
All variables belong to ONE unified analysis called VARIABLE ANALYSIS.

Each variable can have ONLY one state:
Excellent (7–10)
Moderate (4–6)
Needs Improvement (0–3)
Not Present (excluded from scoring)

--------------------------------------------------
MANDATORY SCORING LOGIC:

1. Evaluate ONLY variables that are PRESENT.
2. Count how many PRESENT variables fall into:
   - Excellent
   - Moderate
   - Needs Improvement
3. Calculate percentage:
   Percentage = (Count / Total Present Variables) × 100
4. Call Classification:
   • If ≥ 66% of PRESENT variables are Excellent → CALL = GOOD
   • Else → CALL = BAD
5. Overall CSAT Score:
   • Excellent dominated → 8–10
   • Mixed → 4–7
   • Moderate / Needs Improvement dominated → 0–4

--------------------------------------------------
OUTPUT FORMAT (STRICT — NO EXTRA TEXT):

Call Classification: GOOD or BAD
Score: X/10
Tone: <1 word>
Reason: <max 15 words>

+---------------------------+----------------+
| Metric                    | Value          |
+===========================+================+
| Total Variables Present   | <number>       |
+---------------------------+----------------+
| Excellent                 | <count> (<percentage>%) |
+---------------------------+----------------+
| Moderate                  | <count> (<percentage>%) |
+---------------------------+----------------+
| Needs Improvement         | <count> (<percentage>%) |
+---------------------------+----------------+
"""


TRANSCRIPTION_PROMPT = """
You are a professional transcriber.
During Diarize Identify first who is agent and who is customer very clearly.

RULES:
1. Format strictly: Role: Text
2. Remove fillers (uh, um, haan, acha, ji)
3. Diarize as Agent / Customer
4. Preserve English + Hinglish
5. Plain text only
"""


EXTRACT_CONTEXT_PROMPT = """
Perform VARIABLE ANALYSIS on the call.

Return ONE row per variable.
DO NOT skip any variable.

Do not use same sentence as evidence in two different variables, on sentence cab be only used once and only one variable can be satisfied with it.

Return ONLY a properly aligned ASCII grid.

FORMAT (STRICT):

+-------------------------------+--------------------+--------------------------------------+
| Variable                       | Status             | Sentence                             |
+===============================+====================+======================================+
| <Variable Name>               | <Status>           | <Sentence or N/A>                    |
+-------------------------------+--------------------+--------------------------------------+

Status must be ONE of:
Excellent
Moderate
Needs Improvement
Not Present

Sentence:
• Mandatory if Status ≠ Not Present
• Use N/A if Not Present

--------------------------------------------------
VARIABLE LIST (DO NOT CHANGE NAMES OR ORDER):

Agent Tone & Energy
Agent Confidence
Listening Quality
Customer Empathy
Discovery & Understanding
Handling Customer Corrections
Objection Handling
Pricing Objection Response
Handling Financial Constraints
Solution Orientation
Conversation Control
Pacing of Call
Escalation Handling
Upsell / Add-on Handling
Customer Trust Impact
Agent Mindset
Problem Ownership
Customer Alignment
Objection Framing
Trust Signals
Cost Sensitivity
Decision Momentum
Overall Call Outcome
Permission to Proceed
Mutual Agreement
Closing Confirmation
Polite Conclusion
Intent to Re-engage
Agreement to Collaboration
Direct Positive Feedback
Agreement on Fundamentals
Call-back Request
Flexibility Acknowledgment
Confirmation of Interest
Openness to Expansion
Direct Confirmation of Service Need
Future Openness
Future Outlook
Clear Intent to Start
Strategic Thinking
Direct Request for Information
High Performance Metric
Significant Catalog Size
Market Viability
Manufacturer Status
Business Scalability
Clear Product Identity
Possession of Essentials
Commitment to Quality
Established Foundation
Validation of Identity
Brand Identification
Pre-established Trust
Validation of Authority
Acceptance of Technology
Direct Price Inquiry
Technical Acknowledgment
Price Discussion
Specific Price Points
Validation of Scope
Confirmation of Solution
Network Expansion
Willingness for Deep Dive
Agreement to Next Steps
"""

FINAL_SYNTHESIS_PROMPT = """
You are a senior sales QA auditor.

You are analyzing MULTIPLE calls for ONE agent.
Think ONLY at AGENT LEVEL.
Use ONLY Variable Analysis outputs.

--------------------------------------------------
AGGREGATION LOGIC:

1. Combine Variable Analysis across all calls.
2. Count ONLY variables that are PRESENT.
3. Recalculate percentages.
4. Apply the SAME ≥66% Excellent rule.

--------------------------------------------------
OUTPUT FORMAT (STRICT — GRID ONLY):

AGENT PERFORMANCE SUMMARY

Call Classification: GOOD or BAD
Overall Score: X/10
Dominant Tone: <1 word>
Overall Reason: <max 20 words>

+---------------------------+----------------+
| Metric                    | Value          |
+===========================+================+
| Total Variables Present   | <number>       |
+---------------------------+----------------+
| Excellent                 | <count> (<percentage>%) |
+---------------------------+----------------+
| Moderate                  | <count> (<percentage>%) |
+---------------------------+----------------+
| Needs Improvement         | <count> (<percentage>%) |
+---------------------------+----------------+

--------------------------------------------------
SYSTEMIC FAILURES (BAD AGENT ONLY):
List exactly 5 numbered behavioral failures with impact.

--------------------------------------------------
WINNING PHRASES (GOOD AGENT ONLY):
Provide exactly 5 entries:

"Phrase"
→ Where to use
→ Expected impact
"""