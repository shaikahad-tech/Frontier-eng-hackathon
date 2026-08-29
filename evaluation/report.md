# Evaluation Report

## Primary Metric: Mean Absolute Error (score accuracy)

Lower is better. Measures how far the assessment score is from ground truth.

| | Baseline | Advanced | Change |
|---|---|---|---|
| MAE | 1.92 | 0.92 | 1.0 (52.2%) |

## Ranking Accuracy
| | Baseline | Advanced | Change |
|---|---|---|---|
| Concordant pairs | 69.7% | 86.4% | +16.7% |

## Finding Specificity
| | Baseline | Advanced | Change |
|---|---|---|---|
| Total findings | 42 | 175 | +133 |

## Verification Rate (advanced only)
63.8% of findings backed by tool evidence

## Recommendation Accuracy
| | Baseline | Advanced |
|---|---|---|
| Correct | 6/12 | 10/12 |
| Percentage | 50.0% | 83.3% |

## Per-Repository Comparison

| Repo | Truth | Baseline | Advanced | B-Error | A-Error | B-Findings | A-Findings |
|---|---|---|---|---|---|---|---|
| broken_tests | 3 | 5 | 6 | 2.0 | 3.0 | 3 | 15 |
| dependency_heavy | 3 | 5 | 3 | 2.0 | 0.0 | 3 | 14 |
| good_with_tests | 8 | 5 | 7 | 3.0 | 1.0 | 4 | 16 |
| high_complexity | 4 | 5 | 4 | 1.0 | 0.0 | 3 | 15 |
| minimal_project | 1 | 3 | 3 | 2.0 | 2.0 | 3 | 11 |
| mixed_quality | 5 | 5 | 6 | 0.0 | 1.0 | 4 | 14 |
| no_readme | 2 | 3 | 3 | 1.0 | 1.0 | 3 | 14 |
| no_tests | 4 | 5 | 4 | 1.0 | 0.0 | 3 | 13 |
| platinum_repo | 9 | 6 | 8 | 3.0 | 1.0 | 5 | 19 |
| single_author | 3 | 5 | 3 | 2.0 | 0.0 | 4 | 13 |
| tech_debt_heavy | 2 | 5 | 3 | 3.0 | 1.0 | 3 | 14 |
| well_documented | 8 | 5 | 7 | 3.0 | 1.0 | 4 | 17 |
