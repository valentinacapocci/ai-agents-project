# Week 1: the stack, the first call, and what it costs

---

## Week 1

**Run conditions.** Everything below was produced on:

- machine: Intel Core Ultra 7 258V, 32 GB RAM
- model: `qwen3:4b-instruct`
- served by: Ollama, one request at a time, locally
- date: 2026-10-02 for the first call and cost measurements, 2026-11-24 for the full live sweep

### 1. Machine and model set

I have the required model set installed (`qwen3:4b-instruct` and `nomic-embed-text`) plus the optional `qwen2.5:7b` model.

### 2. The first call

| | |
|---|---|
| finish reason | `stop` |
| prompt tokens | 24 |
| completion tokens | 49 |
| elapsed | 5.76 s |

The model finished with `stop`. If it had hit the output token limit, I would treat the answer as incomplete and retry with a higher limit if I needed the full answer.

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
|---|---:|---:|---:|
| closed_short, t=0.0 | 1/12 | 1/6 | 0.59 s |
| closed_short, t=1.0 | 1/12 | 1/6 | 0.71 s |
| open_short, t=0.0 | 1/12 | 2/6 | 8.53 s |
| open_short, t=1.0 | 5/12 | 5/6 | 7.61 s |
| open_list, t=0.0 | 1/12 | 1/6 | 12.95 s |
| open_list, t=1.0 | 11/12 | 6/6 | 11.57 s |
| open_reasoning, t=0.0 | 1/12 | 2/6 | 34.17 s |
| open_reasoning, t=1.0 | 12/12 | 6/6 | 25.26 s |

The course recording used `qwen3:4b-instruct` on 2026-08-10. At temperature 0.0, it had one distinct answer in every cell. My run matched that for `closed_short` and `open_list`, while `open_short` and `open_reasoning` each gave two distinct strings. The median latencies in the table are from my live run.

Which cell still returns a single answer at temperature 1.0, and why that one:

`closed_short` gave the same answer all six times. It asks for the capital of Luxembourg in one word, so there is little room for the answer to vary.

Which cells a test asserting exact string equality would pass on, and what that tells me about testing this system:

Using the first answer in each cell as the expected string, every later answer would match for `closed_short` at both temperatures and `open_list` at temperature 0.0. Every other cell would have at least one mismatch. The counts show when the strings differ. I would have to read the answers to see whether those differences change the meaning.

**The sentence that carries into week 10.** I would use exact string equality for a fixed answer like the capital and check open-ended answers against the requirements of the prompt, since two of my open-ended prompts varied even at temperature 0.0.

### 4. The cold start

- cold call: 3.228 s
- warm call: 0.188 s
- ratio: 17.2×

What this implies for a system that uses more than one model, and what I will do about it:

The cold call took about three seconds longer with the same prompt. If switching models means loading one again, that wait can land on the user’s request. I would keep the main model loaded if memory allows and measure the switching delay before putting a second model in the request path.

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
|---|---:|---:|
| small tier | €0.0335 | €3.28 |
| large tier | €2.49 | €244.14 |

Estimates against the price list dated 2026-08-10, not measurements. Running locally, my actual monetary cost was zero. I used 38 input tokens and 200 output tokens per case and assumed one run per night for 14 weeks.

Which tier I would run nightly, which I would run before a release, and why not the same one for both:

I would use the small tier for nightly checks because it costs about €3.28 over 98 runs. Before a release, I would run the same cases on the large tier if I were considering it for deployment. I would compare which cases each model gets right before deciding whether the extra cost is worth it.

### Deferred

I have the models needed for Week 1. I still need to download the optional `qwen3-vl:4b` before week 9.

---

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