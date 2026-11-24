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

- confidence floor: 0.95, because a wrong route can send a fault report to a specialist that only answers questions. One message fell below the cutoff in each run. I only tested this cutoff, so I don’t know whether another value would work better.
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