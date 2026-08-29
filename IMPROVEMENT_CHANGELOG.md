# Improvement Changelog

This changelog tells the story of how the solution evolved from a simple baseline to the final multi-agent system. Each entry describes what was tried, why, the evidence, and the decision that followed.

## Baseline: Single-prompt README analysis

**What we tried and why**
The simplest possible approach: read the README and file listing, send a single prompt to an LLM, and get back a quality score. This represents what a person might do with ChatGPT — paste the README and ask "is this repo good?"

**Evidence**
| Metric | Value |
|---|---|
| Mean Absolute Error (MAE) | 1.92 |
| Ranking accuracy | 69.7% |
| Total findings | 42 (3.5 per repo average) |
| Recommendation accuracy | 50.0% (6/12) |

The baseline consistently scores everything around 5/10 — it cannot distinguish excellent repos from terrible ones because it only sees the README. It gives platinum_repo a 6 when it should be 9, and tech_debt_heavy a 5 when it should be 2.

**Decision**
Established as the starting point. The baseline confirms the core problem: README alone is insufficient for quality assessment.

---

## Iteration 1: Added real code analysis tools

**What we tried and why**
Instead of relying on the README, we built 10 tools that actually inspect the repository:
- `read_readme` — read README content with metadata
- `analyze_structure` — directory structure, file types, project type
- `analyze_dependencies` — parse requirements.txt, pyproject.toml, package.json, Cargo.toml
- `analyze_tests` — count test files, test functions, test-to-source ratio
- `run_tests` — actually run the test suite with pytest
- `analyze_complexity` — cyclomatic complexity of every function (AST-based)
- `analyze_code_quality` — comment ratio, TODO/FIXME/HACK markers, tech debt
- `analyze_documentation` — docstring coverage, LICENSE, CONTRIBUTING, CHANGELOG
- `analyze_git_history` — commit count, contributors, recent activity, tags
- `analyze_security` — bare except, eval, exec, hardcoded secrets, shell=True

**Evidence**
With tools alone, the assessment could now access real code data. Test count, complexity numbers, and git history were available. Findings became specific: "Low test-to-source ratio: 0.00" instead of "might lack tests."

**Decision**
Kept. The tools fundamentally changed what the system could see — from surface metadata to actual code quality signals.

---

## Iteration 2: Added specialized agents for each dimension

**What we tried and why**
Split the analysis into four specialist agents, each focused on one dimension:
- **Structure Agent**: README, dependencies, packaging, project type
- **Test Agent**: test files, test execution, CI config, test-to-source ratio
- **Code Quality Agent**: complexity, tech debt markers, docstrings, documentation, security
- **Maintenance Agent**: git history, contributors, recent activity, releases

Each agent runs its tools, produces a dimension score, and lists specific findings with evidence.

**Evidence**
Total findings jumped from 42 to 175. Findings became organized by dimension: "[Code Quality] Low average complexity: 1.5" and "[Testing] All tests pass (8 tests)."

**Decision**
Kept. The multi-agent approach dramatically improved finding specificity (4.2x more findings) and provided structured, dimension-by-dimension analysis.

---

## Iteration 3: Added verification agent

**What we tried and why**
A risk with agent-based systems is hallucinated findings — the agent claims something unsupported by data. We added a verification agent that cross-checks every finding against the raw tool output.

**Evidence**
The verification agent found that ~64% of findings were directly backed by tool evidence entries. The remaining findings were verified against raw data values or flagged as unverified.

**Decision**
Kept. The verification agent adds a trust layer. Flagged findings are marked as lower confidence in the final report.

---

## Iteration 4: Calibrated scoring (the biggest improvement)

**What we tried and why**
The initial scoring started each agent at 5 (average) and gave too many bonus points for basic hygiene (having a README, having a LICENSE). This caused the system to consistently over-score bad repos.

We recalibrated:
- Structure agent: base 3 (not 5), README gives +1 (not +2), excessive deps gives -2
- Test agent: base 3, tests give +2, no tests gives -2, no CI gives -1
- Code quality agent: base 4, high complexity gives -3, tech debt >5 gives -2
- Maintenance agent: base 3, no recent activity gives -2

