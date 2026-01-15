import os
import time
import requests
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompts import (
    CSAT_SCORING_PROMPT,
    TRANSCRIPTION_PROMPT,
    EXTRACT_CONTEXT_PROMPT,
    FINAL_SYNTHESIS_PROMPT
)

# -------------------- CONFIG --------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

INPUT_SHEET = "calls.xlsx"
OUTPUT_FILE = "call_level_results.txt"
TRANSCRIPT_FILE = "transcripts.txt"
MAX_WORKERS = 3
# ------------------------------------------------


def safe_delete(path):
    if path and os.path.exists(path):
        os.remove(path)


def process_single_call(index, url, total):
    print(f"[START] ({index}/{total}) Processing call")

    temp_path = f"temp_call_{index}_{int(time.time() * 1000)}.mp3"

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()

        with open(temp_path, "wb") as f:
            f.write(r.content)

        gem_file = genai.upload_file(path=temp_path)

        while gem_file.state.name == "PROCESSING":
            time.sleep(1)

        transcript = model.generate_content(
            [TRANSCRIPTION_PROMPT, gem_file]
        ).text.strip()

        variable_analysis = model.generate_content(
            [EXTRACT_CONTEXT_PROMPT, gem_file]
        ).text.strip()

        csat = model.generate_content(
            [CSAT_SCORING_PROMPT, gem_file]
        ).text.strip()

        genai.delete_file(gem_file.name)
        safe_delete(temp_path)

        print(f"[SUCCESS] ({index}/{total}) Completed")

        return {
            "index": index,
            "url": url,
            "transcript": transcript,
            "analysis": variable_analysis,
            "csat": csat
        }

    except Exception as e:
        safe_delete(temp_path)
        print(f"[FAILED] ({index}/{total}) Error: {e}")
        return None


def main():
    df = pd.read_excel(INPUT_SHEET)

    if "recording_url" not in df.columns:
        raise ValueError("Excel must contain 'recording_url' column")

    urls = df["recording_url"].dropna().tolist()
    total_files = len(urls)

    print("=" * 80)
    print(f"[INFO] Total recordings to process : {total_files}")
    print(f"[INFO] Max parallel workers       : {MAX_WORKERS}")
    print("=" * 80)

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_single_call, idx + 1, url, total_files): idx + 1
            for idx, url in enumerate(urls)
        }

        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    print("=" * 80)
    print(f"[INFO] Successfully processed {len(results)} / {total_files} calls")
    print("=" * 80)

    # ---------------- SAVE TRANSCRIPTS ----------------
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as tf:
        for r in sorted(results, key=lambda x: x["index"]):
            tf.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            tf.write(f"Call Index: {r['index']}\n")
            tf.write(f"Call URL  : {r['url']}\n\n")
            tf.write(r["transcript"])
            tf.write("\n" + "-" * 80 + "\n")

    # ---------------- SAVE CALL RESULTS ----------------
    with open(OUTPUT_FILE, "a", encoding="utf-8") as of:
        for r in sorted(results, key=lambda x: x["index"]):
            of.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            of.write(f"Call Index: {r['index']}\n")
            of.write(f"Call URL  : {r['url']}\n\n")
            of.write(r["csat"] + "\n\n")
            of.write("VARIABLE ANALYSIS\n")
            of.write(r["analysis"])
            of.write("\n" + "=" * 80 + "\n")

    print("[DONE] All outputs generated successfully.")


if __name__ == "__main__":
    main()
    