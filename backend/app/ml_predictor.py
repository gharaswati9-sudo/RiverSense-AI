import os
import pickle
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ── Load model once when server starts ──
# Load from the unzipped model folder
MODEL_PATH = "./dnabert_finetuned"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True
)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True
)

# Load label mapping
with open(f"{MODEL_PATH}/label_mapping.pkl", "rb") as f:
    label_mapping = pickle.load(f)

LABEL_NAMES = {0: "Clean", 1: "Polluted"}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model  = model.to(device)
model.eval()

# ── Ecological map for feature extraction ──
ECOLOGICAL_MAP = {
    "Pseudomonas"        : {"group": "heavy_pollution",     "weight": 3.0},
    "Pseudomonadota"     : {"group": "heavy_pollution",     "weight": 2.0},
    "Proteobacteria"     : {"group": "heavy_pollution",     "weight": 2.0},
    "Acinetobacter"      : {"group": "heavy_pollution",     "weight": 3.0},
    "Alcaligenes"        : {"group": "heavy_pollution",     "weight": 3.0},
    "Shewanella"         : {"group": "heavy_pollution",     "weight": 3.0},
    "Alphaproteobacteria": {"group": "mild_pollution",      "weight": 1.5},
    "Rhizobium"          : {"group": "agricultural_runoff", "weight": 1.5},
    "Rhizobiaceae"       : {"group": "agricultural_runoff", "weight": 1.5},
    "Neorhizobium"       : {"group": "agricultural_runoff", "weight": 1.0},
    "Hyphomicrobiales"   : {"group": "nutrient_pollution",  "weight": 1.5},
    "Bacillus"           : {"group": "mild_pollution",      "weight": 1.0},
    "Lactobacillus"      : {"group": "clean_indicator",     "weight": -1.0},
    "Nitrosomonas"       : {"group": "clean_indicator",     "weight": -1.0},
    "Caulobacter"        : {"group": "clean_indicator",     "weight": -1.0},
}

def parse_kraken2_report(report_path):
    """Reads Kraken2 report and returns feature dictionary"""
    rows = []
    
    # Only try to read if the file physically exists
    if os.path.exists(report_path):
        with open(report_path) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 6:
                    continue
                try:
                    rows.append({
                        "percent": float(parts[0].strip()),
                        "reads"  : int(parts[1].strip()),
                        "rank"   : parts[3].strip(),
                        "taxid"  : parts[4].strip(),
                        "name"   : parts[5].strip()
                    })
                except:
                    continue

    # 🛡️ FIX 1 & 2: Convert rows to DataFrame, or build a safe skeleton structure if file parsing failed
    if not rows:
        report_df = pd.DataFrame(columns=["percent", "reads", "rank", "taxid", "name"])
    else:
        report_df = pd.DataFrame(rows)

    features  = {
        "unclassified_percent"    : 0.0,
        "heavy_pollution_score"   : 0.0,
        "mild_pollution_score"    : 0.0,
        "agricultural_score"      : 0.0,
        "clean_indicator_score"   : 0.0,
        "species_diversity"       : 0,
        "dominant_organism"       : "Unknown",
        "total_classified_percent": 0.0
    }

    for _, row in report_df.iterrows():
        name    = row['name']
        percent = row['percent']
        if 'unclassified' in name.lower():
            features['unclassified_percent'] = percent
            continue
        if row['rank'] == 'S':
            features['species_diversity'] += 1
        for organism, info in ECOLOGICAL_MAP.items():
            if organism.lower() in name.lower():
                group  = info['group']
                weight = info['weight']
                if group == 'heavy_pollution':
                    features['heavy_pollution_score']  += percent * weight
                elif group in ['mild_pollution', 'nutrient_pollution']:
                    features['mild_pollution_score']   += percent * weight
                elif group == 'agricultural_runoff':
                    features['agricultural_score']      += percent * weight
                elif group == 'clean_indicator':
                    features['clean_indicator_score']  += percent * weight
                break

    features['total_classified_percent'] = (
        100 - features['unclassified_percent']
    )
    
    # Safely handle extracting dominant organism even if no data exists
    if not report_df.empty:
        classified = report_df[
            ~report_df['name'].str.contains('unclassified', case=False)
        ].sort_values('percent', ascending=False)
        if len(classified) > 0:
            features['dominant_organism'] = classified.iloc[0]['name']

    return features

def calculate_score(features):
    """Calculates 0-100 biodiversity score from features"""
    score = 100.0
    c = features['total_classified_percent']
    if c < 2: score -= 25
    elif c < 5: score -= 15
    elif c < 10: score -= 5
    score -= features['heavy_pollution_score'] * 4
    score -= features['mild_pollution_score']  * 2
    score -= features['agricultural_score']    * 1.5
    score += features['clean_indicator_score'] * 3
    d = features['species_diversity']
    if d < 5: score -= 20
    elif d < 10: score -= 10
    elif d < 20: score -= 5
    score = int(max(0, min(100, score)))

    if score < 30: level = "CRITICAL"
    elif score < 60: level = "WARNING"
    else: level = "HEALTHY"

    sources = []
    if features['heavy_pollution_score'] > 0.3:
        sources.append("Industrial discharge — Pseudomonadota detected")
    if features['agricultural_score'] > 0.2:
        sources.append("Agricultural runoff — Rhizobium detected")
    if features['mild_pollution_score'] > 0.2:
        sources.append("General bacterial pollution detected")
    if not sources:
        sources.append("Low diversity — monitoring recommended")

    return {
        "biodiversity_score" : score,
        "alert_level"        : level,
        "pollution_sources"  : sources,
        "dominant_organism"  : features['dominant_organism'],
        "species_diversity"  : features['species_diversity'],
        "classified_percent" : features['total_classified_percent'],
        "heavy_pollution"    : features['heavy_pollution_score'] > 0.3,
        "agricultural_runoff": features['agricultural_score'] > 0.2,
    }

def dna_to_kmers(sequence, k=6):
    """Converts DNA sequence to k-mer format for DNABERT"""
    kmers = [sequence[i:i+k] for i in range(len(sequence)-k+1)]
    return " ".join(kmers)

def classify_sequence(sequence):
    """Classifies one DNA sequence as Clean or Polluted."""
    kmers  = dna_to_kmers(sequence[:512])
    inputs = tokenizer(
        kmers,
        return_tensors = "pt",
        truncation     = True,
        max_length     = 512,
        padding        = True
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs    = model(**inputs)
        pred_idx   = torch.argmax(outputs.logits, dim=1).item()
        confidence = torch.softmax(
            outputs.logits, dim=1
        ).max().item()

    original_label = label_mapping.get(pred_idx, 1)
    return {
        "label"      : original_label,
        "label_name" : LABEL_NAMES.get(original_label, "Unknown"),
        "confidence" : round(confidence * 100, 1)
    }

def predict_from_report(kraken_report_path, location, lat, lng):
    """MAIN FUNCTION — Called by FastAPI routes"""
    features = parse_kraken2_report(kraken_report_path)
    result   = calculate_score(features)
    result.update({
        "location"  : location,
        "latitude"  : lat,
        "longitude" : lng,
        "status"    : "complete"
    })
    return result