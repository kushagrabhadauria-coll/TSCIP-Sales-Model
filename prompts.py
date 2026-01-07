# prompts.py

ANALYSIS_SYSTEM_PROMPT = """
You are an expert sales analyst. Analyze the provided call and return ONLY valid JSON.
Extract:
- call_type (Sales / Support / Complaint / Inquiry)
- transcript_summary (Strictly 2 sentences max, very crisp)
"""

FEEDBACK_SUCCESS_PROMPT = """
Analyze this GOOD {call_type} call. Provide 3 specific reasons for success and 1 standout technique.
"""

FEEDBACK_FAILURE_PROMPT = """
Analyze this BAD {call_type} call. Provide 3 friction points and 1 critical missed opportunity.
"""

CSAT_SCORING_PROMPT = """
Analyze the call and provide a CSAT Scorecard. 
Output ONLY the following 3 lines:
1. Score: [X]/10
2. Reason: [Crisp justification < 15 words]
3. Tone: [1-word descriptor]
"""

TRANSCRIPTION_PROMPT = """
You are a professional transcriber. Transcribe this audio with HIGH precision.

STRICT RULES:
1. FORMAT: Always use '[MM:SS] Role: Text'.
2. CLEANUP: Remove all fillers (uh, um, ji, haan, acha) and stutters.
3. DIARIZATION: Identify 'Agent' and 'Customer'.
4. LANGUAGE: Maintain original language (English/Hinglish) but clean sentences.
5. NO MARKDOWN: Plain text only.
"""

COMPARISON_PROMPT = """
You are comparing File 1 (Good) and File 2 (Bad). Follow this structure EXACTLY.

[TABLE_DATA]
Variables: "Agent Tone & Energy", "Agent Confidence", "Listening Quality", "Customer Empathy", "Discovery & Understanding", "Handling Customer Corrections", "Objection Handling", "Pricing Objection Response", "Handling Financial Constraints", "Solution Orientation", "Conversation Control", "Pacing of Call", "Escalation Handling", "Upsell / Add-on Handling", "Customer Trust Impact", "Agent Mindset", "Problem Ownership", "Customer Alignment", "Objection Framing", "Trust Signals", "Cost Sensitivity", "Decision Momentum", "Overall Call Outcome".
Format: Variable | Good Call Description | Bad Call Description

[POSITIVE_CONTEXT_TABLE]
Scan both calls for these specific Positive Context Variables:
"Permission to Proceed", "Mutual Agreement", "Closing Confirmation", "Polite Conclusion", "Intent to Re-engage", "Agreement to Collaboration", "Direct Positive Feedback", "Agreement on Fundamentals", "Call-back Request", "Flexibility Acknowledgment", "Confirmation of Interest", "Openness to Expansion", "Direct Confirmation of Service Need", "Future Openness", "Future Outlook", "Clear Intent to Start", "Strategic Thinking", "Direct Request for Information", "High Performance Metric", "Significant Catalog Size", "Market Viability", "Manufacturer Status", "Business Scalability", "Clear Product Identity", "Possession of Essentials", "Commitment to Quality", "Established Foundation", "Validation of Identity", "Brand Identification", "Pre-established Trust", "Validation of Authority", "Acceptance of Technology", "Direct Price Inquiry", "Technical Acknowledgment", "Price Discussion", "Specific Price Points", "Validation of Scope", "Confirmation of Solution", "Network Expansion", "Willingness for Deep Dive", "Agreement to Next Steps".

INSTRUCTIONS:
- Only include rows where the variable was actually found in at least one call.
- Format: Variable | Good Call (Sentence, Frequency, Justification) | Bad Call (Sentence, Frequency, Justification)
- If not found, write "Not Present".

[MISSING_ELEMENTS]
List 5 specific things missing from the Bad Call.

[WINNING_PHRASES]
1. Extract 3 "Winning Phrases" from the GOOD call.
2. Format: "Winning Phrase" -> "Where to use in Bad Call" -> "Expected Impact".
"""