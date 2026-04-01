import os
from utils.parser import extract_text_from_pdf
from utils.cleaner import clean_text
from utils.scorer import compute_scores, generate_feedback , generate_top_improvements
from utils.roadmap import roadmap

resume_folder = "data/"

job_folder = "jobs/"

job_descriptions = {}

for file in os.listdir(job_folder):
    if file.endswith(".txt"):
        with open(os.path.join(job_folder, file), "r") as f:
            job_descriptions[file] = f.read()

with open("skills.txt", "r") as f:
    skills_list = set(line.strip() for line in f)

results = []

for job_name, job_desc in job_descriptions.items():
    print(f"\n========== JOB: {job_name} ==========")

    job_clean = clean_text(job_desc)
    job_words = job_clean.split()

    job_skills = set() 
    for skill in skills_list:
      if skill in job_words:
        job_skills.add(skill)

    for file in os.listdir(resume_folder):
        if file.endswith(".pdf"):
            path = os.path.join(resume_folder, file)

            resume_text = extract_text_from_pdf(path)
            if not resume_text.strip():
                continue

            result = compute_scores(job_clean, resume_text, job_skills, skills_list)

            feedback = generate_feedback(
            result["explanations"],
            result["skill_evidence"],
            job_skills
           )
            
            top_improvements = generate_top_improvements(result["explanations"])

            results.append({
            "job": job_name,
            "name": file,
            "feedback": feedback, 
            "top_improvements": top_improvements,  
            **result
           })

from collections import defaultdict

job_results = defaultdict(list)

for r in results:
    job_results[r["job"]].append(r)

for job, res_list in job_results.items():
    print(f"\n========== JOB: {job} ==========")

    res_list.sort(key=lambda x: x['final_score'], reverse=True)

    for i, r in enumerate(res_list):
        print(f"\nRank {i+1}: {r['name']}")

        print(f"Final Score: {round(r['final_score']*100, 2)}% "
              f"(Keyword: {round(r['weighted_score']*100, 2)}%, "
              f"Semantic: {round(r['semantic_score']*100, 2)}%)")

        print("\nMatched Skills:")
        for s in r["matched"]:
            print("-", s.replace("_", " ").title())

        print("\nMissing Skills:")
        for s in r["missing"]:
            print("-", s.replace("_", " ").title())

        print("\nFeedback:")
        for f in r.get("feedback", []):
            print("-", f)

        print("\nTop Improvements:")
        for t in r.get("top_improvements", []):
            print("-", t)