# Reproduction Guide

This guide is written for someone starting from a clean environment. It walks through setup, running both Phase 1 and Phase 2, running the evaluation, and verifying results.

## Prerequisites

- Python 3.12+
- Git (for git history analysis tool)
- pip (Python package installer)

## Setup

```bash
cd repo-assess
pip install -r requirements.txt
```

Dependencies:
- `pytest` (for running test suites in analyzed repos and for the project's own tests)
- All other tools use only the Python standard library

No API keys are required. The solution is fully deterministic and reproducible.

## Data required

No external data is needed. The 12 test repositories are generated synthetically by `src/generate_test_repos.py`.

## Generate test repositories

```bash
python -m src.generate_test_repos
```

This creates 12 test repositories in `test_repos/` with known quality characteristics.

## Phase 1: Run the evaluation (baseline vs advanced)

```bash
python -m src.evaluate
```

Expected output:
```
Baseline MAE:  1.92
Advanced MAE:  0.92
Improvement:   1.0 (52.2%)
```

## Phase 1: Assess a single repo

```bash
python -m src.advanced test_repos/platinum_repo
python -m src.baseline test_repos/platinum_repo
```

## Phase 2: Run the production-grade pipeline

```bash
# Run the full Phase 2 analysis
python -m src.phase2.pipeline test_repos/platinum_repo

# Save reports to a specific directory
python -m src.phase2.pipeline test_repos/platinum_repo --output phase2_reports

# Run sequentially (for debugging)
python -m src.phase2.pipeline test_repos/platinum_repo --sequential

# Quiet mode
python -m src.phase2.pipeline test_repos/platinum_repo --quiet
```

Phase 2 produces three reports:
- `phase2_output/executive_report.md` — executive summary with top risks and strengths
- `phase2_output/engineering_report.md` — detailed findings with evidence, CWE/OWASP mappings
- `phase2_output/machine_report.json` — strict JSON for downstream processing

## Phase 2: Quality gate check (CI/CD integration)

```bash
# First generate the machine report
python -m src.phase2.pipeline /path/to/repo --output reports

# Then check quality gates
python -m src.phase2.gates reports/machine_report.json --min-score 70 --no-critical

# Exit codes: 0=pass, 1=gate failed, 2=analyzer error, 3=invalid config
```

## Phase 1 vs Phase 2 comparison

To reproduce the comparison data from the README:

```bash
# Generate test repos
python -m src.generate_test_repos

# Run Phase 1 evaluation
python -m src.evaluate

# Run Phase 2 on each test repo
for repo in test_repos/*/; do
    python -m src.phase2.pipeline "$repo" --quiet --output "phase2_output/$(basename $repo)"
done
```

## Run the test suite

```bash
pytest tests/ -v
```

Expected: 65 tests pass (45 Phase 1 + 20 Phase 2).

## Agent trajectories

Every Phase 1 agent run produces trajectory logs in `trajectories/`. Each trajectory contains:
- Agent name and start time
- Instructions received
- Every tool call with inputs and outputs
- Agent thoughts (reasoning)
- Feedback and retries
- Final result

## Versions

- Python: 3.12
- pytest: 8.0+
- Git: 2.39+
- OS: Linux/macOS

## Runtime and cost

| Operation | Time | Cost |
|---|---|---|
| Generate test repos | ~5s | $0 |
| Phase 1 full evaluation (12 repos) | ~30s | $0 |
| Phase 2 single repo analysis | ~0.14s | $0 |
| Phase 1 single repo (advanced) | ~2.6s | $0 |
| Phase 1 single repo (baseline) | ~0.01s | $0 |

## Verifying the main result

```bash
pip install -r requirements.txt
python -m src.generate_test_repos
python -m src.evaluate
pytest tests/ -v
```

The evaluation output should show:
- Baseline MAE: ~1.92
- Advanced MAE: ~0.92
- Improvement: ~52.2%
- 65 tests passing
