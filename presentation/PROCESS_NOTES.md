# Pitch Deck — Build Process Notes

Live log of what's being built, why, and the decisions made along the way.
Written in parallel with `pitch_deck.pptx` so the reasoning isn't lost —
this is not a polished doc, it's a working record.

---

## 2026-08-15 — Kickoff

### Goal
One-shot pitch meeting with West Cancer Center (real hospital — **never
named in the deck itself**, per explicit instruction) within the next few
days. Audience: doctors/physicians/clinical staff, little to no technical
background. A live demo is planned as the centerpiece — the deck's job is
to set up the problem, earn early trust, and get out of the way for the
demo, then close on a small concrete ask.

### Non-negotiable content (must be covered, can be delivered visually)
1. Pipeline/design of the product, explained simply
2. Customization/personalization to their specific setup
3. How data is extracted
4. Likely data structures/file types/information they have
5. Databases/database software they may run
6. How the data files get analyzed
7. Output type/visualizations — for doctors, how it helps decisions
8. Input formats
9. How this is secured in a hospital environment

Mapped these onto slides rather than 1:1 — several combined per slide so
the deck doesn't turn into a 20-slide technical lecture for a non-technical
room. See outline below for the mapping.

### Why the old deck got scrapped
User feedback: wrong tone (read like a portfolio/demo writeup, not a
confident vendor pitch) and not visual enough. Old deck also led with
architecture (MPI, gateways, storage-tech tables) — fine for a technical
reader, wrong for a room of clinicians who don't care *how* it works
internally, only that it *does* work and is safe.

### Design decisions

**Palette — Clinical Navy / Ice Blue / Warm Coral**
- Navy `14213D` — dominant (~65%), backgrounds for title/close slides,
  headers, icon circles. Reasoning: navy reads as trustworthy/clinical
  without being generic corporate blue — chosen deliberately, not a
  default.
- Ice Blue `D8E6F3` — secondary, light slide backgrounds and cards.
- Warm Coral `EF6351` — sharp accent only. Reasoning: healthcare decks
  skew cold (blues/greens/white); one warm human tone breaks that and
  draws the eye to what matters (CTAs, the ask, key stats) without
  turning into a rainbow of accent colors.
- White `FFFFFF` — neutral, body backgrounds/text-on-navy.

**Motif — icon-in-circle, repeated everywhere.** Every concept (a pipeline
step, a data format, a trust point) gets one icon inside a navy or coral
circle plus a short label. Chosen because it scales down complex technical
ideas (extraction, analysis, matching) into something a non-technical
reader parses in one glance, and it's the single repeated visual thread a
"mostly pictures" deck needs to not feel like a random slide grab-bag.

**Fonts.** Cambria (bold) for headlines — a safe-list serif with QA-
reliable width, reads more institutional/trustworthy than a sans title
would for this audience. Calibri for body/captions.

**Typography discipline.** Minimal text per slide — a headline plus one
visual, not paragraphs. This audience is here to watch a live demo, not
read; the deck's text budget is spent on the headline doing the framing
work, not on explaining details out loud.

### Outline (11 slides) and what each covers

| # | Slide | Covers from the non-negotiable list |
|---|---|---|
| 1 | Title / hook | — |
| 2 | The problem, visually | (sets up 1, 3, 6 for slide 3) |
| 3 | How it works, start to finish (pipeline visual) | 1, 3, 6 |
| 4 | We meet your data where it lives (format/system icon grid) | 4, 5, 8 |
| 5 | Built around your systems, not ours | 2 |
| 6 | Live demo hand-off | — |
| 7 | What you just saw (output for doctors) | 7 |
| 8 | Trust & safety, in plain terms | 9 |
| 9 | Getting this running here (phased pilot) | — |
| 10 | Investment | — |
| 11 | The ask | — |

**Note on slide 4:** deliberately kept to format *categories* (scanned
reports, flat exports, imaging archives, database-backed systems, free-text
notes) rather than naming specific vendor products (no Epic/Cerner/GE
logos) — we don't yet know their actual stack, and naming vendors we
haven't verified compatibility with risks overclaiming in a room that will
remember exactly what was promised.

