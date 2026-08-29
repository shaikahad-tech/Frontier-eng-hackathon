"""
Trajectory logger — captures every agent action, tool call, and response
for submission as required by the hackathon (deliverable #4: Agent trajectories).

Each trajectory is a structured JSON log of:
- The agent's name and role
- The instructions it received
- Each step: tool calls, inputs, outputs, and any feedback
- Retries and human checkpoints
- Final result

Usage:
    logger = TrajectoryLogger("baseline")
    logger.log_instruction("Analyze repo X")
    logger.log_tool_call("run_tests", {"repo_path": "/path"}, {"pass": 5, "fail": 2})
    logger.log_thought("Test coverage is low, this is a risk")
    logger.save()  # writes to trajectories/baseline_<timestamp>.json
"""

import json
import os
import datetime
from typing import Any, Optional


class TrajectoryLogger:
    def __init__(self, agent_name: str, trajectories_dir: str = "trajectories"):
        self.agent_name = agent_name
        self.trajectories_dir = trajectories_dir
        self.steps: list[dict] = []
        self.instructions: list[str] = []
        self.started_at = datetime.datetime.now(datetime.timezone.utc)
        os.makedirs(trajectories_dir, exist_ok=True)

    def log_instruction(self, instruction: str) -> None:
        """Log the initial instruction / prompt given to the agent."""
        entry = {
            "type": "instruction",
            "timestamp": self._now(),
            "content": instruction,
        }
        self.instructions.append(instruction)
        self.steps.append(entry)

    def log_thought(self, thought: str) -> None:
        """Log the agent's reasoning / thinking."""
        self.steps.append({
            "type": "thought",
            "timestamp": self._now(),
            "content": thought,
        })

    def log_tool_call(
        self,
        tool_name: str,
        inputs: dict,
        output: Any,
        error: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Log a tool call with its inputs and outputs."""
        entry = {
            "type": "tool_call",
            "timestamp": self._now(),
            "tool": tool_name,
            "inputs": self._safe_serialize(inputs),
            "output": self._safe_serialize(output),
        }
        if error:
            entry["error"] = error
        if duration_seconds is not None:
            entry["duration_seconds"] = round(duration_seconds, 3)
        self.steps.append(entry)

    def log_feedback(self, feedback: str, source: str = "self") -> None:
        """Log feedback that shaped the next step (self-correction, verification, human checkpoint)."""
        self.steps.append({
            "type": "feedback",
            "timestamp": self._now(),
            "source": source,
            "content": feedback,
        })

    def log_retry(self, reason: str, attempt: int) -> None:
        """Log a retry of a failed step."""
        self.steps.append({
            "type": "retry",
            "timestamp": self._now(),
            "reason": reason,
            "attempt": attempt,
        })

    def log_human_checkpoint(self, description: str, decision: str) -> None:
        """Log a human-in-the-loop checkpoint."""
        self.steps.append({
            "type": "human_checkpoint",
            "timestamp": self._now(),
            "description": description,
            "decision": decision,
        })

    def log_result(self, result: Any) -> None:
        """Log the final result of the agent."""
        self.steps.append({
            "type": "result",
            "timestamp": self._now(),
            "content": self._safe_serialize(result),
        })

    def save(self, suffix: str = "") -> str:
        """Save the trajectory to a JSON file. Returns the file path."""
        timestamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.agent_name}_{timestamp}{suffix}.json"
        filepath = os.path.join(self.trajectories_dir, filename)

        # Handle filename collisions (if saved twice in same second)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{self.agent_name}_{timestamp}_{counter}{suffix}.json"
            filepath = os.path.join(self.trajectories_dir, filename)
            counter += 1

        trajectory = {
            "agent_name": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "instructions": self.instructions,
            "total_steps": len(self.steps),
            "steps": self.steps,
        }

        with open(filepath, "w") as f:
            json.dump(trajectory, f, indent=2, default=str)

        return filepath

    def _now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _safe_serialize(self, obj: Any) -> Any:
        """Make an object JSON-serializable."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._safe_serialize(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self._safe_serialize(v) for k, v in obj.items()}
        # For everything else, convert to string, truncating long values
        s = str(obj)
        if len(s) > 2000:
            s = s[:2000] + "...[truncated]"
        return s
