import os
import time
import requests
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor
from prompts import (
    CSAT_SCORING_PROMPT,
    TRANSCRIPTION_PROMPT,
    EXTRACT_CONTEXT_PROMPT,
    FINAL_SYNTHESIS_PROMPT
)

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

REPORT_FILE = "master_comparison_report.txt"
TRANSCRIPT_FILE = "transcripts_log.txt"
INPUT_SHEET = "calls.xlsx"


def clean_local_file(path):
    if path and os.path.exists(path):
        os.remove(path)


def process_single_call(url, label):
    if not url or pd.isna(url):
        return None

    temp_path = f"temp_{label}_{int(time.time()*1000)}.mp3"

    try:
        r = requests.get(url, timeout=30)
        with open(temp_path, "wb") as f:
            f.write(r.content)

        gem_file = genai.upload_file(path=temp_path)
        while gem_file.state.name == "PROCESSING":
            time.sleep(1)

        transcript = model.generate_content(
            [TRANSCRIPTION_PROMPT, gem_file]
        ).text

        csat = model.generate_content(
            [CSAT_SCORING_PROMPT, gem_file]
        ).text

        context = model.generate_content(
            [EXTRACT_CONTEXT_PROMPT, gem_file]
        ).text

        genai.delete_file(gem_file.name)
        clean_local_file(temp_path)

        return {
            "url": url,
            "transcript": transcript,
            "csat": csat,
            "context": context
        }

    except Exception as e:
        print(f"Error processing {url}: {e}")
        clean_local_file(temp_path)
        return None


def format_table(raw_text, headers):
    rows = []
    for line in raw_text.split("\n"):
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= len(headers):
                rows.append(parts[:len(headers)])

    rows = [r for r in rows if r[0] not in headers]
    return tabulate(rows, headers=headers, tablefmt="grid")


def extract_section(text, start, end=None):
    try:
        s = text.index(start) + len(start)
        e = text.index(end) if end else len(text)
        return text[s:e].strip()
    except ValueError:
        return ""


def run_aggregate_analysis():
    df = pd.read_excel(INPUT_SHEET)
    good_urls = df["good_url"].dropna().tolist()
    bad_urls = df["bad_url"].dropna().tolist()

    print(f"[INFO] Processing {len(good_urls)} GOOD and {len(bad_urls)} BAD calls")

    with ThreadPoolExecutor(max_workers=3) as executor:
        good_results = list(
            filter(None, executor.map(lambda u: process_single_call(u, "good"), good_urls))
        )
        bad_results = list(
            filter(None, executor.map(lambda u: process_single_call(u, "bad"), bad_urls))
        )

    # ---- SAVE TRANSCRIPTS SEPARATELY ----
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as tf:
        tf.write("=== TRANSCRIPTS LOG ===\n\n")
        for r in good_results + bad_results:
            tf.write(f"URL: {r['url']}\n")
            tf.write(r["transcript"])
            tf.write("\n" + "-" * 60 + "\n")

    # ---- AGGREGATE INPUT FOR LLM ----
    good_block = "\n".join([
        f"""
CALL TYPE: GOOD AGENT
CSAT:
{r['csat']}
CONTEXT:
{r['context']}
"""
        for r in good_results
    ])

    bad_block = "\n".join([
        f"""
CALL TYPE: BAD AGENT
CSAT:
{r['csat']}
CONTEXT:
{r['context']}
"""
        for r in bad_results
    ])

    master_input = f"""
GOOD AGENT CALLS (MULTIPLE):
{good_block}

BAD AGENT CALLS (MULTIPLE):
{bad_block}
"""

    print("[INFO] Generating aggregate comparison report...")

    response = model.generate_content(
        [master_input, FINAL_SYNTHESIS_PROMPT]
    ).text

    csat_section = extract_section(response, "[CSAT_SUMMARY]", "[TABLE_DATA]")
    table_raw = extract_section(response, "[TABLE_DATA]", "[POSITIVE_CONTEXT_TABLE]")
    pos_raw = extract_section(response, "[POSITIVE_CONTEXT_TABLE]", "[MISSING_ELEMENTS]")
    missing = extract_section(response, "[MISSING_ELEMENTS]", "[WINNING_PHRASES]")
    winning = extract_section(response, "[WINNING_PHRASES]")

    report = f"""
====================================================================================
MASTER AGENT COMPARISON REPORT
====================================================================================

--- AGGREGATED CSAT SUMMARY ---
{csat_section}

--- COMPARISON ANALYSIS ---
{format_table(table_raw, ["Evaluation Variable", "GOOD AGENT", "BAD AGENT"])}

--- POSITIVE CONTEXT STRINGS & FREQUENCY ---
{format_table(pos_raw, ["Context Variable", "GOOD AGENT", "BAD AGENT"])}

--- MISSING ELEMENTS IN BAD AGENT ---
{missing}

--- WINNING PHRASES MAPPING ---
{winning}

====================================================================================
"""

    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(report)

    print("[SUCCESS] Aggregate report and transcripts generated.")


if __name__ == "__main__":
    run_aggregate_analysis()
