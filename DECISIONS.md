# Week 1: the stack, the first call, and what it costs

## Week 1

**Run conditions.** Everything below was produced on:

- machine: Intel Core Ultra 7 258V, 32 GB RAM
- model: qwen3:4b-instruct
- served by: Ollama, one request at a time, locally
- date: 2026-10-02

Every number in this file is meaningless without those four lines, so they are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the required model set.

### 2. The first call

| | |
|---|---|
| finish reason | stop |
| prompt tokens | 24 |
| completion tokens | 49 |
| elapsed | 5.76 s |

The finish reason was `stop`, meaning the model completed normally. If it returned a truncation instead, the program would need to treat the response as incomplete rather than assuming that it contained a complete answer.

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
|---|---:|---:|---:|
| closed_short, t=0.0 | 1/12 | 1/6 | 0.17 s |
| closed_short, t=1.0 | 1/12 | 1/6 | 0.17 s |
| open_list, t=0.0 | 1/12 | 1/6 | 3.00 s |
| open_list, t=1.0 | 11/12 | 6/6 | 2.84 s |

The `closed_short` cell still returned a single answer at temperature 1.0. The question has a very constrained answer space, so increasing temperature did not result in different outputs.

An exact-string equality test would pass for the tested temperature-0 outputs and for `closed_short` at temperature 1.0 because those outputs repeated exactly. It would fail for `open_list` at temperature 1.0 because all six outputs were different. This shows that exact-string equality is not generally reliable for testing open-ended model outputs.

**The sentence that carries into week 10.** Model outputs can repeat reliably for sufficiently constrained prompts and settings, but exact repetition cannot be assumed for more open-ended prompts, especially as temperature increases.

### 4. The cold start

- cold call: 3.45 s
- warm call: 0.19 s
- ratio: approximately 18.2×

The cold start was much slower because the model had to be loaded into memory. A system that switches between multiple models could therefore introduce significant additional latency if models need to be repeatedly loaded and unloaded. I would avoid unnecessary model switching and keep the required model loaded where possible.

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
|---|---:|---:|
| small tier | approximately €0.03 | approximately €3.33 |
| large tier | approximately €2.49 | approximately €244.22 |

Estimates against the price list dated 2026-08-10, not measurements. Running locally, my actual monetary cost was zero.

I would use the small tier for nightly evaluation because repeated evaluation needs to remain inexpensive. I would use the large tier before a release, when the additional cost can be justified for a more thorough final evaluation.

### Deferred

Nothing deferred.

---

# Week 2: a structured-output extractor, measured

## Week 2

**Run conditions.** model: qwen3:4b-instruct | temperature: 0.0 | prompt version: zero-shot and four-example few-shot | served locally | date: 2026-10-02 | scored on: my own machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: `null`
- due_date, when the message states only a relative expression: `null`
- quote, and what "verbatim" means in my scorer: the quote must occur exactly as a substring of the original source text, without translation or paraphrasing
- what my scorer does with a record that failed validation: it increments the invalid count and records every scored field as a failure

This matters because skipping records that failed validation would artificially improve the reported score as the number of invalid model outputs increased.

### 2. Zero-shot, per field

| field | correct | of |
|---|---:|---:|
| category | 7 | 10 |
| urgency | 9 | 10 |
| due_date | 9 | 10 |
| quote | 9 | 10 |
| invalid records | 0 | 10 |

My prediction before block 3 was that examples would help most with category boundaries because examples can demonstrate distinctions between labels that may be difficult to express completely in the prompt.

### 3. Few-shot

I selected four examples from the held-out `EXAMPLE_POOL`, rather than from the ten evaluation documents.

| example | why it is in the block | field it should move |
|---|---|---|
| EX-01 | provides an English access example with no explicit due date | category / due_date |
| EX-02 | provides a French facilities example and demonstrates multilingual extraction | category / urgency |
| EX-03 | provides a German hardware example with an explicit date | category / due_date |
| EX-04 | provides an English `other` example with no due date | category / due_date |

| field | zero-shot | few-shot | move |
|---|---:|---:|---:|
| category | 7/10 | 7/10 | +0 |
| urgency | 9/10 | 10/10 | +1 |
| due_date | 9/10 | 8/10 | -1 |
| quote | 9/10 | 10/10 | +1 |

### 4. What got worse

The `due_date` field got worse, decreasing from 9/10 to 8/10. In the few-shot run, the model invented dates for REQ-05 and REQ-10 even though those messages did not contain explicit calendar dates.

The category score did not improve. In the few-shot failure output, REQ-04 was classified as `access` instead of `facilities`, REQ-08 as `access` instead of `hardware`, and REQ-09 as `facilities` instead of `other`. Looking at the individual failures therefore shows that the examples did not solve the category-boundary problem even though other fields improved.

### 5. What the examples cost

- extra input tokens per call: 391
- per thousand calls: 391,000
- estimated euros per thousand calls on the small tier: approximately €0.08, against the price list dated 2026-08-10. Estimate, not a measurement.

The additional cost is calculated from the small-tier input price of €0.20 per million tokens. Running locally, the actual monetary cost was zero.

### 6. Ship it or not

I would not ship the few-shot variant yet. It improved urgency from 9/10 to 10/10 and quote from 9/10 to 10/10, but category remained unchanged at 7/10 and due_date became worse, falling from 9/10 to 8/10. It also adds 391 input tokens to every call.

Ten evaluation records are not enough to establish that the few-shot variant is consistently better. I would reconsider this decision if a larger evaluation set showed consistent improvements without introducing additional due-date errors.

### Sensitivity variant

Variant assigned: `role`.

I prepended `You are a senior service desk analyst.` to the few-shot baseline prompt and changed nothing else.

| field | baseline | role | move |
|---|---:|---:|---:|
| category | 7/10 | 7/10 | +0 |
| urgency | 10/10 | 10/10 | +0 |
| due_date | 8/10 | 9/10 | +1 |
| quote | 10/10 | 10/10 | +0 |

The role variant improved the `due_date` field by one case, from 8/10 to 9/10. Category, urgency, and quote did not change.

For the English documents, both variants had 3 field errors. French improved from 2 field errors to 1, while German remained at 0. With only ten documents in total, these results are not enough to conclude that adding the role instruction consistently improves performance.

The experiment shows that even a small prompt change can alter measured behaviour, which is why prompt changes should be measured rather than assumed to be improvements.

### The gold set

Ten cases were written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

The quote scorer only checks whether the generated quote is an exact substring of the source document. It cannot determine whether that substring actually provides appropriate evidence for the predicted urgency.

### Deferred

A larger evaluation set would be needed to determine whether the observed few-shot and sensitivity differences generalize beyond these ten documents.