from collections import Counter, defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from utils.cleaner import clean_text
import re

model = SentenceTransformer('all-MiniLM-L6-v2')

def split_into_sentences(text):
    sentences = re.split(r'[.\n]', text)
    return [s.strip() for s in sentences if s.strip()]

def extract_skills_from_sentence(sentence, skills_list):
    found_skills = set()
    for skill in skills_list:
        if skill in sentence:
            found_skills.add(skill)
    return found_skills

def is_skill_list(sentence):
    keywords = ["proficient", "skills", "tools", "technologies"]
    return any(k in sentence.lower() for k in keywords)

def generate_top_improvements(explanations):
    items = []

    for skill, data in explanations.items():
        if data["status"] != "strong":
            score = 0

            if data["importance"] == "high":
                score += 2
            elif data["importance"] == "medium":
                score += 1

            if data["status"] == "missing":
                score += 2
            elif data["status"] == "weak":
                score += 1

            items.append((score, skill))

    items.sort(key=lambda x: (x[0], x[1]), reverse=True)

    return [s.replace("_", " ").title() for _, s in items[:3]]

def compute_scores(job_clean, resume_text, job_skills, skills_list):
    job_words = job_clean.split()
    job_skill_counts = Counter(job_words)

    priority_weight = {}
    for skill in job_skills:
        priority_weight[skill] = job_skill_counts.get(skill, 1) + 1

    sentences = [
        s for s in split_into_sentences(resume_text)
        if 5 <= len(s.split()) <= 30
    ]

    skill_map = defaultdict(list)

    for sentence in sentences:
        clean_sentence = clean_text(sentence)
        skills = extract_skills_from_sentence(clean_sentence, skills_list)
        for skill in skills:
            skill_map[skill].append(sentence)

    total = 0
    score = 0
    skill_strength = {}

    for skill in job_skills:
        weight = priority_weight.get(skill, 1)
        total += weight

        if skill not in skill_map:
            skill_strength[skill] = 0.0
            continue

        best_score = 0

        filtered_sentences = [s for s in skill_map[skill] if not is_skill_list(s)]
        if not filtered_sentences:
            filtered_sentences = skill_map[skill]

        strong_words = ["built", "developed", "designed", "implemented", "created"]

        for sentence in filtered_sentences:
            emb1 = model.encode([ f"{skill} development experience", f"working with {skill}", f"{skill} project implementation"])
            emb2 = model.encode([sentence])
            sim = max(cosine_similarity(emb1, emb2).flatten())

            if any(word in sentence.lower() for word in strong_words):
                sim += 0.08

            if is_skill_list(sentence):
                sim -= 0.05

            if sim > best_score:
                best_score = sim

        best_score = max(0, min(best_score, 1))

        skill_strength[skill] = float(best_score)
        score += weight * best_score

    weighted_score = float(score / total)
    weighted_score = weighted_score ** 0.7

    job_embedding = model.encode([job_clean])
    resume_embedding = model.encode([" ".join(sentences)])

    semantic_score = float(
        (cosine_similarity(job_embedding, resume_embedding)[0][0] + 1) / 2
    )

    final_score = 0.85 * weighted_score + 0.15 * semantic_score

    matched = list(skill_map.keys() & job_skills)
    missing = list(job_skills - skill_map.keys())

    explanations = {}

    for skill in job_skills:
        weight = priority_weight.get(skill, 1)
        count = len(skill_map.get(skill, []))
        strength = skill_strength.get(skill, 0.0)

        if weight >= 3:
            importance = "high"
        elif weight == 2:
            importance = "medium"
        else:
            importance = "low"

        if count == 0:
           status = "missing"

        elif count == 1:
           if strength > 0.5 or any(word in skill_map[skill][0].lower() for word in ["built", "developed", "implemented"]):
             status = "strong"
           else:
             status = "weak"

        else:
         if strength > 0.5:
           status = "strong"
         else:
           status = "weak"


        if status == "missing":
            reason = "Not found in resume"
            suggestion = f"Add {skill.replace('_',' ')} in projects or experience"
        elif status == "weak":
            reason = "Skill present but not strongly demonstrated"
            suggestion = f"Strengthen {skill.replace('_',' ')} with better examples"
        else:
            reason = "Strong evidence found in resume"
            suggestion = "Good"

        explanations[skill] = {
            "status": status,
            "importance": importance,
            "strength": round(strength, 2),
            "reason": reason,
            "suggestion": suggestion
        }

    return {
        "final_score": final_score,
        "weighted_score": weighted_score,
        "semantic_score": semantic_score,
        "matched": matched,
        "missing": missing,
        "skill_evidence": skill_map,
        "skill_strength": skill_strength,
        "priority_weight": {k: int(v) for k, v in priority_weight.items()},
        "explanations": explanations
    }

def generate_feedback(explanations, skill_evidence, job_skills):
    feedback_items = []

    def get_meaningful_sentence(sentences):
        for s in sentences:
            if not s:
                continue
            words = s.split()
            if len(words) < 5:
                continue
            if re.search(r'\S+@\S+\.\S+', s):
                continue
            if re.search(r'\+?\d[\d\-\(\)\s]{8,}\d', s):
                continue
            if any(len(w) > 30 for w in words):
                continue
            if len(s) > 120:
                s = s[:117].strip() + "..."
            else:
                s = s.strip()
            return s
        return None

    for skill in job_skills:
        if skill not in explanations:
            continue

        data = explanations[skill]
        status = data.get("status")
        importance = data.get("importance")

        if importance == "low":
            continue

        priority = 0
        if importance == "high" and status == "missing":
            priority = 5
        elif importance == "high" and status == "weak":
            priority = 4
        elif importance == "medium" and status == "missing":
            priority = 3
        elif importance == "medium" and status == "weak":
            priority = 2
        else:
            continue

        if len(skill) <= 3:
            skill_display = skill.upper()
        else:
            skill_display = skill.replace("_", " ").title()

        message = ""
        if status == "missing":
            if importance == "high":
                message = f"Missing {skill_display}, which is a key requirement for this role."
            else:
                message = f"{skill_display} is missing from your resume."
        elif status == "weak":
            sentences = skill_evidence.get(skill, [])
            example = get_meaningful_sentence(sentences)
            if example:
                message = f"{skill_display} is weak. Example: '{example}' Improve impact by adding measurable results."
            else:
                message = f"{skill_display} is weak. Improve impact by adding measurable results."

        if message:
            feedback_items.append((priority, message))

    feedback_items.sort(key=lambda x: x[0], reverse=True)

    results = []
    seen = set()

    for _, msg in feedback_items:
        if msg not in seen:
            seen.add(msg)
            results.append(msg)
            if len(results) == 3:
                break

    return results