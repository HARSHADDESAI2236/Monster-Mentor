def monster_system(monster, lesson):
    return (
        f"You are {monster['name']}, a friendly monster tutor. Personality: {monster['trait']} "
        f"You are teaching the concept '{lesson['title']}' to a student.\n"
        f"Core analogy: {lesson['analogy']}\n"
        f"Reference explanation: {lesson['concept']}\n\n"
        "Rules: explain using your monster analogy first, then give the precise technical meaning. "
        "Be warm, concise (under 150 words unless asked for more), and technically correct. "
        "If you are unsure about a fact, say so instead of guessing."
    )


def quiz_prompt(lesson, n):
    return (
        f"Write {n} NEW multiple-choice questions testing the concept '{lesson['title']}'.\n"
        f"Concept summary: {lesson['concept']}\n"
        "Do not repeat these existing questions: " + "; ".join(q["q"] for q in lesson["quiz"]) + "\n"
        "Return ONLY JSON in this exact shape:\n"
        '{"quiz":[{"q":"...","options":["a","b","c","d"],"answer":0,"why":"one short sentence, may use the monster analogy"}]}\n'
        "Each question has exactly 4 options; answer is the 0-based index of the single correct option."
    )


def explain_mistakes_prompt(lesson, wrong):
    lines = "\n".join(
        f"- Question: {w['q']} | Student chose: {w['picked']} | Correct: {w['correct']}" for w in wrong
    )
    return (
        f"A student studying '{lesson['title']}' got these quiz questions wrong:\n{lines}\n"
        "For each, explain in 1-2 friendly sentences why the chosen answer is wrong and why the correct one is right, "
        "using the monster analogy where it helps."
    )


def lesson_prompt(topic, subject, monster_ids):
    return (
        f"Create a short lesson on '{topic}' (subject area: {subject}) explained with a friendly monster analogy.\n"
        "Return ONLY JSON in this exact shape:\n"
        '{"id":"kebab-case-id","title":"...","monster":"<one of: ' + ", ".join(monster_ids) + '>",'
        '"analogy":"2-3 sentences with the monster","concept":"3-4 sentences, technically accurate",'
        '"quiz":[{"q":"...","options":["a","b","c","d"],"answer":0,"why":"..."}]}\n'
        "Include exactly 2 quiz questions with 4 options each; answer is a 0-based index."
    )
