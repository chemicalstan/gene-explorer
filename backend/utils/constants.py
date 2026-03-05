# Supported cancer types — must match cancer_indication values in gene_dataset.csv
CANCER_TYPES = [
    "lung", "breast", "prostate", "gastric",
    "glioblastoma", "colorectal", "melanoma",
    "ovarian", "pancreatic", "renal",
]

# Groq
GROQ_MODEL="llama-3.3-70b-versatile"
GROQ_MODEL_MAX_TOKEN=1024
GROQ_MODEL_TEMPERATURE=0.2

# Agent
MAX_ITERATIONS = 5
