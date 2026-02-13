# =========================
# IMPORTS
# =========================

import os
import time
import requests
import pandas as pd
import pytz
import threading
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from prompts import TRANSCRIPTION_PROMPT, EXTRACT_CONTEXT_PROMPT

# =========================
# CONFIGURATION
# =========================

PROJECT_ID = "mec-transcript"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

# Processing Config
BATCH_SIZE = 5             # Number of concurrent calls to process
MAX_RETRIES_GEMINI = 3     # Retries for each Gemini API call

EXPECTED_VARIABLES = 64    # Expected number of variables from the prompt
MIN_AUDIO_SIZE = 10240     # 10KB minimum audio file size

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel(MODEL_NAME)

# Thread lock for safe file writes
file_write_lock = threading.Lock()

# =========================
# UTILS & HELPERS
# =========================

def get_ist_time():
    """Returns current time in Indian Standard Time (IST)."""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")

def call_gemini(prompt=None, parts=None):
    """
    Calls Vertex AI with retry logic (exponential backoff).
    Returns plain text response.
    """
    config = GenerationConfig(
        temperature=0,
        max_output_tokens=16384   # FIX #6: Increased from 8192
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES_GEMINI + 1):
        try:
            response = model.generate_content(
                parts if parts else prompt,
                generation_config=config
            )
            return response.text.strip()
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES_GEMINI:
                wait_time = 2 ** attempt  # 2s, 4s, 8s
                print(f"      [RETRY] Gemini attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"      [FAIL] Gemini failed after {MAX_RETRIES_GEMINI} attempts: {e}")

    raise last_error

# =========================
# AUDIO VALIDATION
# =========================

def download_and_validate_audio(audio_url):
    """
    Downloads audio and validates it.
    Returns (audio_bytes, mime_type) on success.
    Raises ValueError on validation failure.
    """
    response = requests.get(audio_url, timeout=60)

    # FIX #3a: Check HTTP status
    if response.status_code != 200:
        raise ValueError(f"HTTP {response.status_code} — server did not return audio")

    audio_bytes = response.content

    # FIX #3b: Check if server returned HTML instead of audio (expired token / error page)
    content_type = response.headers.get("Content-Type", "")
    try:
        first_bytes = audio_bytes[:500].decode("utf-8", errors="ignore").lower()
        if "<html" in first_bytes or "<!doctype" in first_bytes:
            raise ValueError(f"Server returned HTML instead of audio (token may have expired)")
    except Exception:
        pass  # binary data = likely actual audio, which is fine

    # FIX #3c: Check minimum file size
    if len(audio_bytes) < MIN_AUDIO_SIZE:
        raise ValueError(f"Audio too small ({len(audio_bytes)} bytes) — likely empty/corrupt")

    # FIX #4: Always use audio/mpeg (safest for Gemini, matches original working code)
    mime_type = "audio/mpeg"


    return audio_bytes, mime_type

# =========================
# TRANSCRIPT QUALITY CHECK
# =========================

def check_transcript_quality(transcript):
    """
    Detects hallucinated/garbage transcripts.
    Returns (is_good, reason).
    """
    if not transcript or len(transcript.strip()) < 20:
        return False, "EMPTY_TRANSCRIPT"

    # Check for repetitive hallucination
    words = transcript.split()
    if len(words) > 20:
        word_counts = Counter(words)
        most_common_word, most_common_count = word_counts.most_common(1)[0]
        repetition_ratio = most_common_count / len(words)
        if repetition_ratio > 0.5:
            return False, f"HALLUCINATED_REPEAT ('{most_common_word}' repeated {most_common_count}/{len(words)} times)"

    # Check for diarization
    has_agent = "Agent:" in transcript or "agent:" in transcript.lower()
    has_customer = "Customer:" in transcript or "customer:" in transcript.lower()
    if not has_agent and not has_customer:
        return False, "NO_DIARIZATION (no Agent:/Customer: labels found)"

    return True, "OK"

# =========================
# CORE LOGIC
# =========================

def transcribe_audio(audio_url):
    """
    Transcribes audio URL with validation.
    Returns (transcript, error_reason).
    """
    try:
        audio_bytes, mime_type = download_and_validate_audio(audio_url)

        parts = [
            Part.from_text(TRANSCRIPTION_PROMPT),
            Part.from_data(audio_bytes, mime_type=mime_type)
        ]
        transcript = call_gemini(parts=parts)

        is_good, reason = check_transcript_quality(transcript)
        if not is_good:
            return transcript, f"BAD_TRANSCRIPT: {reason}"

        return transcript, None

    except ValueError as ve:
        return None, f"AUDIO_VALIDATION_FAILED: {str(ve)}"
    except Exception as e:
        return None, f"TRANSCRIPTION_ERROR: {str(e)}"

def extract_variable_analysis(transcript):
    """
    Extracts variables by parsing the TEXT TABLE returned by the prompt.
    """
    prompt = EXTRACT_CONTEXT_PROMPT + "\n\nTRANSCRIPT:\n" + transcript
    raw_text = call_gemini(prompt=prompt)

    variables = []

    lines = raw_text.splitlines()
    for line in lines:
        if "|" not in line:
            continue

        cols = [c.strip() for c in line.strip("|").split("|")]

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

    considered = total_possible - not_present

    # FIX #1: Use .get() to prevent KeyError
    excellent_pct = round(
        (counts.get("Excellent", 0) / considered) * 100, 2
    ) if considered > 0 else 0

    call_type = "GOOD" if excellent_pct >= 40 else "BAD"

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
    """Process a single call through the full pipeline."""
    timestamp = get_ist_time()
    print(f"  [{timestamp}] Processing Call {call['index']}...")

    # Step 1: Transcribe
    transcript, error_reason = transcribe_audio(call["audio_url"])

    # FIX #2: Don't pass errors forward silently
    if error_reason:
        print(f"    [WARN] Call {call['index']}: {error_reason}")
        saved_transcript = transcript if transcript else f"[FAILED] {error_reason}"

        return {
            "index": call["index"],
            "url": call["audio_url"],
            "timestamp": timestamp,
            "transcript": saved_transcript,
            "variables": [],
            "summary": {"counts": {}, "excellent_percentage": 0, "call_type": "ERROR",
                         "total_possible": 0, "considered": 0},
            "error": error_reason,
            "is_complete": False
        }

    # Step 2: Extract variables
    try:
        variables = extract_variable_analysis(transcript)
    except Exception as e:
        print(f"    [WARN] Call {call['index']}: Variable extraction failed: {e}")
        return {
            "index": call["index"],
            "url": call["audio_url"],
            "timestamp": timestamp,
            "transcript": transcript,
            "variables": [],
            "summary": {"counts": {}, "excellent_percentage": 0, "call_type": "ERROR",
                         "total_possible": 0, "considered": 0},
            "error": f"VARIABLE_EXTRACTION_FAILED: {str(e)}",
            "is_complete": False
        }

    # Step 3: Compute summary
    summary = compute_summary(variables)

    is_complete = len(variables) >= EXPECTED_VARIABLES
    if not is_complete:
        print(f"    [WARN] Call {call['index']}: Only {len(variables)}/{EXPECTED_VARIABLES} variables extracted")

    return {
        "index": call["index"],
        "url": call["audio_url"],
        "timestamp": timestamp,
        "transcript": transcript,
        "variables": variables,
        "summary": summary,
        "error": None,
        "is_complete": is_complete
    }

def load_calls(excel_path):
    df = pd.read_excel(excel_path)
    return [
        {"index": i + 1, "audio_url": url}
        for i, url in enumerate(df["recording_url"])
        if pd.notna(url)
    ]

# =========================
# THREAD-SAFE FILE WRITERS
# =========================

def save_transcript(r, filepath):
    """Append a single transcript to the transcripts file (thread-safe)."""
    with file_write_lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{'#'*40}\n")
            f.write(f"CALL INDEX: {r['index']}\n")
            f.write(f"{'#'*40}\n")
            f.write(f"Timestamp : {r['timestamp']}\n")
            f.write(f"Audio URL : {r['url']}\n")
            f.write(f"Result    : {r['summary']['call_type']} ({r['summary']['excellent_percentage']}%)\n")
            if r.get("error"):
                f.write(f"Error     : {r['error']}\n")
            f.write("\n")
            f.write("TRANSCRIPT\n")
            f.write("-"*30 + "\n")
            f.write(r['transcript'])
            f.write("\n" + "="*80 + "\n\n")

def save_summary_report(r, filepath):
    """Append a single summary report (thread-safe)."""
    with file_write_lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"CALL {r['index']} ANALYSIS REPORT\n")
            f.write(f"{'='*80}\n")
            f.write(f"Time (IST): {r['timestamp']}\n")
            f.write(f"URL       : {r['url']}\n")
            f.write(f"Result    : {r['summary']['call_type']} ({r['summary']['excellent_percentage']}%)\n")
            if r.get("error"):
                f.write(f"Error     : {r['error']}\n")
            f.write("\n")

            header = f"| {'Variable':<40} | {'Status':<20} | {'Evidence'} |\n"
            divider = f"|{'-'*42}|{'-'*22}|{'-'*50}|\n"

            f.write(divider)
            f.write(header)
            f.write(divider)

            for v in r["variables"]:
                evidence = str(v.get("evidence", "NA")).replace("\n", " ")
                f.write(f"| {v['variable']:<40} | {v['status']:<20} | {evidence}\n")

            f.write(divider)

            summary = r["summary"]
            counts = summary["counts"]

            f.write("\nSCORING METRICS\n")
            f.write("-"*20 + "\n")
            f.write(f"Total Variables : {summary['total_possible']}\n")
            f.write(f"Not Present     : {counts.get('Not Present', 0)}\n")
            f.write(f"Evaluated       : {summary['considered']}\n")
            f.write(f"Excellent       : {counts.get('Excellent', 0)}\n")
            f.write(f"Moderate        : {counts.get('Moderate', 0)}\n")
            f.write(f"Needs Improve   : {counts.get('Needs Improvement', 0)}\n")
            f.write(f"Final Score     : {summary['excellent_percentage']}%\n")
            f.write(f"Classification  : {summary['call_type']}\n\n")