**Note on Investment slide:** the $50-100K/year range comes from
`project_knowledge.md`'s prior research (matches published real-hospital AI
pilot spend) — carried over as directionally reasonable, not a firm quote.
Flagging this back to the user before the real meeting; a live financial
number in front of a real prospective client isn't something to leave on
autopilot.

### Build approach
`pptxgenjs`, `LAYOUT_WIDE` (13.3"x7.5"), icons rendered via `react-icons` →
SVG → `sharp` PNG → embedded as images (per the pptx skill's icon
workflow). Native shapes for connectors/timelines rather than static
images, so spacing stays exact.

---

### Build result

Built with `pptxgenjs` (`LAYOUT_WIDE`, 13.333"×7.5"), icons rendered via
`react-icons` → SVG → `sharp` PNG, embedded as images inside navy/coral
circles (the repeated motif). Ran clean on the first generation pass — no
corrupt-file footguns hit (chart axes, negative shadow offsets, shared
option objects, etc. — n/a here since this deck uses no native charts).

QA performed, all passed:
- `scripts/office/validate.py` — structural/schema validation: **all
  checks passed**.
- Rendered all 11 slides to JPEG (LibreOffice → PDF → `pdftoppm`) and
  inspected each visually: no text overflow, no overlapping elements, no
  contrast issues, consistent spacing/margins, icon-in-circle motif held
  across every slide.
- `markitdown` content dump, grepped for leftover placeholder text
  (`TODO`, `lorem`, `[insert`, etc.) — clean.
- Grepped for the hospital's real name — clean, doesn't appear anywhere.

Output: `presentation/pitch_deck.pptx` (11 slides). Intermediate QA files
(rendered JPEGs, PDF) deleted after inspection — not needed going forward.

### Flagged back to the user (not decided unilaterally)

- **Investment slide (#10) uses a $50K–100K/year range** carried over from
  `project_knowledge.md`'s prior research on comparable hospital AI pilot
  spend. It's directionally reasonable, not a number this project has
  independently verified for this specific engagement — worth confirming
  before it's said out loud in the real meeting.
- The "gives back" stat on the same slide is deliberately qualitative
  ("more time with patients, less time hunting for records") rather than
  a fabricated precise number — didn't want to invent a specific
  hours/week figure with nothing behind it.

### Still open (not done in this pass, flagged from the original plan)

- `demo_script.md` — needs a live rehearsal against the running app to
  pick a patient/questions confirmed clean against the open hallucination
  bugs (HANDOFF.md §0.4). Can't be finalized from docs alone.
- `qa_brief.md` — plain-language objection-handling notes for the
  presenter.
- Old deck files (`Patient_portal_presentation*.pptx`,
  `West_Cancer_Center_IPDS_Review.pptx`, `speaker_notes.md`) left
  untouched in `presentation/` — not deleted, since removing them wasn't
  asked for.

---

## 2026-08-15 — Round 2: DocAssist, real data standards, more diagrams

### What prompted this round
User reviewed the v1 deck (good reaction), made two manual edits directly
in the pptx — retitled slide 1 to name the product ("Integrated Patient
Portal with DocAssist.") and deleted the Investment + Ask slides — then
asked for three content gaps to be closed:
1. Nothing explained how AI (DocAssist) is actually integrated.
2. Nothing explained how reports are generated / data is analyzed.
3. The data-format slide didn't name real standards (e.g. DICOM for
   imaging) — flagged specifically.
Plus a general ask for more diagrams (flowcharts, tree diagrams, graphs)
and to "think more deeply."

**First fixed a QA gap of my own**: the "clean" content-QA claim from
round 1 was actually vacuous — `markitdown` wasn't installed, so that
grep ran against an empty file and silently passed. Installed
`markitdown[pptx]` and `python-pptx` properly this round and reran real
checks (see below) — flagging this so it doesn't get trusted blindly
next time either.

**Confirmed before touching anything**: rendered the user's edited pptx
to images and diffed against what I expected — title text change and the
two deleted slides were the only differences; nothing else drifted.
Asked explicitly whether to restore Investment/Ask after adding new
content — user said no, deliberately cut, don't restore. Deck now closes
on the phased-pilot slide.

### Changes made
- **Slide 1** — title text updated to match the user's edit (naming
  DocAssist directly), carried into the source script so future
  regenerations don't lose it.
