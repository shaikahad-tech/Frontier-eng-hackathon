# RepoAssess — Agentic Repository Quality Assessment

## Who has this problem?

Engineering teams and technical buyers who need to evaluate code repositories for adoption, purchase, or integration. When a team considers adopting an open-source library, purchasing a proprietary codebase, or bringing in a third-party dependency, they need to quickly and reliably assess code quality before committing.

## The bottleneck

A README file or working demo reveals little about actual code quality. The buyer must understand an unfamiliar codebase: run the build and tests, inspect the architecture and dependencies, assess technical debt and maintenance risks. Relevant evidence is spread across the code itself, test coverage, dependency manifests, and git history. Without a repeatable method, the valuation depends on incomplete or inconsistent judgment — one reviewer might weigh test coverage heavily while another focuses on documentation, and neither might check the git history for recent activity.

This problem matters because the cost of adopting a low-quality codebase is enormous: maintenance burden, security vulnerabilities, integration failures, and opportunity cost. A fast, reliable, evidence-backed assessment saves engineering time and reduces risk.

## What this solution does

RepoAssess is a multi-agent system that analyzes a code repository across four dimensions — structure, testing, code quality, and maintenance — using 10 real code analysis tools. Each specialist agent gathers evidence from the repository and produces findings with citations back to the tool data. A verification agent cross-checks the findings, and an orchestrator synthesizes a final quality report with a score, strengths, weaknesses, and recommendation.

The baseline solution (for comparison) reads only the README and file listing — representing what a person might do with a quick glance at the repository page.

## Key results

| Metric | Baseline | Advanced | Improvement |
|---|---|---|---|
| Score accuracy (MAE, lower is better) | 1.92 | 0.92 | 52.2% better |
| Ranking accuracy | 69.7% | 86.4% | +16.7pp |
| Total findings (specificity) | 42 | 175 | 4.2x more |
| Recommendation accuracy | 50.0% | 83.3% | +33.3pp |
| Verification rate | N/A | 63.8% | — |

Evaluated on 12 synthetic test repositories with known quality characteristics.

## Architecture

```
                    ┌─────────────────────┐
                    │   Orchestrator      │
                    │   Agent             │
                    └─────────┬───────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
  │ Structure Agent│ │ Test Agent     │ │ Code Quality   │
  │                │ │                │ │ Agent          │
  │ • README       │ │ • Test files   │ │ • Complexity    │
  │ • Dependencies │ │ • Run tests    │ │ • Tech debt    │
  │ • Project type │ │ • CI config    │ │ • Docstrings   │
  │ • Dockerfile   │ │ • Test ratio   │ │ • Security     │
  └────────────────┘ └────────────────┘ └────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
  │ Maintenance    │ │ Verification   │ │ Final Report   │
  │ Agent          │ │ Agent          │ │                │
  │ • Git history  │ │ • Cross-checks │ │ • Score 1-10   │
  │ • Contributors │ │   findings     │ │ • Tier         │
  │ • Recent commits│ │   vs raw data  │ │ • Evidence     │
  │ • Tags/releases│ │ • Flags unsupported│ • Recommendation│
  └────────────────┘ └────────────────┘ └────────────────┘
```

## Tools used by agents

| Tool | What it does |
|---|---|
| `read_readme` | Read README file content and metadata |
| `analyze_structure` | Directory structure, file types, project type |
| `analyze_dependencies` | Parse requirements.txt, pyproject.toml, package.json, Cargo.toml |
| `analyze_tests` | Count test files/functions, test-to-source ratio, CI config |
| `run_tests` | Execute the test suite with pytest |
| `analyze_complexity` | AST-based cyclomatic complexity of every function |
| `analyze_code_quality` | Comment ratio, TODO/FIXME/HACK markers, tech debt |
| `analyze_documentation` | Docstrings, LICENSE, CONTRIBUTING, CHANGELOG |
| `analyze_git_history` | Commit count, contributors, recent activity, tags |
| `analyze_security` | Bare except, eval, exec, hardcoded secrets, shell=True |

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Generate test repositories (12 repos with known quality)
python -m src.generate_test_repos

# Run the full evaluation (baseline vs advanced)
python -m src.evaluate

# Assess a single repository with the advanced solution
python -m src.advanced /path/to/repo

# Assess a single repository with the baseline
python -m src.baseline /path/to/repo

# Run the test suite
pytest tests/ -v
```

See [REPRODUCTION.md](REPRODUCTION.md) for the full reproduction guide.

## Project structure

```
repo-assess/
├── src/
│   ├── trajectory_logger.py      # Agent trajectory logging (deliverable #4)
│   ├── baseline.py               # Baseline: single-prompt assessment
│   ├── advanced.py               # Advanced: multi-agent with tools + verification
│   ├── evaluate.py               # Evaluation framework
│   ├── generate_test_repos.py    # Test case generation (12 repos)
│   ├── tools/
│   │   └── repo_tools.py         # 10 code analysis tools
│   └── agents/                   # Agent modules (agents live in advanced.py)
├── tests/
│   └── test_all.py               # 45 tests covering all components
├── test_repos/                   # 12 synthetic repos with known quality
├── trajectories/                 # Agent trajectory logs (JSON)
├── evaluation/                   # Evaluation results and reports
├── requirements.txt
├── README.md
├── IMPROVEMENT_CHANGELOG.md
└── REPRODUCTION.md
```

## Agent trajectories

Every agent run produces a structured JSON trajectory in `trajectories/` that captures:
- The instruction the agent received
- Each tool call with inputs and outputs
- The agent's reasoning (thoughts)
- Feedback and retries
- The final result

See the `trajectories/` directory for representative trajectories from each agent.

## Coding agent disclosure

This project was built using Sarvam AI's coding assistant as the agent. The agent was instructed to:
1. Analyze the hackathon problem statement
2. Design a multi-agent repository quality assessment system
3. Build the baseline and advanced solutions
4. Create 12 test cases with known quality characteristics
5. Build the evaluation framework
6. Write all documentation deliverables
7. Audit every file for bugs and refine all components

The agent used Python as the implementation language. No external LLM API calls were made — the agents use rule-based scoring with real code analysis tools, making the solution fully reproducible without API keys.
