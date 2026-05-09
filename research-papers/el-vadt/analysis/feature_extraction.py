"""
PHASE 2: SOTA Feature Engineering (Dependency Free)
Script: feature_extraction.py

Objectives:
1. Extract Turn-Level Features (Duration, WPM, Questions).
2. Extract Sales Methodology Features (SPIN patterns).
3. Extract Compliance Features (Risk claims, Pressure).
4. Extract Cultural Features (Kinship density).

Output: features.csv
"""

import os
import glob
import re
import csv
import math
from collections import defaultdict

TRANSCRIPT_DIR = "/home/shovalbe/projects/el-vadt/seekapa-sales-conversations-transcripts"
OUTPUT_CSV = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/features.csv"

# --- Feature Definitions ---

# SPIN Selling Patterns (Arabic/English)
SPIN_PATTERNS = {
    "situation": [r"(current|حاليا)", r"(status|وضع)", r"(platform|منصة)", r"(using|تستخدم)"],
    "problem": [r"(problem|مشكلة)", r"(issue|قضية)", r"(difficult|صعب)", r"(slow|بطيء)", r"(risk|مخاطرة)"],
    "implication": [r"(cost|يكلف)", r"(loss|خسارة)", r"(impact|تأثير)", r"(consequence|عاقبة)", r"(money|فلوس)"],
    "need_payoff": [r"(help|مساعدة)", r"(solution|حل)", r"(benefit|فائدة)", r"(save|توفير)"]
}

# Compliance Flags
COMPLIANCE_PATTERNS = {
    "risk_claim": [r"(no risk|لا يوجد خطر|مضمون|guarantee)"],
    "pressure_tactic": [r"(now|limited|expires|terminates|ينتهي|بسرعة)"],
    "oath_manipulation": [r"(wallah|swear to god|والله|أقسم بالله)"]
}

# Cultural Markers
CULTURAL_PATTERNS = {
    "kinship": [r"(brother|sister|akhi|ukhti|habibi|ya 3ami|يا عمي|حبيبي|يا روحي)"],
    "religious": [r"(inshallah|mashallah|alhamdulillah|إن شاء الله|الحمد لله)"]
}

def analyze_turn(text):
    text_lower = text.lower()
    features = {
        "word_count": len(text.split()),
        "char_count": len(text),
        "is_question": "?" in text or "؟" in text,
        "is_imperative": bool(re.search(r"(!|must|have to|لازم|يجب)", text_lower)),
    }
    
    # SPIN
    for stage, regexes in SPIN_PATTERNS.items():
        features[f"spin_{stage}"] = sum(1 for r in regexes if re.search(r, text_lower)) > 0
        
    # Compliance
    for flag, regexes in COMPLIANCE_PATTERNS.items():
        features[f"compliance_{flag}"] = sum(1 for r in regexes if re.search(r, text_lower)) > 0
        
    # Cultural
    for marker, regexes in CULTURAL_PATTERNS.items():
        features[f"cultural_{marker}"] = sum(1 for r in regexes if re.search(r, text_lower)) > 0
        
    return features

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse Turns (Assuming [Speaker]: format from Phase 0 findings)
        # Note: Phase 0 fixed 'נציג' to 'Agent', but we handle both just in case or raw files
        raw_turns = re.split(r'(\[(?:Agent|Customer|009\d+|נציג|لقوح).*?\])', content)
        
        turns_data = []
        current_speaker = "Unknown"
        
        for i in range(1, len(raw_turns), 2):
            header = raw_turns[i]
            text = raw_turns[i+1].strip()
            if not text: continue
            
            # Identify Speaker
            if "Agent" in header or "נציג" in header:
                speaker = "Agent"
            else:
                speaker = "Customer"
                
            features = analyze_turn(text)
            features["speaker"] = speaker
            turns_data.append(features)
            
        if not turns_data:
            return None

        # Aggregation per Transcript
        agg = defaultdict(float)
        agg["filename"] = os.path.basename(filepath)
        agg["turn_count"] = len(turns_data)
        
        agent_turns = [t for t in turns_data if t["speaker"] == "Agent"]
        cust_turns = [t for t in turns_data if t["speaker"] == "Customer"]
        
        # Ratios
        agg["agent_turn_ratio"] = len(agent_turns) / len(turns_data) if turns_data else 0
        
        # SPIN Density (Agent Only)
        for stage in SPIN_PATTERNS:
            count = sum(1 for t in agent_turns if t[f"spin_{stage}"])
            agg[f"agent_spin_{stage}_density"] = count / len(agent_turns) if agent_turns else 0
            
        # Compliance Risk (Agent Only - Critical)
        for flag in COMPLIANCE_PATTERNS:
            count = sum(1 for t in agent_turns if t[f"compliance_{flag}"])
            agg[f"agent_{flag}_count"] = count
            agg[f"has_{flag}"] = count > 0
            
        # Cultural Density (Both)
        for marker in CULTURAL_PATTERNS:
            count = sum(1 for t in turns_data if t[f"cultural_{marker}"])
            agg[f"total_{marker}_density"] = count / len(turns_data) if turns_data else 0

        # Dynamics
        # Question Ratio
        agent_qs = sum(1 for t in agent_turns if t["is_question"])
        agg["agent_question_ratio"] = agent_qs / len(agent_turns) if agent_turns else 0
        
        return agg
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return None

def main():
    files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))
    results = []
    print(f"Extracting features from {len(files)} transcripts...")
    
    for f in files:
        res = process_file(f)
        if res:
            results.append(res)
            
    if not results:
        print("No features extracted.")
        return

    # Write CSV
    headers = list(results[0].keys())
    # Ensure specific order if desired, but default dict keys is okay for now
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Features saved to {OUTPUT_CSV}")
    print("-" * 30)
    print(f"Analyzed {len(results)} files.")
    
    # Quick Stat check
    risk_count = sum(1 for r in results if r["has_risk_claim"])
    print(f"Transcripts with 'No Risk' claims: {risk_count}")

if __name__ == "__main__":
    main()
