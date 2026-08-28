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

*(more entries appended below as the build progresses)*
