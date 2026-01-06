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
1. FORMAT: Always use '[MM:SS] Role: Text' (e.g., [00:12] Agent: Hello).
2. CLEANUP: Remove all fillers like 'uh', 'um', 'ji', 'haan', 'acha' (when used as filler), and stutters/repetitions.
3. DIARIZATION: Correctly identify the 'Agent' and the 'Customer'. 
   - Note: The person calling and introducing themselves/the company is the Agent.
4. LANGUAGE: Maintain the original language (English/Hindi) but keep the sentences grammatically clean.
5. NO MARKDOWN: Do not use bold (**) or italics. Just plain text.
"""

COMPARISON_PROMPT = """
You are comparing two calls: File 1 (Good Call) and File 2 (Bad Call). 
Follow the structure below EXACTLY. Use the bracketed tags to separate sections.

[TABLE_DATA]
List the comparison rows using the '|' separator. 
Variables: "Agent Tone & Energy", "Agent Confidence", "Listening Quality", "Customer Empathy", "Discovery & Understanding", "Handling Customer Corrections", "Objection Handling", "Pricing Objection Response", "Handling Financial Constraints", "Solution Orientation", "Conversation Control", "Pacing of Call", "Escalation Handling", "Upsell / Add-on Handling", "Customer Trust Impact", "Agent Mindset", "Problem Ownership", "Customer Alignment", "Objection Framing", "Trust Signals", "Cost Sensitivity", "Decision Momentum", "Overall Call Outcome".

[MISSING_ELEMENTS]
List 5 specific things missing from the Bad Call.

[WINNING_PHRASES]
1. Extract 3 "Winning Phrases" from the GOOD call.
2. Format: "Winning Phrase" -> "Where to use in Bad Call" -> "Expected Impact".
"""