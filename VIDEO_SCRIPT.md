# Video Script — RepoAssess (≤5 minutes)

## Overview

This script walks through the RepoAssess project: the problem, the baseline, the
advanced multi-agent solution, the evaluation results, and the key insights.

Target duration: 4 minutes 30 seconds.

---

## [0:00–0:30] Problem Statement

**Narration:**
"Imagine you're an engineering team evaluating a codebase for adoption or
purchase. You look at the README — it looks fine. But is the code actually good?
Are there tests? Is it maintainable? Is it secure? The README can't tell you.

RepoAssess solves this problem. It's a multi-agent system that analyzes a code
repository across four dimensions — structure, testing, code quality, and
maintenance — using 10 real code analysis tools, and produces an
evidence-backed quality report."

**Visual:** Show the README of a repo, then cut to the RepoAssess architecture diagram.

---

## [0:30–1:00] Baseline Solution

**Narration:**
"First, the baseline. This is the simplest approach — what someone might do
with ChatGPT. Read the README, look at the file listing, and produce a score.

The baseline uses only two tools: read_readme and analyze_structure. It makes
a single assessment call. No code analysis, no test execution, no git history."

**Visual:** Show `src/baseline.py` — highlight the two tool calls and the single
prompt approach. Show the output: score 5-6/10 for everything.

**Key point:** The baseline gives everything a score around 5/10. It can't tell
a platinum repo from a terrible one.

---

## [1:00–2:30] Advanced Multi-Agent Solution

**Narration:**
"The advanced solution uses four specialist agents running in parallel, each
focused on one dimension:

1. **Structure Agent** — reads README, analyzes dependencies, checks for
   Dockerfile, packaging config
2. **Test Agent** — counts test files, runs the test suite with pytest, checks
   for CI/CD configuration
3. **Code Quality Agent** — analyzes cyclomatic complexity via AST, checks for
   TODO/FIXME/HACK markers, docstring coverage, and security issues
4. **Maintenance Agent** — analyzes git history, contributor count, recent
   activity, release tags

Each agent calls real tools, gathers structured data, and produces findings
with evidence citations."

**Visual:** Show `src/advanced.py` — scroll through the agent functions.
Highlight the concurrent.futures ThreadPoolExecutor for parallel execution.

**Then show the verification agent:**
"A verification agent cross-checks every finding against the raw tool data.
If a finding can't be backed by evidence, it's flagged as unverified."

**Visual:** Show the verification_agent function and a sample output with
verified_count and flagged_count.

---

## [2:30–3:30] Evaluation Results

**Narration:**
"We evaluated both solutions on 12 synthetic test repositories with known
quality scores — from a platinum repo with tests, docs, and low complexity
to a minimal empty project."

**Visual:** Show the evaluation report table:

| Metric | Baseline | Advanced | Improvement |
|---|---|---|---|
| Score accuracy (MAE) | 1.92 | 0.92 | 52.2% better |
| Ranking accuracy | 69.7% | 86.4% | +16.7pp |
| Total findings | 42 | 175 | 4.2x more |
| Recommendation accuracy | 50.0% | 83.3% | +33.3pp |

**Narration:**
"The advanced solution improved score accuracy by 52%, produced 4 times more
specific findings, and correctly recommended adopt/investigate/avoid 83% of
the time versus 50% for the baseline.

5 out of 12 repos were scored with zero error."

**Visual:** Show `evaluation/report.md` and the per-repo comparison table.

---

## [3:30–4:15] Agent Trajectories

**Narration:**
"Every agent run produces a structured JSON trajectory that captures each
tool call, the agent's reasoning, and the final result. These are the agent
trajectories required by the hackathon."

**Visual:** Show a trajectory JSON file — highlight the steps array with
tool_call entries showing tool name, inputs, and outputs.

---

## [4:15–4:30] Hot Take and Conclusion

**Narration:**
"The biggest lesson from this project: scoring calibration mattered more
than the agent architecture. Adding agents and tools increased finding
specificity 4x, but it was the scoring recalibration — starting from a
lower base and requiring evidence of quality rather than penalizing its
absence — that actually improved accuracy by 52%.

Invest in calibration and verification before complexity. A well-calibrated
simple system you trust is worth more than a complex system you don't."

**Visual:** Show the repo URL: github.com/shaikahad-tech/Frontier-eng-hackathon

---

## Recording tips

- Use a screen recording at 1920x1080
- Show the code in a dark theme editor (VS Code)
- Use the terminal for running commands
- Keep the camera off, narrate over the screen
- Total duration: ~4:30 (well under the 5-minute limit)
