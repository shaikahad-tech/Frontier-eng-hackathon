# RepoAssess — Evidence-Backed Engineering Due Diligence

A multi-agent system that evaluates software repositories for engineering quality, producing evidence-backed scores with verification, remediation plans, and explainability.

## What It Does

RepoAssess analyzes a Git repository across four engineering dimensions — **testing**, **code quality**, **structure**, and **maintenance** — using a pipeline of 27 static analyzers, then produces a score (0-100) with:

- **Verification**: Every finding is verified against actual tool data. Claims that contradict tool evidence are flagged and penalized.
- **Evidence graph**: Full traceability from score → dimension → finding → tool → evidence → file → line.
- **Remediation plan**: Prioritized (P0/P1/P2/P3) actions with file locations and expected impact.
- **Score explainability**: Per-dimension breakdown of what drove the score up or down.
- **Known unknowns**: Explicit acknowledgment of what couldn't be evaluated.

## Architecture

```
Repository → Phase 2 Tool Layer (27 analyzers) →
    Structure Agent ─┐
    Test Agent ─────┤
    Code Quality Agent ─┤
    Maintenance Agent ─┘
        → Verification Agent (structured claim verification)
        → Orchestrator (weighted scoring, hard gates)
        → Final Report
```

### Verification Agent

The verification agent uses **structured claim verification** with 14 claim types. Each finding's claim is classified into a type (test_pass, test_fail, test_count, coverage, security_findings, etc.) and verified against actual Phase 2 tool data:

- **VERIFIED** (100% weight): Tool data confirms the claim
- **PARTIALLY_VERIFIED** (90%): Source ran but claim not fully cross-referenced
- **UNKNOWN** (95%): Can't verify — neutral stance
- **UNVERIFIED** (70%): No evidence references
- **CONTRADICTED** (30%): Tool data contradicts the claim

This means **verification affects the final score** — the system with verification produces different scores than without it.

### Hard Gates

Hard gates override the weighted average for critical issues:
- Critical security findings → score capped at 30
- Committed secrets → score capped at 25
- Failing tests → score capped at 40
- No tests at all → score capped at 50

## Installation

```bash
git clone https://github.com/shaikahad-tech/Frontier-eng-hackathon.git
cd Frontier-eng-hackathon
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Analyze a repository
python repoassess.py analyze /path/to/repo --format executive

# Get detailed engineering report
python repoassess.py analyze /path/to/repo --format engineering

# JSON output for CI/CD integration
python repoassess.py analyze /path/to/repo --format json --output report.json

# Use project profile (affects weights)
python repoassess.py analyze /path/to/repo --profile LIBRARY

# Run the full benchmark suite
python repoassess.py benchmark

# Gate check (exit code 0 = pass, 1 = fail)
python repoassess.py gate report.json --min-score 70
```

### Programmatic

```python
from src.phase4.orchestrator import evaluate_advanced

result = evaluate_advanced("/path/to/repo")
print(f"Score: {result['score']}/100")
print(f"Grade: {result['grade']}")
print(f"Recommendation: {result['recommendation']}")
print(f"Verification rate: {result['verification_rate']:.0%}")
```

### Benchmark

```python
from src.phase5.benchmark import run_full_benchmark

results = run_full_benchmark(verbose=True)
# 25 repos, 10-step benchmark suite
```

## Benchmark Results (25 repos)

| Metric | Baseline | Advanced | Change |
|--------|----------|----------|--------|
| MAE | 1.556 | 1.804 | +0.248 |
| Spearman | 0.149 | 0.367 | **+0.218** |
| Pearson | 0.312 | 0.478 | **+0.166** |
| Pairwise Accuracy | 0.546 | 0.648 | **+0.102** |

The advanced system shows significantly better **ranking correlation** (Spearman +146%, Pearson +53%, Pairwise +19%) despite more conservative absolute calibration.

### Benchmark Suite (10 steps)

1. Baseline vs Advanced evaluation (25 repos)
2. Ablation testing (remove each component)
3. Weight sensitivity (4 configurations)
4. Invariance testing (irrelevant changes → stable scores)
5. Causal sensitivity (secrets/failing tests → score drops)
6. Mutation testing (inject mutations → detection rate)
7. Monotonicity testing (add quality → score increases)
8. Counterfactual testing (remove components → score drops)
9. Verification metrics (aggregate rates)
10. Dashboard generation

## Project Structure

```
src/
├── phase2/          # Tool layer (27 analyzers, pipeline, scoring)
├── phase3/          # Baseline evaluator (2 tools, 0-10 scale)
├── phase4/          # Advanced multi-agent system
│   ├── agents.py        # Data structures, EvidenceCollector, base agent
│   ├── specialists.py   # Structure, Test, CodeQuality, Maintenance agents
│   ├── verification.py  # Structured claim verification (14 types)
│   ├── orchestrator.py  # Scoring, gates, evidence graph, remediation
│   └── advanced.py      # Entry point
├── phase5/          # Benchmark suite
│   ├── ground_truth.py  # 25 repos with known scores
│   ├── repos.py         # Repo generators (01-15)
│   ├── repos_adversarial.py  # Adversarial repos (06, 08-11, 14-15)
│   ├── repos_extended.py     # Extended repos (16-25)
│   └── benchmark.py     # Metrics, runner, validation tests
└── tools/           # Repository analysis tools
repoassess.py        # CLI
tests/               # Test suite (32 tests)
```

## Testing

```bash
# Run all tests
python -m pytest tests/test_comprehensive.py -v

# Run specific phase tests
python -m pytest tests/test_comprehensive.py::TestPhase4 -v
```

## CI

GitHub Actions workflow runs on every push and PR:
- Import verification (all phases)
- Smoke test (evaluate a sample repo)
- Test suite
- Benchmark (on main branch)

## Reproducibility

The entire benchmark runs without any LLM API. All analysis is deterministic:
- 25 synthetic repos with known ground truth
- 27 static analyzers (no external services)
- Deterministic scoring with configurable weights
- Verification uses rule-based claim checking

## Honest Assessment

### What Works
- **Ranking correlation** — Spearman improved from 0.149 to 0.367
- **Verification** — 58% average verification rate, contradicted findings penalized
- **Adversarial detection** — surface camouflage and fake quality repos correctly scored low
- **Causal sensitivity** — secrets and failing tests trigger hard gates
- **Invariance** — irrelevant changes don't affect scores

### Known Limitations
- **Absolute calibration** — scores are compressed (2.5-4.5 range) vs ground truth (2-9.5)
- **Phase 2 analyzers** — don't detect all positive signals (e.g., nested src/ directories)
- **Test execution** — only runs for repos with pytest detected

## License

MIT
