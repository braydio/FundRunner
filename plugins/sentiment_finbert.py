# Corrected FinBERT sentiment plugin using ProsusAI/finbert

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

# Load model + tokenizer once
_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

# The model output is: [positive, negative, neutral]
_LABELS = ["positive", "negative", "neutral"]


def analyze_sentiment(text):
    """
    Analyze financial sentiment from input text using FinBERT.

    Returns a dict like:
    {'positive': 0.82, 'negative': 0.04, 'neutral': 0.14}
    """
    inputs = _tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = _model(**inputs).logits
        probs = F.softmax(logits, dim=1)[0].tolist()

    return {label: float(prob) for label, prob in zip(_LABELS, probs)}
