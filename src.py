# =========================
# IMPORTS
# =========================

import os
import requests
import pandas as pd
import pytz
from datetime import datetime
from collections import Counter

import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from prompts import TRANSCRIPTION_PROMPT, EXTRACT_CONTEXT_PROMPT

# =========================
# CONFIGURATION
# =========================

PROJECT_ID = "mec-transcript"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel(MODEL_NAME)

# =========================
# UTILS & HELPERS
# =========================

def get_ist_time():
    """Returns current time in Indian Standard Time (IST)."""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")

def call_gemini(prompt=None, parts=None):
    """Calls Vertex AI returning plain text."""
    config = GenerationConfig(
        temperature=0,
        max_output_tokens=8192
    )
    
    response = model.generate_content(
        parts if parts else prompt,
        generation_config=config
    )
    return response.text.strip()

# =========================
# CORE LOGIC
# =========================

def transcribe_audio(audio_url):
    """Transcribes audio URL."""
    try:
        audio_bytes = requests.get(audio_url, timeout=60).content
        parts = [
            Part.from_text(TRANSCRIPTION_PROMPT),
            Part.from_data(audio_bytes, mime_type="audio/mpeg")
        ]
        return call_gemini(parts=parts)
    except Exception as e:
        return f"Error transcribing: {str(e)}"

def extract_variable_analysis(transcript):
    """
    Extracts variables by parsing the TEXT TABLE returned by the prompt.
    Does NOT rely on JSON.
    """
    prompt = EXTRACT_CONTEXT_PROMPT + "\n\nTRANSCRIPT:\n" + transcript
    raw_text = call_gemini(prompt=prompt)
    
    variables = []
    
    # Parse the pipe-separated table
    lines = raw_text.splitlines()
    for line in lines:
        if "|" not in line:
            continue
            
        # Remove outer pipes and split
        cols = [c.strip() for c in line.strip("|").split("|")]
        
        # Skip header or malformed lines
        if len(cols) < 3 or cols[0].lower() == "variable" or "---" in cols[0]:
            continue

        variables.append({
            "variable": cols[0],
            "status": cols[1],
            "evidence": cols[2] if len(cols) > 2 else "NA"
        })

    return variables

def compute_summary(variables):
    """Calculates scores based on extracted variables, excluding 'Not Present'."""
    if not variables:
        return {"counts": {}, "excellent_percentage": 0, "call_type": "ERROR", "total_possible": 0, "considered": 0}

    counts = Counter(v["status"] for v in variables)
    total_possible = len(variables)
    not_present = counts.get("Not Present", 0)
    
    # Logic: Total minus Not Present
    considered = total_possible - not_present

    excellent_pct = round(
        (counts["Excellent"] / considered) * 100, 2
    ) if considered > 0 else 0

    call_type = "GOOD" if excellent_pct >= 66 else "BAD"

    # Add extra metadata to the summary dictionary
    return {
        "counts": dict(counts),
        "excellent_percentage": excellent_pct,
        "call_type": call_type,
        "total_possible": total_possible,
        "considered": considered
    }

# =========================
# PIPELINE RUNNER
# =========================

def process_call(call):
    timestamp = get_ist_time()
    print(f"[{timestamp}] Processing Call {call['index']}...")

    transcript = transcribe_audio(call["audio_url"])
    variables = extract_variable_analysis(transcript)
    summary = compute_summary(variables)

    return {
        "index": call["index"],
        "url": call["audio_url"],
        "timestamp": timestamp,
        "transcript": transcript,
        "variables": variables,
        "summary": summary
    }

def load_calls(excel_path):
    df = pd.read_excel(excel_path)
    return [
        {"index": i + 1, "audio_url": url}
        for i, url in enumerate(df["recording_url"])
        if pd.notna(url)
    ]

# =========================
# MAIN EXECUTION
# =========================

