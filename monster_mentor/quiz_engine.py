import random


def grade_quiz(quiz, answers):
    """answers: list of chosen option indexes (None if skipped)."""
    results = [answers[i] == item["answer"] for i, item in enumerate(quiz)]
    score = sum(results)
    total = len(quiz)
    return {"score": score, "total": total, "results": results,
            "passed": total > 0 and score / total >= 0.6}


def shuffle_options(item, rng=random):
    """Return a copy of a question with options shuffled and answer index updated."""
    order = list(range(len(item["options"])))
    rng.shuffle(order)
    new = dict(item)
    new["options"] = [item["options"][i] for i in order]
    new["answer"] = order.index(item["answer"])
    return new