- **Slide 4 (data formats) — upgraded to a tree diagram.** Root node
  ("every hospital data source") branches via dashed connector lines to
  4 cards, each naming the *real* standard: Imaging (MRI/X-Ray/CT) →
  **DICOM**, Labs → relational database, ECG → waveform flat-file,
  Treatment/EHR → **HL7 FHIR-style**. Grouped the three imaging
  modalities under one DICOM branch instead of repeating "DICOM" three
  times — cleaner tree, same accuracy. These are genuine standard names
  a clinician recognizes from their own PACS/EHR systems, not jargon
  introduced for this deck — confirmed this doesn't conflict with
  keeping the AI content non-technical, since DICOM/HL7 are *their*
  domain vocabulary, not ours.
- **New slide 6 — "Meet DocAssist."** Positioning-only: what it is, one
  line on how doctors interact with it, 3 capability chips (reads across
  departments, cites sources, cloud or fully private). Deliberately kept
  separate from the mechanics slide that follows — identity first,
  mechanism second, so neither slide gets overloaded.
- **New slide 7 — "How DocAssist builds every answer."** The actual
  answer to "how is data analyzed / how are reports generated": a
  5-step flowchart (question asked → right records found → facts
  computed → answer drafted → checked before shown) that's a plain-
  language description of the real pipeline — retrieval, the
  deterministic encoder, LLM drafting, guardrails — without using any of
  those internal names. Added a small native line chart underneath
  showing a compressed illustrative trend, captioned as illustrative
  (not a real patient shown to a stranger — deliberate, avoids a PHI/
  overclaiming problem in a sales deck) to make "facts computed, not
  guessed" concrete rather than just asserted. This is the "graph"
  requested, placed where it's actually load-bearing rather than
  decorative.
- Renumbered the demo hand-off / output / trust / pilot slides to follow
  the new section (8–11); no content changes to those beyond position.

### Bug caught in QA this round
The native chart's data labels initially rounded 12.4 → "12" (default
number format). Looked like a real defect, not acceptable for a slide
whose whole point is "computed precisely, not guessed" — fixed with
`dataLabelFormatCode: "0.0"` on both the data labels and the value axis.
Caught by rendering and looking, not by assuming the default was fine.

### QA this round (all real this time)
- `validate.py` — passed, including the new native chart (the exact
  chart footguns the pptx skill warns about — missing axis declarations,
  bad stacked-label positions — don't apply here since it's a single
  non-stacked line series).
- Rendered all 11 slides, inspected each — new tree diagram, DocAssist
  intro, and 5-step/chart slide all clean (no overflow/overlap), then
  re-rendered slide 7 alone after the label fix to confirm.
- `markitdown` content dump (properly installed this time) — grepped
  clean for placeholder text and for the hospital's real name.
- `python-pptx` slide count confirms 11 slides, matching the outline.

### Still open
- `demo_script.md`, `qa_brief.md` — unchanged from round 1, still
  pending a live rehearsal against the running app.
- Deck currently ends on the phased-pilot slide (slide 11) — no
  investment/cost or closing-ask slide, per explicit user instruction.

---

## 2026-08-16 — v2: "Getting real access" slide (non-destructive)

User asked how real-time data integration works and whether it's APIs
vs. a sync pipeline. Answered from the actual code (`lab_gateway.py`
etc., confirmed with `project_knowledge.md` §2): it's **on-demand
federated query** — MPI resolves the patient's local ID per department,
then each gateway calls that department's system live, at request time.
No batch/nightly copy. In production the same gateway shape just points
at real interfaces (HL7 FHIR APIs, DICOM query/retrieve, lab system
APIs) instead of local demo data — this is architecturally identical to
what a hospital's own interface engine (Mirth Connect/Rhapsody-style)
already does.

