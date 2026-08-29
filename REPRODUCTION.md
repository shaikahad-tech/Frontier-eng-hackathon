# Reproduction Guide

This guide is written for someone starting from a clean environment. It walks through setup, running the solution, running the baseline, and running the evaluation.

## Prerequisites

- Python 3.12+
- Git (for git history analysis tool)
- pip (Python package installer)

## Setup

```bash
# 1. Clone or unpack the repository
cd repo-assess

# 2. Install dependencies
pip install -r requirements.txt
```

Dependencies:
- `pytest` (for running test suites in analyzed repos and for the project's own tests)
- All other tools use only the Python standard library

No API keys are required. The solution is fully deterministic and reproducible.

## Data required

No external data is needed. The 12 test repositories are generated synthetically by `src/generate_test_repos.py`. Each repository is a small Python project with known quality characteristics.

The ground truth scores are defined in `src/generate_test_repos.py` in the `GROUND_TRUTH` dictionary and saved to `test_repos/ground_truth.json`.

## Generate test repositories

```bash
python -m src.generate_test_repos
```

This creates 12 test repositories in `test_repos/`:

| Repo | Score | Description |
|---|---|---|
| `platinum_repo` | 9 | Excellent: tests, docs, low complexity, Dockerfile |
| `good_with_tests` | 8 | Good quality with strong test suite |
| `well_documented` | 8 | Excellent docstrings and documentation |
| `no_tests` | 4 | Decent code but zero tests |
| `high_complexity` | 4 | Overly complex code, hard to maintain |
| `tech_debt_heavy` | 2 | TODOs, FIXMEs, hacks throughout |
| `no_readme` | 2 | Missing README, minimal code |
| `single_author` | 3 | Single contributor, low activity |
| `minimal_project` | 1 | Bare minimum, almost empty |
| `dependency_heavy` | 3 | 30+ dependencies, no tests |
| `mixed_quality` | 5 | Some good, some bad — the challenging case |
| `broken_tests` | 3 | Tests exist but are deliberately broken |

Each repository is initialized as a git repo with multiple commits and tags.

## Run the full evaluation (baseline vs advanced)

```bash
python -m src.evaluate
```

This runs both the baseline and advanced solutions on all 12 test repos and prints a comparison table. Results are saved to:
- `evaluation/full_results.json` — complete results for every repo
- `evaluation/report.json` — summary metrics
- `evaluation/report.md` — human-readable markdown report

### Expected output

```
======================================================================
EVALUATION SUMMARY
======================================================================
Total test repositories: 12

PRIMARY METRIC: Mean Absolute Error (score accuracy)
  Baseline MAE:  1.92
  Advanced MAE:  0.92
  Improvement:   1.0 (52.2%)

Ranking accuracy:
  Baseline:  0.697
  Advanced:  0.864

Finding specificity:
  Baseline:  42 findings
  Advanced:  175 findings

Recommendation accuracy:
  Baseline:  6/12 (50.0%)
  Advanced:  10/12 (83.3%)
```

## Run the baseline on a single repo

```bash
python -m src.baseline test_repos/platinum_repo
```

Output: JSON assessment with overall_score, quality_tier, strengths, weaknesses, recommendation, and confidence.

## Run the advanced solution on a single repo

```bash
python -m src.advanced test_repos/platinum_repo
```

Output: JSON assessment with dimension scores, evidence-backed findings, verification results, and overall recommendation.

## Run on any repository

```bash
# Clone a real repo
git clone https://github.com/psf/requests /tmp/requests

# Assess it
python -m src.advanced /tmp/requests
python -m src.baseline /tmp/requests
```

## Run the test suite

```bash
pytest tests/ -v
```

Expected: 45 tests pass, covering tools, baseline, advanced, edge cases, and trajectory logging.

## Agent trajectories

Every run produces trajectory logs in `trajectories/`:
- `baseline_<timestamp>.json` — baseline agent trajectory
- `advanced_orchestrator_<timestamp>.json` — orchestrator trajectory
- `advanced_structure_<timestamp>.json` — structure agent trajectory
- `advanced_test_<timestamp>.json` — test agent trajectory
- `advanced_code_quality_<timestamp>.json` — code quality agent trajectory
- `advanced_maintenance_<timestamp>.json` — maintenance agent trajectory

Each trajectory contains:
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
- OS: Linux/macOS (Windows should work but is untested)

## Runtime and cost

- Generate test repos: ~5 seconds
- Full evaluation (12 repos, baseline + advanced): ~30 seconds
- Single repo assessment (advanced): ~2 seconds
- Single repo assessment (baseline): ~0.01 seconds
- Cost: $0 (no API calls, fully local)

## Verifying the main result

To verify the main result from a clean environment:

```bash
pip install -r requirements.txt
python -m src.generate_test_repos
python -m src.evaluate
```

The evaluation output should show:
- Baseline MAE: ~1.92
- Advanced MAE: ~0.92
- Improvement: ~52.2%

If the numbers match, the result is reproduced.
