"""
PHASE 1: EDA - Dark Pattern Discovery (Dependency Free)
Script: eda_dark_patterns.py

Objectives:
1. Scan for specific 'Housewife Targeting' keywords ( زوجك, مصروف, debts).
2. Scan for 'Religious Manipulation' keywords ( والله, وحياة ).
3. Scan for 'High Pressure' keywords ( bonus, now, expires ).
"""

import os
import glob
import re
import csv

TRANSCRIPT_DIR = "/home/shovalbe/projects/el-vadt/seekapa-sales-conversations-transcripts"
OUTPUT_CSV = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/dark_patterns_report.csv"

# Keyword Dictionaries (Arabic/English)
DARK_PATTERNS = {
    "Targeting_Vulnerable": [
        r"(housewife|ربت منزل|ربة منزل)", 
        r"(husband|زوجك)", 
        r"(borrow|تسلف|سلف)", 
        r"(debt|دين|قرض)", 
        r"(secret|سر|لا تخبري)"
    ],
    "Religious_Pressure": [
        r"(wallah|والله)", 
        r"(swear|احلف)", 
        r"(god|ربنا|الله)", 
        r"(halal|حلال)"
    ],
    "High_Pressure": [
        r"(now|الآن|الحين)", 
        r"(expires|ينتهي)", 
        r"(bonus|بونص|مكافأة)", 
        r"(opportunity|فرصة)"
    ]
}

def scan_transcript(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read().lower()
            
        flags = {}
        for category, regexes in DARK_PATTERNS.items():
            count = 0
            matches = []
            for regex in regexes:
                found = re.findall(regex, text)
                if found:
                    count += len(found)
                    matches.extend(found)
            flags[category] = count
            flags[f"{category}_matches"] = ",".join(list(set([str(m) for m in matches])))
            
        return {"filename": os.path.basename(filepath), **flags}
        
    except Exception as e:
        return {"filename": os.path.basename(filepath), "error": str(e)}

def main():
    files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))
    results = [scan_transcript(f) for f in files]
    
    # Sort results by vulnerability count
    results.sort(key=lambda x: x.get('Targeting_Vulnerable', 0), reverse=True)
    
    # Save to CSV
    keys = results[0].keys() if results else []
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
    
    # Summary
    print(f"Scanned {len(results)} files.")
    print("Top Vulnerability Flags:")
    for row in results[:5]:
        matches = row.get('Targeting_Vulnerable_matches', '')
        if matches:
            print(f"- {row['filename']}: {matches}")

if __name__ == "__main__":
    main()
