# Week 2: a structured-output extractor, measured

---

## Week 2

**Run conditions.** model: `qwen3:4b-instruct` | temperature: 0.0 | prompt version: `week02-zero-shot-v1` and four-example few-shot | served locally | date: 2026-10-02 | scored on: my own machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: `null`, because there is no date to extract
- due_date, when the message states only a relative expression: `null`, because I only extract explicit calendar dates
- quote, and what "verbatim" means in my scorer: the quote must appear as an exact substring of the source text, with the same casing, punctuation, and whitespace
- what my scorer does with a record that failed validation: it counts the record as invalid and marks all four fields wrong

Skipping invalid records would leave the hardest cases out of the scores and make the extractor look more accurate than it was.

### 2. Zero-shot, per field

| field | correct | of |
|---|---:|---:|
| category | 7 | 10 |
| urgency | 9 | 10 |
| due_date | 9 | 10 |
| quote | 9 | 10 |
| invalid records | 0 | 10 |

The live zero-shot run used 2,158 input tokens and 679 output tokens across ten documents. At the small-tier prices dated 2026-08-10, I estimate that 1,000 calls at the same average token counts would cost about €0.10.

My prediction, written before block 3: examples will help most on category because they can show the difference between labels that are easy to confuse from the definitions alone.

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
|---|---|---|
| EX-01 | Shows an English access request with no explicit due date | category / due_date |
| EX-02 | Shows how to label a French facilities request and its urgency | category / urgency |
| EX-03 | Shows a German hardware request with an explicit date | category / due_date |
| EX-04 | Shows an English request that belongs in `other` and has no due date | category / due_date |

| field | zero-shot | few-shot | move |
|---|---:|---:|---:|
| category | 7/10 | 7/10 | 0 |
| urgency | 9/10 | 10/10 | +1 |
| due_date | 9/10 | 8/10 | -1 |
| quote | 9/10 | 10/10 | +1 |

### 4. What got worse

The `due_date` score went from 9/10 to 8/10. The few-shot prompt fixed the date error in REQ-01, then introduced two new errors. It returned calendar dates for REQ-05 and REQ-10 even though neither message gave an explicit date. Both should have returned `null`.

The few-shot prompt fixed the quote in REQ-06 and the urgency label in REQ-09. I expected the examples to help most with category, but the same three category errors remained in REQ-04, REQ-08, and REQ-09.

### 5. What the examples cost

- extra input tokens per call: 391
- per thousand calls: 391,000 extra input tokens
- estimated euros per thousand calls on the small tier: €0.08 for the extra input tokens, against the price list dated 2026-08-10. Estimate, not a measurement.

### 6. Ship it or not

I would keep zero-shot for now. The four examples fixed one urgency label and one quote, but they left the category errors in place, added a net date error, and cost 391 extra input tokens per call. With only ten records, I would try both prompts on more requests and switch if few-shot kept its gains without inventing more dates.

### Sensitivity variant

Variant assigned: `role`. What I changed: I prepended `You are a senior service desk analyst.` to the few-shot prompt. What moved: in the saved sensitivity summary, `due_date` went from 8/10 to 9/10. Category stayed at 7/10, and urgency and quote both stayed at 10/10.

### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

The scorer can check that a quote appears verbatim in the message. It cannot tell whether that quote actually supports the urgency label.

### Deferred

Nothing deferred.