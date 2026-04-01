import re

stop_words = {
    "the", "is", "and", "in", "to", "of", "for", "with",
    "on", "a", "an", "by", "as", "at", "from"
}

skill_aliases = {
    "machine_learning": ["ml"],
    "javascript": ["js"],
    "node": ["nodejs"],
    "sql": ["mysql", "postgresql", "database"],
    "api": ["apis"],
    "react": ["reactjs", "react.js"],
    "python": ["python3", "py", "python_programming"]
}

multi_word_skills = [
    "machine learning",
    "data analysis",
    "deep learning"
]

def clean_text(text):
    text = text.lower()

    for main_skill, aliases in skill_aliases.items():
        for alias in aliases:
            pattern = r'\b' + re.escape(alias) + r'\b'
            text = re.sub(pattern, main_skill, text)

    for phrase in multi_word_skills:
        pattern = r'\b' + re.escape(phrase) + r'\b'
        text = re.sub(pattern, phrase.replace(" ", "_"), text)

    text = re.sub(r'[^\w\s]', ' ', text)

    words = text.split()
    words = [word for word in words if word not in stop_words]

    return " ".join(words)