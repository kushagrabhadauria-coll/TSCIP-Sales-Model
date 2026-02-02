# =========================
# IMPORTS
# =========================

import os
import requests
import pandas as pd
from datetime import datetime
from collections import Counter

import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from prompts import TRANSCRIPTION_PROMPT, EXTRACT_CONTEXT_PROMPT

# =========================
# VERTEX AI INIT
# =========================

import vertexai

vertexai.init(
    project="mec-transcript",
    location="us-central1" 
)

model = GenerativeModel("gemini-2.5-flash")

# =========================
# GEMINI HELPER
# =========================

def call_gemini(prompt=None, parts=None):
    response = model.generate_content(
        parts if parts else prompt,
        generation_config=GenerationConfig(
            temperature=0,
            max_output_tokens=4096
        )
    )
    return response.text.strip()

# =========================
# TRANSCRIPTION
# =========================

def transcribe_audio(audio_url):
    audio_bytes = requests.get(audio_url, timeout=60).content
    parts = [
        Part.from_text(TRANSCRIPTION_PROMPT),
        Part.from_data(audio_bytes, mime_type="audio/mpeg")
    ]
    return call_gemini(parts=parts)

# =========================
# VARIABLE EXTRACTION
# =========================

def extract_variable_analysis(transcript):
    prompt = EXTRACT_CONTEXT_PROMPT + "\n\nTRANSCRIPT:\n" + transcript
    table_text = call_gemini(prompt=prompt)

    variables = []

    for line in table_text.splitlines():
        if not line.startswith("|"):
            continue

        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) != 3 or cols[0] == "Variable":
            continue

        variables.append({
            "variable": cols[0],
            "status": cols[1],
            "evidence": cols[2]
        })

    return variables

# =========================
# CALL METRICS
# =========================

def compute_summary(variables):
    counts = Counter(v["status"] for v in variables)

    considered = (
        counts["Excellent"] +
        counts["Moderate"] +
        counts["Needs Improvement"]
    )

    excellent_pct = round(
        (counts["Excellent"] / considered) * 100, 2
    ) if considered else 0

    call_type = "GOOD" if excellent_pct >= 66 else "BAD"

    return {
        "counts": dict(counts),
        "excellent_percentage": excellent_pct,
        "call_type": call_type
    }

# =========================
# PROCESS SINGLE CALL
# =========================

def process_call(call):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"[PROCESSING] Call {call['index']}")

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

# =========================
# LOAD INPUT
# =========================

def load_calls(excel_path):
    df = pd.read_excel(excel_path)
    return [
        {"index": i + 1, "audio_url": url}
        for i, url in enumerate(df["recording_url"])
        if pd.notna(url)
    ]

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    INPUT_EXCEL = "calls.xlsx"
    OUTPUT_DIR = "output"
    TRANSCRIPT_DIR = f"{OUTPUT_DIR}/transcripts"
    PIPELINE_FILE = f"{OUTPUT_DIR}/pipeline_output.txt"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    calls = load_calls(INPUT_EXCEL)

    results = []
    for call in calls:
        results.append(process_call(call))

    # =========================
    # SAVE TRANSCRIPTS
    # =========================

    for r in results:
        path = f"{TRANSCRIPT_DIR}/call_{r['index']}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TIMESTAMP : {r['timestamp']}\n")
            f.write(f"CALL INDEX: {r['index']}\n")
            f.write(f"CALL URL  : {r['url']}\n\n")
            f.write(r["transcript"])

    # =========================
    # SAVE PIPELINE OUTPUT
    # =========================

    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"\nCALL {r['index']}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp : {r['timestamp']}\n")
            f.write(f"Audio URL : {r['url']}\n\n")

            f.write("| Variable | Status | Evidence |\n")
            f.write("|" + "-" * 78 + "|\n")

            for v in r["variables"]:
                f.write(
                    f"| {v['variable']} | {v['status']} | {v['evidence']} |\n"
                )

            f.write("\nSUMMARY\n")
            f.write("-" * 40 + "\n")
            for k, v in r["summary"]["counts"].items():
                f.write(f"{k}: {v}\n")
            f.write(f"Excellent %: {r['summary']['excellent_percentage']}\n")
            f.write(f"Call Type : {r['summary']['call_type']}\n")
            f.write("=" * 80 + "\n")

    print("Pipeline completed successfully")
