"""
PHASE 3: Pattern Mining & Action Logic
Script: pattern_mining.py

Objectives:
1. Load features.csv.
2. Apply heuristic rules to identify "Systemic Failures" vs "Success Patterns".
3. Generate actionable "Execute/Avoid" lists.

Outputs: 
- patterns.json (Machine readable)
- pattern_report.txt (Human readable)
"""

import csv
import json
import os
from collections import defaultdict

FEATURES_CSV = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/features.csv"
PATTERNS_JSON = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/discovered_patterns.json"
REPORT_TXT = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/pattern_report.txt"

def load_features():
    if not os.path.exists(FEATURES_CSV):
        print("features.csv not found.")
        return []
    
    with open(FEATURES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def analyze_patterns(data):
    patterns = {
        "AVOID": [],
        "EXECUTE": [],
        "FOLLOW": []
    }
    
    stats = defaultdict(int)
    total_calls = len(data)
    
    # 1. Compliance (Critical AVOID)
    risk_claims = [d['filename'] for d in data if d.get('has_risk_claim') == 'True']
    if risk_claims:
        patterns["AVOID"].append({
            "code": "AVOID-002",
            "name": "Regulatory Violation: No Risk Claims",
            "frequency": f"{len(risk_claims)}/{total_calls}",
            "evidence": risk_claims,
            "action": "Immediate prompt override to ban 'guaranteed/no risk' terms."
        })

    oath_usage = [d['filename'] for d in data if d.get('has_oath_manipulation') == 'True']
    if len(oath_usage) > 0.3 * total_calls: # High frequnecy
        patterns["AVOID"].append({
            "code": "AVOID-005",
            "name": "Religious Manipulation (Oaths)",
            "frequency": f"{len(oath_usage)}/{total_calls}",
            "evidence": oath_usage[:5], # Sample
            "action": "Remove 'Wallah/Swear' from objection handling response bank."
        })

    # 2. Methodology (EXECUTE Gaps)
    # Check for "Lecturing" (Low questions + Low SPIN)
    lecturing = [d['filename'] for d in data if float(d.get('agent_question_ratio', 0)) < 0.2]
    if len(lecturing) > 0.5 * total_calls:
        patterns["EXECUTE"].append({
            "code": "EXEC-002",
            "name": "Force Socratic Dialogue",
            "reason": "50%+ of calls have <20% agent questions (Lecturing Mode).",
            "action": "Enforce 1 question per turn constraint in Prompt Section Zero."
        })

    # Check for SPIN utilization
    low_implication = [d['filename'] for d in data if float(d.get('agent_spin_implication_density', 0)) < 0.05]
    if len(low_implication) > 0.7 * total_calls:
        patterns["EXECUTE"].append({
            "code": "EXEC-001",
            "name": "Inject SPIN Implications",
            "reason": "70%+ of calls miss 'Implication' questions (Cost of Inaction).",
            "action": "Add specific 'Implication' examples to Response Bank."
        })

    # 3. Cultural (FOLLOW / Tuning)
    kinship_users = [d['filename'] for d in data if float(d.get('total_kinship_density', 0)) > 0.2]
    if len(kinship_users) < 0.2 * total_calls:
         patterns["EXECUTE"].append({
            "code": "EXEC-003",
            "name": "Boost Warmth/Kinship",
            "reason": "Kinship terms (Ya 3ami/Habibi) used in <20% of calls (Low Warmth).",
            "action": "Inject 'Gulf Warmth' markers into greeting and closing."
        })

    return patterns

def save_outputs(patterns):
    # JSON
    with open(PATTERNS_JSON, 'w', encoding='utf-8') as f:
        json.dump(patterns, f, indent=2)
        
    # Text Report
    with open(REPORT_TXT, 'w', encoding='utf-8') as f:
        f.write("=== SOTA PATTERN MINING REPORT ===\n\n")
        
        f.write("🚨 CRITICAL AVOID ACTIONS:\n")
        for p in patterns["AVOID"]:
            f.write(f"- [{p['code']}] {p['name']} ({p['frequency']})\n")
            f.write(f"  Action: {p['action']}\n\n")
            
        f.write("✅ STRATEGIC EXECUTE ACTIONS:\n")
        for p in patterns["EXECUTE"]:
            f.write(f"- [{p['code']}] {p['name']}\n")
            f.write(f"  Reason: {p['reason']}\n")
            f.write(f"  Action: {p['action']}\n\n")

def main():
    data = load_features()
    if not data: return
    
    print(f"Mining patterns from {len(data)} records...")
    patterns = analyze_patterns(data)
    
    save_outputs(patterns)
    print(f"Patterns saved to {PATTERNS_JSON}")
    print(f"Report report saved to {REPORT_TXT}")

if __name__ == "__main__":
    main()