if __name__ == "__main__":
    
    # Input/Output Config
    INPUT_EXCEL = "calls_4.xlsx"
    OUTPUT_DIR = "output"
    TRANSCRIPT_DIR = f"{OUTPUT_DIR}/transcripts"
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    
    SUMMARY_REPORT = f"{OUTPUT_DIR}/summary_report.txt"

    calls = load_calls(INPUT_EXCEL)
    results = []

    # 1. Process all calls
    for call in calls:
        results.append(process_call(call))

   # 2. Save All Transcripts to a Single File
    ALL_TRANSCRIPTS_FILE = f"{OUTPUT_DIR}/all_call_transcripts.txt"
    print(f"\nSaving all transcripts to {ALL_TRANSCRIPTS_FILE}...")
    
    with open(ALL_TRANSCRIPTS_FILE, "a", encoding="utf-8") as f:
        for r in results:
            f.write(f"{'#'*40}\n")
            f.write(f"CALL INDEX: {r['index']}\n")
            f.write(f"{'#'*40}\n")
            f.write(f"CALL METADATA\n")
            f.write(f"==========================\n")
            f.write(f"Timestamp  : {r['timestamp']}\n")
            f.write(f"Audio URL  : {r['url']}\n")
            f.write(f"Result     : {r['summary']['call_type']} ({r['summary']['excellent_percentage']}%)\n")
            f.write(f"==========================\n\n")
            f.write(f"TRANSCRIPT\n")
            f.write(f"--------------------------\n")
            f.write(r['transcript'])
            f.write(f"\n--------------------------\n")
            f.write(f"End of Transcript for Call {r['index']}\n\n")
            f.write(f"{'='*80}\n\n") # Visual separator between different calls
    # 3. Save Summary Report
    print(f"Saving summary report to {SUMMARY_REPORT}...")
    
    with open(SUMMARY_REPORT, "a", encoding="utf-8") as f:
        for r in results:
            f.write(f"\n{'='*80}\n")
            f.write(f"CALL {r['index']} ANALYSIS REPORT\n")
            f.write(f"{'='*80}\n")
            f.write(f"Time (IST) : {r['timestamp']}\n")
            f.write(f"URL        : {r['url']}\n")
            f.write(f"Result     : {r['summary']['call_type']} ({r['summary']['excellent_percentage']}%)\n\n")

            header = f"| {'Variable':<40} | {'Status':<20} | {'Evidence'} |\n"
            divider = f"|{'-'*42}|{'-'*22}|{'-'*50}|\n"
            
            f.write(divider)
            f.write(header)
            f.write(divider)

            for v in r["variables"]:
                evidence = str(v.get('evidence', 'NA')).replace('\n', ' ')
                variable = str(v.get('variable', 'Unknown'))
                status = str(v.get('status', 'Unknown'))
                f.write(f"| {variable:<40} | {status:<20} | {evidence}\n")

            f.write(divider)
            
            # UPDATED SCORING METRICS SECTION
            summary = r['summary']
            counts = summary['counts']
            
            f.write(f"\nSCORING METRICS:\n")
            f.write(f"{'-'*20}\n")
            f.write(f"Total Variables        : {summary['total_possible']}\n")
            f.write(f"Not Present            : {counts.get('Not Present', 0)}\n")
            f.write(f"Total Evaluated (Net)  : {summary['considered']}\n")
            f.write(f"{'-'*20}\n")
            f.write(f"Excellent              : {counts.get('Excellent', 0)}\n")
            f.write(f"Moderate               : {counts.get('Moderate', 0)}\n")
            f.write(f"Needs Improvement      : {counts.get('Needs Improvement', 0)}\n")
            f.write(f"{'-'*20}\n")
            f.write(f"Final Percentage Score : {summary['excellent_percentage']}%\n")
            f.write(f"Call Classification    : {summary['call_type']}\n")
            f.write(f"\n\n")

    print("\nPipeline completed successfully!")