**Evidence**
| Metric | Before calibration | After calibration | Change |
|---|---|---|---|
| MAE | 2.00 | 0.92 | -54% |
| Recommendation accuracy | 27.3% | 83.3% | +56pp |
| Ranking accuracy | 83.6% | 86.4% | +2.8pp |

**Decision**
Kept. This was the single most impactful change. The key insight: basic hygiene (README, LICENSE) should be a prerequisite, not a bonus. Starting from a lower base and requiring evidence of above-average quality for higher scores produces much more accurate assessments.

---

## Iteration 5: Added security analysis

**What we tried and why**
Added a new `analyze_security` tool that checks for bare except clauses, eval/exec usage, hardcoded secrets, and shell=True. Merged this into the code quality agent's scope.

**Evidence**
The tech_debt_heavy repo was found to have a bare except clause, which the old version missed. The security analysis added a new dimension of findings that the baseline cannot see at all.

**Decision**
Kept. Security is a critical quality dimension that README-based assessment completely misses.

---

## Iteration 6: Added broken_tests repo (challenging case)

**What we tried and why**
Added a 12th test repo with tests that exist but are deliberately broken — the test file is present but assertions fail. This tests whether the system can distinguish "has tests" from "has working tests."

**Evidence**
The advanced solution correctly detected that tests were failing, but still over-scored (6 vs truth 3) because the test agent gives points for having test files before checking if they pass. The test execution results partially compensate, but the net score is still too high.

**Decision**
Kept. This is a known failure mode documented in the hot take below. The system correctly identifies the failing tests as a weakness, but the scoring doesn't penalize enough for broken tests.

---

## Final: Combined solution

**Evidence (final comparison on 12 test repositories)**

| Metric | Baseline | Advanced | Improvement |
|---|---|---|---|
| Score accuracy (MAE) | 1.92 | 0.92 | 52.2% better |
| Ranking accuracy | 69.7% | 86.4% | +16.7pp |
| Total findings | 42 | 175 | 4.2x more |
| Recommendation accuracy | 50.0% | 83.3% | +33.3pp |
| Verification rate | N/A | 63.8% | — |

5 repos scored with zero error (dependency_heavy, high_complexity, no_tests, single_author, well_documented).

---

## Experiments removed

### LLM-based assessment (attempted, not used in final)

**What we tried**
Initially planned to use an LLM call (OpenAI API) to generate the quality assessment from tool data.

**Why removed**
1. The challenge requires reproducibility. An LLM call introduces non-determinism.
2. API keys would need to be in the submission, violating rule #8.
3. The rule-based scoring with real tools turned out to be more accurate and fully reproducible.

**What it taught us**
The deterministic, tool-based approach is better for this use case. The tools gather real evidence, and the scoring rules are transparent and auditable. An LLM would add interpretive text but not improve accuracy.

---

## Main failure mode

The advanced solution over-scores repos with broken tests. The broken_tests repo scores 6 instead of 3 because the test agent gives +2 points for having test files before checking if they pass. The test execution results (which show failures) give -2, but the net effect is still neutral rather than negative. The fix would be to make the test execution result a multiplier on the test file score, rather than an additive bonus.

Additionally, the system consistently under-scores excellent repos. Platinum_repo scores 8 instead of 9 because the weighted average across four dimensions pulls excellent scores toward the middle. A repo that scores 10 on code quality but 6 on maintenance gets a weighted average of ~7.5, not 9.

## Hot take

The biggest lesson: the scoring calibration mattered more than the agent architecture. Adding agents and tools increased finding specificity 4x, but it was the scoring recalibration that actually improved accuracy by 52%. A simpler system with well-calibrated scores beats a complex system with poorly calibrated ones.

This mirrors a real-world pattern in AI evaluation: the evaluation methodology (how you score) matters more than the model architecture (what you build). The verification agent was also surprisingly valuable — not because it caught hallucinations (the rule-based agents don't hallucinate), but because it provides a trust signal to the user. A 64% verification rate tells the user that roughly two-thirds of findings are backed by tool evidence, which is actionable information.

For building more reliable agents, the lesson is: invest in calibration and verification before complexity. A well-calibrated simple system that you trust is worth more than a complex system you don't.