Asked what to actually put on a slide from that research. Recommendation
(given, not yet built until confirmed): don't put HL7/FHIR/DICOM/Mirth
Connect vocabulary on a slide — wrong altitude for a clinical audience
and breaks the visual-first design discipline held since round 1. The
one idea worth a slide is the *access process itself* — test data first,
their IT signs off, then live in stages — since it preempts the room's
likely unspoken doubt ("will this survive contact with our real
systems") without any jargon. Deeper protocol detail earmarked for
`qa_brief.md` (still pending) as spoken backup, not slide content.

User approved, with one explicit constraint: **do not overwrite the
existing deck** — build this as a new v2 file instead.

**Built:** `presentation/pitch_deck_v2.pptx` (12 slides) — identical to
`pitch_deck.pptx` (11 slides, untouched, still on disk) plus one new
slide 11, "Getting real access happens in stages — not all at once": a
3-step visual (test data first → your IT signs off → then live, one
department at a time) with a closing line, *"the same integration
pattern hospitals already run — nothing new for them to adopt."* Placed
right before the closing pilot-path slide, which shifted to slide 12
with no content changes. No existing slide's content was edited — pure
addition, per the "don't override" instruction.

QA: `validate.py` passed, slide count confirmed at 12, new slide
rendered and inspected (clean, no overflow/overlap), `markitdown` grep
clean for placeholders and the hospital's real name. Confirmed both
`pitch_deck.pptx` (unchanged, same file size/timestamp as before this
session) and `pitch_deck_v2.pptx` exist independently on disk.

---

## Parked idea — domain-specific local AI slide (not yet built)

User wants to revisit adding a slide showing DocAssist's foundation can
extend to a **domain-specific, locally-trained model** — example given:
AI-assisted tumor detection (brain or elsewhere), fine-tuned on *this*
hospital's own imaging data, running either on their own GPU hardware
on-prem or in a BAA-secured cloud.

Grounding: this isn't invented for the pitch — `MedGemma` (a medical
vision model) is already wired into the app locally via Ollama for
image/document analysis (see `HANDOFF.md` §"MedGemma vision adapter").
A tumor-detection model would be the specialized version of that same
foundation, fine-tuned on the hospital's own labeled scans instead of
general medical knowledge.

**Proposed slide (discussed, not built):** one slide, placed near the
end (before the closing pilot slide), titled something like *"This same
foundation can go further, if you want it to."* Three points: (1)
trained on your data, not just general knowledge, (2) runs on your GPU
hardware or a BAA-secured cloud — your choice, (3) an explicit honest
caveat that diagnostic-use models like this need clinical validation
(likely FDA clearance / Software-as-a-Medical-Device pathway) before
real use — framed as a platform capability/vision point, not a pilot-day
deliverable.

**Why the caveat matters:** DocAssist reads and summarizes an existing
chart (human always decides) — low regulatory bar. A model making an
actual diagnostic call on an image is a different, heavier regulatory
category. Recommended keeping that distinction visible on the slide so
the pitch doesn't accidentally imply something not true.

Real technical path if this ever gets built: fine-tune from MedGemma's
vision encoder or a purpose-built framework (MONAI is the standard for
hospital imaging AI) on radiologist-labeled local scans, train in a
secured on-prem/BAA-cloud environment, validate against radiologist
ground truth before any inference result touches real care.

Waiting on user to confirm wording/placement/whether to keep the
regulatory caveat before this becomes a v3 build.

---

## 2026-08-28 — New artifact: masters project proposal deck

User is taking a masters project course this semester under Dr. Dipankar
Dasgupta at University of Memphis, presenting a project plan to him the
next day, and wants this same codebase to serve double duty. Researched
(via web search, not memory) the actual program structure before
suggesting anything: MS Computer Science has a thesis option (COMP 7996)
and a non-thesis project option (COMP 7980, min. 3 credit hours, capped
combined with a few other course numbers at 6 hours) — specific
deliverable format (report length, defense structure) isn't published
anywhere public, flagged to the user to confirm directly with Dasgupta
or the CS graduate coordinator rather than guessing.

Also researched Dasgupta himself: William Hill Professor in Cyber
Security, Director of the Center for Information Assurance, IEEE
Fellow — research is artificial immune systems, bio-inspired computation,
and intrusion detection, not healthcare. That mismatch is exactly why
the two decks needed to stay separate rather than trying to reuse the
hospital pitch: a business audience and a research advisor need
different spines entirely.

