"""Lokale Stimmungsbewertung mit FinBERT (ProsusAI/finbert, CPU, kein Token)."""
import threading

MODEL_ID = "ProsusAI/finbert"
LABELS_DE = {"positive": "positiv", "neutral": "neutral", "negative": "negativ"}

_pipe = None
_lock = threading.Lock()


def _pipeline():
    global _pipe
    with _lock:
        if _pipe is None:
            from transformers import pipeline
            _pipe = pipeline("text-classification", model=MODEL_ID, top_k=None, device=-1)
    return _pipe


def score(texts):
    """Gibt je Text {label, label_de, confidence, probs} zurück."""
    if not texts:
        return []
    results = _pipeline()(list(texts), truncation=True, batch_size=16)
    out = []
    for res in results:
        probs = {r["label"].lower(): float(r["score"]) for r in res}
        label = max(probs, key=probs.get)
        out.append({"label": label, "label_de": LABELS_DE[label],
                    "confidence": probs[label], "probs": probs})
    return out


def aggregate(items):
    """Durchschnittliche Stimmung: Mittelwert von P(positiv) - P(negativ) über alle Schlagzeilen."""
    scored = [i["sentiment"] for i in items if i.get("sentiment")]
    if not scored:
        return None
    net = sum(s["probs"]["positive"] - s["probs"]["negative"] for s in scored) / len(scored)
    counts = {k: sum(1 for s in scored if s["label"] == k) for k in LABELS_DE}
    label = "positive" if net > 0.15 else "negative" if net < -0.15 else "neutral"
    return {"net_score": net, "label": label, "label_de": LABELS_DE[label],
            "counts": counts, "n": len(scored)}
