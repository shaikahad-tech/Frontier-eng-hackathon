# Video Script — RepoAssess Demo

## Target duration: 4-5 minutes

---

### [0:00] Problem Statement (30s)

**Narration:**
"Engineering teams need to assess code repositories for adoption, purchase, or integration. But a README reveals little about actual code quality. You need to understand the codebase: run tests, inspect architecture, check dependencies, assess security. Without a repeatable method, the assessment depends on incomplete judgment."

**Screen:** Show a GitHub repo page with a nice README, then reveal that the code has no tests, security issues, and no CI.

---

### [0:30] Phase 1: Baseline vs Advanced (60s)

**Narration:**
"We built a multi-agent system called RepoAssess. The baseline solution reads only the README — like glancing at the repo page. The advanced solution uses 10 real code analysis tools across 4 specialist agents, with a verification agent that cross-checks findings."

**Screen:** Run the evaluation
```bash
python -m src.generate_test_repos
python -m src.evaluate
```

**Highlight:** Show the evaluation output:
- Baseline MAE: 1.92
- Advanced MAE: 0.92
- 52.2% improvement
- 4.2x more findings

---

### [1:30] Phase 1: Single Repo Demo (30s)

**Narration:**
"Let's see it in action on a single repository."

**Screen:**
```bash
python -m src.advanced test_repos/platinum_repo
```

Show the JSON output with dimension scores, findings, and recommendation.

---

### [2:00] Phase 2: Production-Grade Platform (90s)

**Narration:**
"Phase 2 upgrades RepoAssess to a production-grade engineering intelligence platform with 12 analyzers covering 10 scoring dimensions. It adds hard gates that cap scores when critical issues are found, letter grades from A+ to F, maturity levels from 0 to 5, and three report formats."

**Screen:**
```bash
python -m src.phase2.pipeline test_repos/platinum_repo
```

Show the output:
- Overall score with grade (e.g., 63/100, C+, Level 2)
- Hard gates triggered (if any)
- Category scores across 10 dimensions
- Findings count by severity

Then show the generated reports:
```bash
cat phase2_output/executive_report.md
```

Show the executive report with top risks, strengths, and category scores table.

```bash
cat phase2_output/engineering_report.md | head -50
```

Show the engineering report with detailed findings, CWE/OWASP mappings, and evidence.

---

### [3:30] Phase 2: CI/CD Integration (30s)

**Narration:**
"Phase 2 is designed for CI/CD integration. Quality gates with deterministic exit codes let you block deployments on critical issues."

**Screen:**
```bash
python -m src.phase2.gates phase2_output/machine_report.json --min-score 70 --no-critical
```

Show the gate check output and exit code.

---

### [4:00] Comparison and Results (60s)

**Narration:**
"Here's the comparison. Phase 1 achieved 52.2% MAE improvement over the baseline. Phase 2 adds 10 scoring dimensions, 5 hard gates, structured findings with CWE/OWASP mappings, 3 report formats, CI exit codes, and runs 19x faster — making it suitable for production CI/CD pipelines."

**Screen:** Show the comparison table:
- Baseline MAE: 19.2, Phase 1: 9.2, Phase 2: 15.2
- Phase 2 produces 61 structured findings with hard gates
- Phase 2 runs in 0.14s per repo

---

### [4:30] Conclusion (30s)

**Narration:**
"RepoAssess demonstrates how a multi-agent system with real code analysis tools can produce evidence-backed repository quality assessments. Phase 2 takes it to production with hard gates, CI integration, and structured reporting. The solution is fully deterministic, requires no API keys, and runs in under 200ms per repo."

**Screen:** Show the GitHub repo URL and the test results (65 tests passing).

---

## Key points to emphasize

1. **Evidence over assumptions**: Every finding has file/line references, evidence, and confidence
2. **Hard gates**: Critical security issues cap the score at 59 regardless of other dimensions
3. **Structured output**: Findings have id, severity, confidence, CWE/OWASP mappings
4. **Speed**: Phase 2 runs in 0.14s per repo — 19x faster than Phase 1
5. **Deterministic**: No API keys, fully reproducible, no LLM hallucination risk
6. **CI-ready**: Exit codes for quality gate integration