**Key framing decision:** connected the project's existing guardrail
work to Dasgupta's own research vocabulary — his foundational idea is
"self vs. non-self" anomaly detection (immune-system-inspired). Proposed
framing the AI assistant's safety layer the same way: a "self" answer is
grounded/correct, a "non-self" answer is hallucinated, cross-patient
leaked, prompt-injected, or mislabeled — and the masters contribution is
formalizing that as a taxonomy and building/evaluating detectors. This
isn't a stretch — it's an honest bridge between what's already been
built and debugged in this project (the four real failure modes in
HANDOFF.md §0.4) and his actual field.

**Built:** `presentation/masters_project_proposal.pptx` (7 slides, new
script `build_masters_deck.js`, same navy/ice-blue/coral visual system
as the hospital decks for continuity but more content-forward — an
advisor pitch needs substance over polish). Outline: title → the
problem (four real observed failures, not hypothetical) → what's
already built (proof this isn't starting from zero) → the core
self/non-self framing slide → methodology & evaluation plan → 3-month
phased timeline → deliverables, closing with an explicit open question
back to Dasgupta about the report/defense format, since that's the one
thing that couldn't be confirmed from public sources.

QA: validate.py passed, all 7 slides rendered and inspected (clean),
markitdown content check clean, slide count confirmed.

Kept deliberately separate from the hospital pitch decks — different
audience, different job, sharing only the underlying codebase and
visual identity.

---

## 2026-09-25/26 — v3: real screenshots, security/reliability pillars, industry research

User asked for three things at once: (1) make the hospital deck more
visually convincing with real pictures instead of only icon illustrations,
(2) add a section on how the platform is being made secure/reliable/
flexible/fast, with an explicit HIPAA-collaboration framing, and (3)
deepen the data-integration story with real research on how small vs.
large healthcare orgs actually solve this — explicitly named as the
first priority. Also: no budget/cost slide (reconfirmed), and the closing
slide should ask the physicians what problems *they're* facing, not push
a pilot ask.

### Getting real screenshots — the actual story, including a mistake

First attempt: tried to drive the app myself via the Browser pane, then
via `claude-in-chrome`, to capture and save screenshots directly. Hit a
real chain of problems:
- The backend port was squatted by an unrelated Docker process; had to
  identify that and start the real backend separately.
- DocAssist was failing every query (503) because Ollama, the configured
  local model backend, wasn't running — started it.
- Chrome-automation clicks (`computer` left_click) silently failed to
  trigger this app's React buttons — real `.click()` via injected JS
  worked every time, coordinate/ref clicks did not. Root cause not fully
  diagnosed; worked around it by dispatching clicks through
  `javascript_tool` instead.
- The `save_to_disk` option on `claude-in-chrome` screenshots never
  produced a file findable anywhere on the filesystem, after a real
  search (Downloads, Caches, Application Support, scratchpad).
- Fell back to macOS's own `screencapture` as a last resort — **this was
  a mistake**. A blind full-screen capture grabbed the user's actual
  foreground Chrome window (a live, mid-draft Gemini conversation
  entirely unrelated to this task) instead of the automated tab, which
  apparently isn't composited on-screen at all. Deleted that file
  immediately and stopped using full-screen capture — it has no way to
  scope itself to the right window and risks capturing private,
  unrelated content. Flagged this to the user directly rather than
  quietly discarding it.

Resolution: user took the screenshots themselves and pasted them in —
9 real screenshots covering login, welcome, search, unified patient
record, both halves of analytics, the X-ray department table, and
DocAssist mid-answer with evidence expanded. Copied all 9 into
`presentation/assets/screenshots/` with descriptive names (user's
instruction: "use what you want, keep others in the assets"). Only 3
were used in the deck; the rest stay there as a reference library for
future slides.

### Cropping and annotation

Source screenshots included full browser chrome (tabs, bookmarks, macOS
menu bar, dock) — not usable raw in a pitch deck. Cropped all three
candidates to the same box (0, 197, 2000, 1160 out of a 2000×1300
source) via Pillow, verified visually, landed clean with no chrome or
dock artifacts.

First annotation attempt (arrows drawn diagonally from inside the dense
text area straight to callout boxes) was a real defect: the connector
lines cut directly across other readable sentences, exactly the "no
overlaps" quality bar the user set. Fixed by redesigning the pattern:
a thin highlight-box border drawn directly on the target text/card
inside the image (no line touching the image content at all), with the
connector line living *only* in the margin between the image's edge and
the callout box. Re-rendered and confirmed clean.

### New content

- **Slide 3** — real screenshot of the unified patient record (proves
  "one page instead of six logins" isn't a mockup).
- **Slide 6** — new: how healthcare actually solves integration at
  different scales, grounded in real published figures (small
  practice: $30K–150K, weeks; large hospital system: $500K–2M, months
  to years) rather than invented numbers — from actual web research
  this session, not memory.
- **Slide 10** — real annotated screenshot of a live DocAssist answer:
  one callout on the "Low confidence" flag ("flags what it's unsure
  about — automatically"), one on the cited evidence card ("cites its
  sources — every single time"). Deliberately reframes the known
  alert-fatigue quirk as a visible trust signal rather than hiding it.
- **Slide 12** — real screenshot of the analytics charts, replacing the
  old icon-card "what you just saw" slide with actual product UI.
- **Slide 14** — new "Secure. Reliable. Flexible. Fast." pillar slide.
  HIPAA line worded exactly per the user's direction: "we'll follow
  HIPAA guidelines end-to-end, working directly with your compliance
  team" — collaborative, not a compliance-jargon claim.
- **Slide 17** — new closing slide: asks the room what's slowing them
  down and invites suggestions, replacing any pilot/investment ask.
  No budget slide anywhere in this deck.

Net: 12 slides (v2) → 17 slides (v3). Saved as `pitch_deck_v3.pptx`,
non-destructive — v1 and v2 untouched on disk.

QA: `validate.py` passed, all 17 slides rendered and inspected
individually (the 3 real-screenshot slides and all 4 new slides checked
closely), `markitdown` grep clean for placeholders and for the
hospital's real name/domain, slide count confirmed.

---

## 2026-09-26 — Sequencing pass: fixed a real story problem on slide 3

Asked directly whether the deck actually reads as a sequential story.
Honest answer, not just validation: no, not quite — flagged three
concrete issues (10 slides of setup before the live demo hand-off; trust
said three separate times across slides 10/13/14; "we unify six systems"
proven three separate times across slides 3/5/7).

User zeroed in on one of these independently, from the PowerPoint side:
slide 3 (the real unified-record screenshot) felt unearned right after
the problem slide — it asserts the solved state before anything explains
*how*, and it spoils the live demo's reveal eight slides early. Agreed —
this was the sharpest of the three issues.

**Fix, per explicit direction ("slide count isn't the issue, everything
landing well is what matters")** — not a cut, a real addition:

- **New slide 3 — "How we actually connect six different systems."**
  A high-level, 3-step mechanism story that was genuinely missing from
  the whole deck: same patient has a different ID in every department
  system → one shared index matches the person → each system's own
  format gets translated on the spot. Closes with the "built fresh every
  time you ask — never a stale overnight copy" line, which is the real,
  already-researched federated-query architecture (see this session's
  earlier discussion: on-demand query, not batch) finally making it onto
  a slide instead of just living in conversation.
- **Old generic 4-icon "pipeline" slide removed** — it covered the same
  ground as the new mechanism slide (pull data in / match the patient)
  more vaguely, plus two AI-answering steps already covered properly by
  the later DocAssist slides. Redundant once the new slide existed.
  Removing it wasn't about slide count, it was about not saying the same
  thing twice at different altitudes.
- **Real screenshot slide moved from position 3 to position 4** — now it
  lands right after the mechanism is explained, so it reads as "and
  here's what that actually produces," not an unexplained assertion.

Net slide count: still 17 (one added, one removed) — count was never
the goal, sequencing was. The other two flagged issues (trust said three
times; six-systems-unified proven three times) are still open — not
touched yet, pending user direction.

QA: validate.py passed, both new/moved slides rendered and inspected,
content QA clean.

*(more entries appended below as the build progresses)*
