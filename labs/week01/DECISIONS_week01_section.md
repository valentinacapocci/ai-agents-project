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

Nothing deferred.