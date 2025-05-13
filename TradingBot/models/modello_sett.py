from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import os
import settings

class SentimentModel:
    def __init__(self, model_name=None, local_path=None):
        self.tokenizer = None
        self.model = None
        model_name = model_name or getattr(
            settings, "SENTIMENT_MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english"
        )
        local_path = local_path or "models/sentiment_model"
        try:
            print(f"[SentimentModel] Loading model: {model_name}")
            if os.path.isdir(local_path):
                self.tokenizer = AutoTokenizer.from_pretrained(local_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(local_path)
                print(f"[SentimentModel] Loaded from local path: {local_path}")
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                os.makedirs(local_path, exist_ok=True)
                self.tokenizer.save_pretrained(local_path)
                self.model.save_pretrained(local_path)
                print(f"[SentimentModel] Downloaded to: {local_path}")
        except Exception as e:
            print(f"[SentimentModel] Failed to load model: {e}")
            raise

    def analyze(self, text: str) -> float:
        try:
            inputs = self.tokenizer(text[:512], return_tensors="pt", truncation=True)
            with torch.no_grad():
                logits = self.model(**inputs).logits
            probs = F.softmax(logits, dim=-1)
            neg, pos = probs[0].tolist()
            return round(pos - neg, 3)
        except Exception as e:
            print(f"[SentimentModel] Error analyzing text: {e}")
            return 0.0
