# Decisions
## Week 1 - Variance

### TODO 5

**a. Temperature 0**

At temperature 0, both tested cells produced 1 distinct answer out of 6 runs on my machine. This agrees with the recording, where the corresponding cells also produced 1 distinct answer out of 12 runs.

**b. Temperature 1.0**

At temperature 1.0, `closed_short` still produced only 1 distinct answer, while `open_list` produced 6 distinct answers out of 6 runs. The closed question has essentially one constrained answer ("Luxembourg"), so increasing temperature does not necessarily result in different outputs when the possible answer space is very limited.

**c. Exact-string unit testing**

An exact-string equality test would work for the tested temperature-0 outputs and for `closed_short` at temperature 1.0 because those outputs repeated exactly. It would fail for `open_list` at temperature 1.0 because all 6 outputs were different. This shows that exact-string equality is not generally reliable for testing model outputs, especially for open-ended prompts.

### TODO 6

Model outputs can repeat reliably for sufficiently constrained prompts and settings, but exact repetition cannot be assumed for more open-ended prompts, especially as temperature increases.

### results
closed t=0          1/6
closed t=1          1/6
open list t=0       1/6
open list t=1       6/6

### TODO 7 - Cold start

Cold start: 3.45 s  
Warm call: 0.19 s

The cold start was much slower because the model had to be loaded into memory. Switching between different models within a single request could therefore introduce significant additional latency if models need to be loaded and unloaded. I would avoid unnecessary model switching and keep the required model loaded where possible.

### TODO 8 - Evaluation cost

A 200-case evaluation run every night for 14 weeks results in 19,600 model calls.

Estimated hosted cost:
- Small tier: approximately €3.33 total
- Large tier: approximately €244.22 total

These are estimates based on the price list dated 2026-08-10, not measured costs.

I would use the small tier for nightly evaluation because repeated evaluation needs to be inexpensive. I would use the large tier before a release when the additional cost can be justified for a more thorough final evaluation.