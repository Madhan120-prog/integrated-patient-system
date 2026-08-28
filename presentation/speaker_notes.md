# Speaker Notes — Integrated Patient Data System (12 slides)

Casual, first-person notes — paste each section into that slide's PowerPoint Notes pane.

---

## Slide 1 — Title

So this whole thing started from something pretty simple. I noticed doctors at this cancer center have to log into six different systems just to see one patient's full picture. That's really the seed of it. This isn't an AI project at heart — it's a data problem, and AI just helps at the end. Keep that in mind through the whole deck: data first, AI second.

---

## Slide 2 — The Problem

Six departments, six vendors, none of them talk to each other. I drew this one on purpose with no real connections between the doctor and the six boxes, because that's genuinely what it's like today — the doctor is the connector, by hand, every single time. Minutes lost, trends missed when records aren't seen side by side, and no record of what was actually reviewed before a decision. That last one's a bigger deal than it sounds.

---

## Slide 3 — The Goal

Simple goal: one place to see everything, one assistant that can reason across it, and both of those done safely. Those four words — unify, assist, secure, scale — aren't just nice-sounding. They're literally the four things I had to build. If I couldn't point to real working code for each one, it doesn't count.

---

## Slide 4 — How It Works

Probably my favorite slide. No jargon at all here. Six systems that don't talk, a connector that quietly matches up the same patient across all of them, one combined view built fresh each time it's needed, an AI that reads it and answers in plain English, a safety check, and the doctor gets one clear answer instead of six browser tabs. It's a grid, not a flowchart — these are pieces of the system, not steps that happen in some fixed order.

---

## Slide 5 — Overall View

Two halves, and that's really how I built it too. Data side first, AI side second — in that order, deliberately. If I'd started with the AI and bolted the data integration on afterward, I'd have ended up with something smart but blind. Get the boring plumbing right first, then the smart stuff can actually be trusted.

---

## Slide 6 — Data Integration

This is "the connector" from a few slides back, but the real version. Each department genuinely runs on a different storage tech — SQLite for labs, plain JSON files for MRI, that kind of thing — because that's actually how real hospital vendors do it. They don't coordinate with each other. The MPI is the one piece that knows a person in the lab system is the same person in the imaging system. Every gateway's whole job is translating that vendor's own format into one shared shape before anything else even sees it. Honestly, that's most of the real work — way more than the AI part.

---

## Slide 7 — Challenges

This one's just honest. Every single thing on here actually broke first, and then got fixed, in this exact project — not a "things that could go wrong" list. PHI needed to stay off the network, so a local model option had to exist. Small models don't reliably restate facts, so I stopped trusting them to and started computing facts myself. Six real schema mismatches. Semantic search that could leak across patients if I didn't explicitly stop it. Patient data itself possibly getting read as an instruction. And real hospital access turning out to be more of a legal hurdle than a technical one. No highlight reel here, all of it real.

---

## Slide 8 — AI Capabilities

Think of this as the AI side growing up over time. V2 was just Gemini in the cloud plus basic keyword matching — worked fine, but had a ceiling. V3 added a local option so it could run fully private if that mattered more, plus guardrails so I stopped trusting the model to get facts right from memory. V4 added real semantic search, so something like "how's her blood cell count" actually finds the WBC results even without that exact word, and MedGemma so it can look at an image locally. Each version fixed a real gap the one before it had.

---

## Slide 9 — Security Layer

Built this whole layer before letting myself add a single new feature. It's easy to make an AI demo look impressive and forget that a real hospital wouldn't let any of this near a real patient without auth, an audit log nobody can quietly edit, and guardrails that flag instead of censor — a human always makes the final call. The newer one's about making sure the AI's own search can't accidentally leak one patient's data into someone else's answer. This slide is really what earns the right to touch real patient data at all.

---

## Slide 10 — Real-World Implementation

Honest gap check here: laptop demo versus an actual hospital. Same pieces, just harder at real scale. Connecting to a real EHR means FHIR and an actual approval process with someone like Epic, not just an API call. The laptop's local model becomes a real GPU sitting inside the hospital's own network. And the unglamorous truth — most of the delay in something like this actually going live is compliance and infrastructure, not the AI part.

---

## Slide 11 — Budget

Wanted this number to hold up, not just sound good. Three paths — pay per use, rent a GPU, or buy one outright — all real tradeoffs, no obvious winner. But the real point is that infrastructure alone isn't the whole cost. Compliance and integration stack right on top of it. Add both honestly and you land around fifty to a hundred thousand a year, which actually matches what real hospital AI pilots report spending. The reasoning matters more than the number itself.

---

## Slide 12 — Status & Path Forward

Ending on where things actually stand, not a victory lap. Left side is done and tested — the architecture, the AI assistant, security, retrieval, local vision. Right side is honest about what's left — real multi-agent reasoning for harder questions, an actual EHR sandbox connection, production infrastructure. And the one line that sums up the whole project for me: the integration is the moat, the AI on top is just the differentiator. Anyone can call a model API. Not many people actually go fix six systems that don't talk to each other.
