"""
PHASE 0: Data Quality & Ground Truth Audit
Script: quality_check.py

Objectives:
1. Scan 100 transcripts for basic metadata (Duration, Turns).
2. Fix known label issues (נציג -> Agent).
3. Generate report: pass/fail per transcript.
"""

import os
import glob
import re
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TRANSCRIPT_DIR = "/home/shovalbe/projects/el-vadt/seekapa-sales-conversations-transcripts"
REPORT_PATH = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/data_quality_report.json"

def detect_language(text):
    # Simple heuristic
    if re.search(r'[ا-ي]', text): return 'ar'
    if re.search(r'[áéíóúñ]', text, re.I): return 'es'
    if re.search(r'[ãõç]', text, re.I): return 'pt'
    return 'en'

def audit_transcript(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            
        # Fix Hebrew Labels (Legacy Issue)
        text = raw_text.replace('נציג', 'Agent').replace('לקוח', 'Customer')
        
        # Turn Analysis
        turns = re.split(r'(\[(?:Agent|Customer|009\d+).*?\])', text)
        valid_turns = [t.strip() for t in turns if len(t.strip()) > 2]
        turn_count = len(valid_turns) // 2 # Approx
        
        # Metadata
        checks = {
            "has_speaker_labels": bool(re.search(r'(Agent|Customer|009\d+)', text)),
            "min_turns": turn_count >= 4,
            "language": detect_language(text),
            "file_size": os.path.getsize(filepath)
        }
        
        return {
            "filename": os.path.basename(filepath),
            "valid": all([checks['has_speaker_labels'], checks['min_turns']]),
            "checks": checks,
            "turn_count": turn_count
        }
        
    except Exception as e:
        return {"filename": os.path.basename(filepath), "valid": False, "error": str(e)}

def main():
    files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))
    results = [audit_transcript(f) for f in files]
    
    # Stats
    pass_rate = len([r for r in results if r['valid']]) / len(results) * 100
    logging.info(f"Analyzed {len(results)} files. Rate: {pass_rate:.1f}%")
    
    # Save Report
    with open(REPORT_PATH, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"Report saved to {REPORT_PATH}")

if __name__ == "__main__":
    main()
