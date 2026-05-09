"""
PHASE 2.2: SOTA LLM Semantic Extraction (Template)
Script: llm_extraction.py

Instructions:
1. Set your OpenAI API Key in env: export OPENAI_API_KEY='sk-...'
2. Run this script to analyze transcripts for subtle signals (Sarcasm, Indirect Refusals).
"""

import os
import glob
import json
from openai import OpenAI
from tqdm import tqdm

TRANSCRIPT_DIR = "/home/shovalbe/projects/el-vadt/seekapa-sales-conversations-transcripts"
OUTPUT_FILE = "/home/shovalbe/projects/el-vadt/sales-agents/analysis/llm_semantic_features.json"

client = OpenAI()

EXTRACTION_PROMPT = """
You are a senior sales analyst specializing in GCC/LATAM cultural nuances.
Analyze this transcript and output JSON only:

1. **Agent Stance**: (consultative | high_pressure | neutral)
2. **Customer Sentiment Trajectory**: (improving | stable | deteriorating)
3. **Indirect Refusal Detected**: (true/false) - Look for "Inshallah later" or "I will think" used as a soft no.
4. **Sarcasm Detected**: (true/false)
5. **Compliance Violation**: Quote any text promising "No Risk" or "Guaranteed Profit".

Transcript:
{transcript_text}
"""

def analyze_transcript(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()[:10000] # Truncate for token limits
            
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert data scientist."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(transcript_text=text)}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        result = json.loads(response.choices[0].message.content)
        result['filename'] = os.path.basename(filepath)
        return result
        
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")
        return

    files = glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))[:10] # Sample 10 for cost control
    results = []
    
    print(f"Analyzing {len(files)} transcripts with GPT-4o...")
    for f in tqdm(files):
        res = analyze_transcript(f)
        if res:
            results.append(res)
            
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"Saved semantic features to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
