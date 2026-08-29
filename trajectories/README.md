# Sample Agent Trajectories

This directory contains representative trajectory logs from each agent type.
When you run the evaluation (`python -m src.evaluate`), full trajectory JSON
files are generated here automatically.

## Trajectory format

Each trajectory is a JSON file with:
- `agent_name` — which agent produced this trajectory
- `started_at` / `saved_at` — timestamps
- `instructions` — the prompt/instruction the agent received
- `total_steps` — number of steps recorded
- `steps` — array of step objects, each with a type:
  - `instruction` — the initial task given to the agent
  - `tool_call` — a tool was called (includes tool name, inputs, output)
  - `thought` — the agent's reasoning between tool calls
  - `feedback` — self-correction or verification feedback
  - `retry` — a failed step was retried
  - `human_checkpoint` — a human-in-the-loop decision point
  - `result` — the final result/output of the agent

## Agent types

| Agent | Typical steps | Tools used |
|---|---|---|
| `baseline` | 6 | read_readme, analyze_structure |
| `advanced_orchestrator` | 13 | coordinates all agents |
| `advanced_structure` | 5 | read_readme, analyze_structure, analyze_dependencies |
| `advanced_test` | 4 | analyze_tests, run_tests |
| `advanced_code_quality` | 6 | analyze_complexity, analyze_code_quality, analyze_documentation, analyze_security |
| `advanced_maintenance` | 3 | analyze_git_history |

## Generating trajectories

```bash
# Generate test repos and run evaluation to produce trajectories
python -m src.generate_test_repos
python -m src.evaluate

# Or run on a single repo
python -m src.advanced test_repos/platinum_repo
python -m src.baseline test_repos/platinum_repo
```

Each run produces trajectory files named `{agent_name}_{timestamp}.json`.
