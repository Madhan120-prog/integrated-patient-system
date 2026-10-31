"""Decision trail: for each note on the chart, who started it, what the AI said,
and what the doctor changed, so "where did this come from?" has a recorded answer.
Logs show what happened and in what order; the doctor's review tick and reason
are what record their judgement."""
import difflib

# How the question reached DocAssist: the doctor's own words, or something the portal offered.
SOURCES = {
    "typed": "wrote the question in their own words",
    "suggestion": "picked one of DocAssist's suggested questions",
    "section": "asked about one chart section",
    "chart": "used a button on the chart",
}
KINDS = {
    "study": "asked DocAssist to analyze a study image",
    "document": "asked DocAssist to read an uploaded file",
    "dicom": "asked DocAssist to analyze a DICOM image",
    "recording": "asked DocAssist about a visit recording",
}


def changes(original: str, final: str):
    """Word-level difference between the AI's text and the saved note, and the share of it that changed."""
    a, b = original.split(), final.split()
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    parts = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            parts.append(["same", " ".join(a[i1:i2])])
            continue
        if i2 > i1:
            parts.append(["removed", " ".join(a[i1:i2])])
        if j2 > j1:
            parts.append(["added", " ".join(b[j1:j2])])
    return parts, 100 - round(matcher.ratio() * 100)


def origin(note: dict) -> str:
    if not note.get("ai"):
        return "Doctor-led"
    return "AI-assisted, doctor edited" if note["ai"]["edited"] else "AI text accepted unchanged"


def trail(note: dict) -> dict:
    """The note's story, step by step, in time order."""
    who, ai = note["author_name"], note.get("ai")
    if not ai:
        steps = [{"at": note["at"], "who": who, "what": f"{who} wrote this note. DocAssist was not used."}]
        return {**note, "origin": origin(note), "steps": steps, "diff": None, "changed_pct": None}
    how = KINDS.get(ai.get("kind")) or SOURCES.get(ai.get("source"), "asked DocAssist (how the question was started was not recorded)")
    diff, pct = changes(ai["original"], note["text"])
    records = ", ".join(f"{r['name']} ({r['date']})" for r in ai["records"]) or "no specific records"
    steps = [
        {"at": ai["asked_at"], "who": who, "what": f"{who} {how}: \"{ai['question']}\""},
        {"at": ai["asked_at"], "who": "DocAssist", "what": f"DocAssist answered using {records}. Model: {ai['model'] or 'not recorded'}."},
        {"at": note["at"], "who": who, "what": (f"{who} changed about {pct}% of the AI's wording" if ai["edited"]
                                                else f"{who} kept the AI's wording unchanged")
                                               + (f". Reason given: {note['reason']}" if note.get("reason") else ". No reason given.")},
        {"at": note["at"], "who": who, "what": f"{who} confirmed they reviewed it and saved it to the chart."},
    ]
    return {**note, "origin": origin(note), "steps": steps, "diff": diff if ai["edited"] else None, "changed_pct": pct}


def summary(notes: list, unsaved_answers: int) -> dict:
    labels = [origin(n) for n in notes]
    return {"doctor_led": labels.count("Doctor-led"), "ai_edited": labels.count("AI-assisted, doctor edited"),
            "ai_unchanged": labels.count("AI text accepted unchanged"), "ai_answers_not_used": unsaved_answers}


if __name__ == "__main__":
    parts, pct = changes("Start carboplatin at full dose.", "Start carboplatin at reduced dose.")
    assert parts == [["same", "Start carboplatin at"], ["removed", "full"], ["added", "reduced"], ["same", "dose."]], parts
    assert 0 < pct < 50
    assert changes("same text", "same text") == ([["same", "same text"]], 0)
    print("ok")