# =========================
# BATCH PROCESSOR
# =========================

def process_batch(calls_batch, transcript_file, summary_file):
    """
    Process a batch of calls concurrently using ThreadPoolExecutor.
    Returns list of result dicts.
    """
    results = []

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        future_to_call = {
            executor.submit(process_call, call): call
            for call in calls_batch
        }

        for future in as_completed(future_to_call):
            call = future_to_call[future]
            try:
                r = future.result()

                # Immediately save results (thread-safe)
                save_transcript(r, transcript_file)
                save_summary_report(r, summary_file)

                status = "✓" if r['is_complete'] else f"⚠ ({r.get('error', 'INCOMPLETE')})"
                print(f"  Call {r['index']} completed {status}")

                results.append(r)

            except Exception as e:
                print(f"  [FATAL] Call {call['index']} crashed: {e}")
                results.append({
                    "index": call["index"],
                    "url": call["audio_url"],
                    "timestamp": get_ist_time(),
                    "transcript": f"[CRASHED] {str(e)}",
                    "variables": [],
                    "summary": {"counts": {}, "excellent_percentage": 0, "call_type": "ERROR",
                                "total_possible": 0, "considered": 0},
                    "error": f"CRASH: {str(e)}",
                    "is_complete": False
                })

    return results

# =========================
# MAIN EXECUTION
# =========================
if __name__ == "__main__":
    # ---------------------------------------------------------
    # Input / Output Config
    # ---------------------------------------------------------
    INPUT_EXCEL = "calls_4.xlsx"
    OUTPUT_DIR = "test"
    TRANSCRIPT_DIR = f"{OUTPUT_DIR}/transcripts"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    SUMMARY_REPORT = f"{OUTPUT_DIR}/summary_report_single_call.txt"
    ALL_TRANSCRIPTS_FILE = f"{OUTPUT_DIR}/call_transcripts_single.txt"

    # ---------------------------------------------------------
    # CALL SOURCE CONFIG
    # ---------------------------------------------------------
    USE_MANUAL_URLS = True

    if USE_MANUAL_URLS:
        URLS = ['https://cloudphone.tatateleservices.com/file/recording?callId=1764655955.828742&type=rec&token=SXZlc0pvZ01Xa3NRZkNBcUtwVnZFUEVSeEhCZDlQTUVZNmtWekIzc1VMYUNtTmQxNUZqTlZIMVMzV2tndTZyazo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764670103.213014&type=rec&token=RnZJZjhyanpYcE5OY3lxbEFxV0FRZmxOSHpPTUdKaCtWVVc3elFic0ZCZW5jZlR0K29sMVlJTmFzaldQOHNCSjo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764668007.33215&type=rec&token=L1p0UjFObnBSMDJqZXpRQ1VjSnpIcE9QVEdjNnRuRHRCM2VIYU1XaitncE1wZ3lkbkFDb0xidnFJMFFxVjVJWjo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764651482.1097070&type=rec&token=aWtXL0hjaFUvLzRleFFZU1Vrb1dnMHlHekx5UHFFTG93SmNraGhycUE1M2pJWnIyc1NzOFBFK2VyRkYrcnlRQjo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764677088.131847&type=rec&token=WWtjTWY2Nk5SMGtreHFScS9GZGtNbkp6c09WZnFBRy9QOVJ0MUs5aFNodWw3djRmeFhHNytKREZBVmhPcVZvZjo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764679305.234202&type=rec&token=cEsxNW9TdW51S09lWS9ibVRHZlFmU1dBNUk0U0hWL3hNTklUamdCeUhoZlhPR0lqMjRKTTRXcVNRVFhFTFN4Zjo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764655838.154382&type=rec&token=ZnpKdm1MS01yYmN1UDkyVjlJQnZwWmhLZ1kwazAxQzNHODlUbnJYVXNDQ1RUdFk1T1UvaGwzc0dFS0pkUFVteDo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764673422.36376&type=rec&token=eGNKUU9jOGhZQmZsMHdzOEZmTEdMcUd4akRoVnZBZTBHYVZkQkpQTTlmSk0wcTRwYjBuakFYWGFEZHVIbmFzbTo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764578779.62121&type=rec&token=Q3QrY0x3QVAralVydE9GY2V5YjdjeUdDalo3WXVaUm9HTWtzRmJrK3BGWVpyK3paZlREQS85dUxhVkF4UTh1cDo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        'https://cloudphone.tatateleservices.com/file/recording?callId=1764584831.86309&type=rec&token=RDVKUlFtZW9oYzhHaVp5cnhPQ2RzSTQ5dHovcGg0ZzYvalRUeTFrR1p5SzM3T1VjS2lyMVRPNGFDc2RabnJBODo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D',
        ]
        calls = [
            {"index": i + 1, "audio_url": url}
            for i, url in enumerate(URLS)
        ]
    else:
        calls = load_calls(INPUT_EXCEL)

    print(f"\nTotal calls to process: {len(calls)}\n")

    # ---------------------------------------------------------
    # PASS 1: Process calls in batches
    # ---------------------------------------------------------
    print(f"{'='*60}")
    print(f"PASS 1: Processing {len(calls)} calls (batch size: {BATCH_SIZE})")
    print(f"{'='*60}\n")

    all_results = []

    for batch_start in range(0, len(calls), BATCH_SIZE):
        batch = calls[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(calls) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n--- Batch {batch_num}/{total_batches} (Calls: {[c['index'] for c in batch]}) ---")

        batch_results = process_batch(batch, ALL_TRANSCRIPTS_FILE, SUMMARY_REPORT)
        all_results.extend(batch_results)



    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE — FINAL SUMMARY")
    print(f"{'='*60}")

    total = len(all_results)
    good = sum(1 for r in all_results if r['summary']['call_type'] == 'GOOD')
    bad = sum(1 for r in all_results if r['summary']['call_type'] == 'BAD')
    errors = sum(1 for r in all_results if r['summary']['call_type'] == 'ERROR')
    complete = sum(1 for r in all_results if r['is_complete'])
    incomplete = sum(1 for r in all_results if not r['is_complete'] and r['summary']['call_type'] != 'ERROR')

    print(f"Total Processed  : {total}")
    print(f"GOOD Calls       : {good}")
    print(f"BAD Calls        : {bad}")
    print(f"ERROR Calls      : {errors}")
    print(f"Complete (64 var): {complete}")
    print(f"Incomplete       : {incomplete}")

    if errors > 0:
        print(f"\n⚠ ERROR Calls (could not be fixed after {RETRY_ROUNDS} retry rounds):")
        for r in all_results:
            if r['summary']['call_type'] == 'ERROR':
                print(f"  - Call {r['index']}: {r.get('error', 'Unknown error')}")

    if incomplete > 0:
        print(f"\n⚠ Incomplete Calls (fewer than {EXPECTED_VARIABLES} variables):")
        for r in all_results:
            if not r['is_complete'] and r['summary']['call_type'] != 'ERROR':
                print(f"  - Call {r['index']}: {r['summary']['total_possible']} variables extracted")

    scores = [r['summary']['excellent_percentage'] for r in all_results]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0

    print(f"\nAverage Score    : {avg_score}%")
    print("\nAll calls processed successfully!")
