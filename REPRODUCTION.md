# Reproduction Guide

## Prerequisites

- Python 3.12+
- Git
- pytest

## Setup

```bash
git clone https://github.com/shaikahad-tech/Frontier-eng-hackathon.git
cd Frontier-eng-hackathon
pip install -r requirements.txt
```

## Run the Benchmark

```bash
# Full benchmark suite (25 repos, 10 steps)
python repoassess.py benchmark --output results.json

# Or programmatically
python -c "
from src.phase5.benchmark import run_full_benchmark
results = run_full_benchmark(verbose=True)
print(f'Repos: {results[\"benchmark\"][\"repo_count\"]}')
"
```

## Analyze a Repository

```bash
# Executive report
python repoassess.py analyze /path/to/repo --format executive

# Detailed engineering report
python repoassess.py analyze /path/to/repo --format engineering

# JSON output
python repoassess.py analyze /path/to/repo --format json --output report.json
```

## Run Tests

```bash
python -m pytest tests/test_comprehensive.py -v
```

## Verify Verification Affects Scores

```python
from src.phase4.orchestrator import evaluate_advanced, evaluate_advanced_no_verification

# With verification
result_v = evaluate_advanced("/path/to/repo")
print(f"With verification: {result_v['score']}")

# Without verification (ablation)
result_nv = evaluate_advanced_no_verification("/path/to/repo")
print(f"Without verification: {result_nv['score']}")

# The scores should differ
print(f"Difference: {result_v['score'] - result_nv['score']}")
```

## Benchmark Structure

1. 25 synthetic repos generated with known ground truth
2. Baseline (Phase 3) and Advanced (Phase 4) evaluations
3. Metrics: MAE, RMSE, Spearman, Pearson, Pairwise Accuracy
4. Ablation: remove each component and measure impact
5. Weight sensitivity: 4 different weight configurations
6. Invariance: modify irrelevant properties, verify stable scores
7. Causal sensitivity: add secrets/failing tests, verify score drops
8. Mutation testing: inject mutations, measure detection rate
9. Monotonicity: add quality features, verify score increases
10. Counterfactual: remove components, verify score drops

## No External Dependencies

The entire benchmark runs without any LLM API or external service. All analysis is deterministic and reproducible.
