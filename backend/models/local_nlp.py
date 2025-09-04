import re

# Very light-weight local NLP (no NLTK). Regex tokenization + custom stopwords.
# You can expand stopwords and synonyms as needed.

STOPWORDS = {
    "the","is","am","are","was","were","be","been","being","a","an","and","or","but",
    "of","to","from","in","on","at","by","for","with","as","that","this","these","those",
    "it","its","i","you","he","she","we","they","me","my","your","his","her","our","their",
    "do","does","did","doing","done","not","no","so","very","too","just"
}

# Minimal Hindi → English glossary (extend over time)
HI_EN_GLOSS = {
    "namaste":"hello","namaskar":"hello","shukriya":"thank you","dhanyavaad":"thank you",
    "kaise":"how","kya":"what","kyon":"why","kab":"when","kahan":"where","achha":"good",
    "bura":"bad","haan":"yes","nahi":"no","pani":"water","khana":"eat","chalo":"go",
    "ghar":"home","computer":"computer","tv":"television","dhanyavad":"thank you",
    "main":"i","tum":"you","aap":"you"
}

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str):
    text = normalize_text(text)
    tokens = text.split()
    return tokens

def filter_keywords(tokens):
    return [t for t in tokens if t not in STOPWORDS]

def hi_to_en_glossary(text: str) -> str:
    # Extremely simple word-level mapping for demo; replace with real translator later.
    toks = tokenize(text)
    mapped = [HI_EN_GLOSS.get(t, t) for t in toks]
    return " ".join(mapped)
