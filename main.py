import os
import time
import requests
import google.generativeai as genai
from dotenv import load_dotenv  
from tabulate import tabulate 
from old_prompts import (
    CSAT_SCORING_PROMPT, 
    COMPARISON_PROMPT, 
    TRANSCRIPTION_PROMPT
)

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

COMPARISON_LOG_FILE = "call_comparisons.txt"

def download_audio(url, suffix):
    temp_path = f"temp_{suffix}_{int(time.time())}.mp3"
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        return temp_path
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None

def upload_to_gemini(file_path):
    audio_file = genai.upload_file(path=file_path)
    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)
    return audio_file

def extract_section(text, start_tag, end_tag=None):
    try:
        start_idx = text.find(start_tag) + len(start_tag)
        if end_tag:
            end_idx = text.find(end_tag)
            return text[start_idx:end_idx].strip()
        return text[start_idx:].strip()
    except:
        return "Section not found."

def format_to_grid_table(raw_table_text, headers):
    lines = raw_table_text.strip().split('\n')
    table_data = []
    for line in lines:
        if '|' in line:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) >= 2: 
                table_data.append(cells)
    
    # Filter out redundant header rows if AI generated them
    table_data = [row for row in table_data if row[0] not in headers[0]]
    
    return tabulate(table_data, headers=headers, tablefmt="grid", maxcolwidths=[25, 35, 35])

def save_comparison_report(good_url, bad_url, good_csat, bad_csat, raw_comparison, t_good, t_bad):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Extract sections
    comp_data = extract_section(raw_comparison, "[TABLE_DATA]", "[POSITIVE_CONTEXT_TABLE]")
    pos_context_data = extract_section(raw_comparison, "[POSITIVE_CONTEXT_TABLE]", "[MISSING_ELEMENTS]")
    missing = extract_section(raw_comparison, "[MISSING_ELEMENTS]", "[WINNING_PHRASES]")
    winning = extract_section(raw_comparison, "[WINNING_PHRASES]")

    # Format Tables
    comp_headers = ["Evaluation Variable", "GOOD CALL (File 1)", "BAD CALL (File 2)"]
    pos_headers = ["Context Variable", "GOOD CALL (Evidence/Freq)", "BAD CALL (Evidence/Freq)"]
    
    comparison_table = format_to_grid_table(comp_data, comp_headers)
    pos_context_table = format_to_grid_table(pos_context_data, pos_headers)

    report = f"""
====================================================================================================
COMPARISON REPORT: {timestamp}
GOOD URL: {good_url}
BAD URL:  {bad_url}
====================================================================================================

--- CSAT SCORES ---
GOOD CALL: {good_csat.strip()}
BAD CALL:  {bad_csat.strip()}

--- COMPARISON ANALYSIS ---
{comparison_table}

--- POSITIVE CONTEXT STRINGS & FREQUENCY ---
{pos_context_table}

--- MISSING ELEMENTS IN BAD CALL ---
{missing}

--- WINNING PHRASES MAPPING ---
{winning}

--- CLEAN TRANSCRIPT: GOOD CALL ---
{t_good}

--- CLEAN TRANSCRIPT: BAD CALL ---
{t_bad}

====================================================================================================
\n"""
    with open(COMPARISON_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(report)
    print(f"[SUCCESS] Detailed report with Positive Context Table saved to {COMPARISON_LOG_FILE}")

def run_dual_analysis(good_url, bad_url):
    path_good = download_audio(good_url, "good")
    path_bad = download_audio(bad_url, "bad")
    
    if not path_good or not path_bad: return

    gem_good = None
    gem_bad = None

    try:
        print("[INFO] Processing Good and Bad calls...")
        gem_good = upload_to_gemini(path_good)
        gem_bad = upload_to_gemini(path_bad)

        # 1. Scoring
        print("[INFO] Scoring calls...")
        csat_good = model.generate_content([CSAT_SCORING_PROMPT, gem_good]).text
        csat_bad = model.generate_content([CSAT_SCORING_PROMPT, gem_bad]).text

        # 2. Transcription
        print("[INFO] Transcribing...")
        t_good = model.generate_content([TRANSCRIPTION_PROMPT, gem_good]).text
        t_bad = model.generate_content([TRANSCRIPTION_PROMPT, gem_bad]).text

        # 3. Deep Comparison (Analysis + Positive Contexts)
        print("[INFO] Performing deep comparison & context extraction...")
        comparison_raw = model.generate_content([
            "File 1 is GOOD, File 2 is BAD.", gem_good, gem_bad, COMPARISON_PROMPT
        ]).text

        save_comparison_report(good_url, bad_url, csat_good, csat_bad, comparison_raw, t_good, t_bad)

    finally:
        for p in [path_good, path_bad]:
            if os.path.exists(p): os.remove(p)
        if gem_good: genai.delete_file(gem_good.name)
        if gem_bad: genai.delete_file(gem_bad.name)

if __name__ == "__main__":
    g_url = input("Enter GOOD Call URL: ").strip()
    b_url = input("Enter BAD Call URL: ").strip()
    run_dual_analysis(g_url, b_url)