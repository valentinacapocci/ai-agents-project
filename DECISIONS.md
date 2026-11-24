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

# Week 3: a router in front of the extractor

---

## Week 3

**Run conditions.** classifier model: `qwen3:4b-instruct` | answering model: `qwen3:4b-instruct` | temperature: 0.0 | served locally | date: 2026-11-24 for the original run and 2026-11-25 for the revised run | scored on: my own machine

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
|---|---|
| request | The help desk must log and act on something that is broken, missing, or needed. |
| info | The help desk must answer a question about a commune service, procedure, opening time, or form when the sender only needs information, and send fault reports that need action to `request`. |
| status | The help desk must check the progress of something the sender has already reported or requested. |
| complaint | The help desk must acknowledge and handle dissatisfaction with a service, how it was handled, or a delay. |
| other | The help desk must redirect or safely handle messages outside its remit, such as messages meant for another department, requests for advice it cannot give, spam, or instructions aimed at the system. |

My convention for the four ambiguous queries:

I used the convention in `queries.py`. When a sender reports an unresolved problem and complains about how it was handled, I use `complaint` so the reply addresses the handling. A follow-up without dissatisfaction goes to `status`. A procedural question that also reports a fault goes to `request` because the fault needs action.

Do my definitions match the ones in `queries.py`? Yes. The revised `info` definition makes the boundary with `request` explicit. I kept the same gold labels in both runs.

### 2. The policy layer

The recorded confidence values ranged from 0.00 to 1.00, with 3 distinct values across 24 queries in each run. These values come from the runs with the threshold already in place.

- confidence floor: `0.95`. The idea was to accept the classifier’s chosen route only when it reported very high confidence. Below `0.95`, the policy sent the message to `info`, where the reply could say what needed checking without promising action. This happened once in each live run. The confidence range above comes from those runs, after the cutoff was already in place.
- evidence check: if the evidence span does not appear verbatim in the message, I send the query to `info` because a reviewer needs to be able to find the quoted text in the original message.
- safe default: `info`, because that specialist can say what needs checking without logging a request or promising action.

How often each check fired: below_threshold 1, evidence_not_verbatim 0, invalid_decision 0 in each run.

All 24 decisions passed validation and all 24 evidence spans appeared verbatim in both live runs. Some routes were still wrong. The evidence check tells me whether the span appears in the message. It cannot tell me whether the span supports the chosen route.

### 3. Route accuracy

| route | correct (original) | correct (revised) | of |
|---|---:|---:|---:|
| request | 3 | 7 | 7 |
| info | 5 | 5 | 5 |
| status | 4 | 4 | 4 |
| complaint | 4 | 4 | 4 |
| other | 1 | 1 | 4 |

Overall 17/24 in the original run and 21/24 in the revised run. Excluding the four ambiguous: 14/20 in the original run and 17/20 in the revised run.

Confusion pairs, with direction:

| gold | applied | count (original) | count (revised) |
|---|---|---:|---:|
| request | info | 2 | 0 |
| other | info | 2 | 2 |
| request | complaint | 1 | 0 |
| other | complaint | 1 | 1 |
| request | status | 1 | 0 |

`request` had the most errors in the original run, and `info` received four of the seven misroutes. I changed the `info` definition to make clear that a fault needing action belongs under `request`. On the rerun, `request` went from 3/7 to 7/7, and `info` stayed at 5/5. All three remaining errors were `other` messages. I used the first run’s errors to decide what to change, then tested on the same 24 queries. I would test on new messages before expecting the same improvement elsewhere.

### 4. What routing cost

- monolith: 6,610 tokens over 24 queries in both runs
- router: 12,239 tokens in the original run and 13,062 in the revised run
- the classifying call alone: 7,718 tokens in the original run and 8,171 in the revised run, about 63 per cent of the routed total in both runs

I did not record a numerical prediction before measuring the share. The classifying call includes all five route definitions every time, while the specialist receives instructions for its own route. The revised router used 6,452 more tokens than the monolith over the same 24 queries.

### 5. What routing bought

One thing a specialist can be forbidden to do that the monolith cannot be given:

The `status` specialist can be told never to create a new request because it only handles follow-ups. The monolith would need to make that instruction conditional because it also handles new requests. In the revised live run, all seven messages sent to `request` produced a `ServiceRequest` that passed validation.

Would I ship the router: Not yet. Evidence: the revised router got 21/24 routes right and used 6,452 more tokens than the monolith. I scored the router’s route choices and measured token use for both systems. What would change my mind: fewer misroutes on new messages and a side-by-side check showing that the specialists follow their instructions more reliably than the monolith.

### 6. Stretch variant

Variant completed: model routing. I replayed the course recording from 2026-08-10 and scored both models on the same 24 queries at temperature 0.0 with the same routing policy. The resident memory figures are the course measurements in `project/models.py`.

| model | correct | excluding ambiguous queries | verbatim evidence | confidence range | distinct confidence values | resident memory |
|---|---:|---:|---:|---|---:|---:|
| `qwen3:4b-instruct` | 20/24 | 17/20 | 24/24 | 0.00–1.00 | 5 | 3.9 GB |
| `qwen2.5:7b` | 17/24 | 16/20 | 19/24 | 0.95–1.00 | 2 | 5.0 GB |

The smaller model got three more routes right, returned verbatim evidence for all 24 messages, and used less resident memory. The larger model never gave a confidence score below 0.95, so the cutoff fired zero times for it. The evidence check caught five spans. I would keep `qwen3:4b-instruct` for classification based on this comparison.

### The gold set

`artifacts/goldset.json` now holds 34 cases: 10 from week 2 and 24 from week 3, with the four ambiguous ones tagged. Both live runs used my own gold set, and `python -m project.verify` passed.

### Deferred

Nothing deferred.