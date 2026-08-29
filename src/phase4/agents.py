"""Phase 4 — Agents Base: Data structures, scoring config, evidence collector, agent base class

Architecture:
    Repository → Phase 2 Tool Layer →
        Structure Agent ─┐
        Test Agent ─────┤
        Code Quality Agent ─┤
        Maintenance Agent ─┘
            → Verification Agent → Orchestrator → Final Evaluation

Agents operate from actual Phase 2 tool output, not invented facts.
"""
from __future__ import annotations
import os
import re
import json
import time
import math
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from collections import defaultdict

from src.phase2.schema import (
    Severity, Status, Finding, ToolResult, AnalyzerBase,
    ProjectProfile, register_analyzer,
)


@dataclass
class AgentFinding:
    """A finding from a specialist agent."""
    agent: str
    dimension: str
    claim: str
    score: float  # 0-10
    confidence: float  # 0-1
    evidence: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    status: str = "UNKNOWN"  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONTRADICTED, UNKNOWN


@dataclass
class AgentResult:
    """Result from a specialist agent."""
    agent_name: str
    dimension: str
    score: float  # 0-10
    confidence: float  # 0-1
    findings: list[AgentFinding] = field(default_factory=list)
    evidence_coverage: float = 0.0
    unknowns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of verifying a finding."""
    finding_id: str
    claim: str
    status: str  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONTRADICTED, UNKNOWN
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    verifier_notes: str = ""


# Default weights (treated as hypotheses — Phase 5 validates)
DEFAULT_WEIGHTS = {
    "testing": 0.25,
    "code_quality": 0.25,
    "structure": 0.20,
    "maintenance": 0.15,
    "documentation": 0.05,
    "dependencies": 0.10,
}

# Profile-specific weight adjustments
PROFILE_WEIGHTS = {
    "LIBRARY": {"structure": 0.25, "testing": 0.20, "code_quality": 0.20,
                "maintenance": 0.10, "documentation": 0.15, "dependencies": 0.10},
    "API": {"testing": 0.30, "code_quality": 0.25, "structure": 0.15,
            "maintenance": 0.10, "documentation": 0.05, "dependencies": 0.15},
    "BACKEND_SERVICE": {"testing": 0.30, "code_quality": 0.25, "structure": 0.15,
                       "maintenance": 0.10, "documentation": 0.05, "dependencies": 0.15},
    "CLI": {"testing": 0.25, "code_quality": 0.20, "structure": 0.20,
            "maintenance": 0.10, "documentation": 0.15, "dependencies": 0.10},
    "ML": {"testing": 0.15, "code_quality": 0.15, "structure": 0.20,
           "maintenance": 0.10, "documentation": 0.15, "dependencies": 0.10},
}

# Hard gate thresholds
HARD_GATES = {
    "critical_security": {"max_score": 30, "description": "Confirmed critical security finding"},
    "broken_build": {"max_score": 35, "description": "Build completely broken"},
    "failing_tests": {"max_score": 40, "description": "Mandatory tests fail"},
    "committed_secret": {"max_score": 25, "description": "Confirmed committed secret"},
    "no_tests": {"max_score": 50, "description": "No tests at all"},
}


class EvidenceCollector:
    """Collects Phase 2 analyzer results for agent consumption."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.results: dict[str, ToolResult] = {}
        self.context: dict[str, Any] = {}
        self.errors: list[str] = []

    def collect(self) -> dict[str, Any]:
        """Run Phase 2 pipeline and collect all evidence."""
        try:
            from src.phase2.pipeline import Pipeline
            pipeline = Pipeline(self.repo_path)
            report = pipeline.run()

            for tool_result in report.get("tool_results", []):
                tool_name = tool_result.get("tool_name", "unknown")
                self.results[tool_name] = tool_result

            self.context = report.get("context", {})
            self.errors = report.get("errors", [])

            return {"results": self.results, "context": self.context,
                    "errors": self.errors, "summary": report.get("summary", {})}
        except Exception as e:
            self.errors.append(f"Evidence collection failed: {e}")
            return {"results": {}, "context": {}, "errors": self.errors, "summary": {}}

    def get_metric(self, analyzer_id: str, metric_name: str, default=None):
        """Get a specific metric from an analyzer's results."""
        for tool_name, result in self.results.items():
            if analyzer_id in tool_name.lower() or tool_name == analyzer_id:
                metrics = result.get("metrics", {})
                if metric_name in metrics:
                    return metrics[metric_name]
        for tool_name, result in self.results.items():
            raw = result.get("raw_data", {})
            if analyzer_id in raw:
                return result.get("metrics", {}).get(metric_name, default)
        for tool_name, result in self.results.items():
            metrics = result.get("metrics", {})
            if metric_name in metrics:
                return metrics[metric_name]
        return default

    def get_findings(self, analyzer_id: str = None) -> list[dict]:
        """Get findings from one or all analyzers."""
        findings = []
        for tool_name, result in self.results.items():
            if analyzer_id:
                raw = result.get("raw_data", {})
                if analyzer_id not in tool_name.lower() and analyzer_id not in raw:
                    continue
            for f in result.get("findings", []):
                findings.append(f)
        return findings

    def get_raw_data(self, analyzer_id: str) -> dict:
        """Get raw data from an analyzer."""
        for tool_name, result in self.results.items():
            raw = result.get("raw_data", {})
            if analyzer_id in tool_name.lower():
                return raw.get(analyzer_id, raw)
            if analyzer_id in raw:
                return raw[analyzer_id]
        return {}


class SpecialistAgent:
    """Base class for specialist agents."""

    AGENT_NAME: str = "base"
    DIMENSION: str = "unknown"
    ALLOWED_ANALYZERS: list[str] = []

    def __init__(self, evidence: EvidenceCollector):
        self.evidence = evidence
        self.findings: list[AgentFinding] = []
        self.unknowns: list[str] = []

    def _get_metric(self, analyzer_id: str, metric: str, default=None):
        return self.evidence.get_metric(analyzer_id, metric, default)

    def _get_findings(self, analyzer_id: str = None) -> list[dict]:
        return self.evidence.get_findings(analyzer_id)

    def _get_raw_data(self, analyzer_id: str) -> dict:
        return self.evidence.get_raw_data(analyzer_id)

    def _get_context(self) -> dict:
        return self.evidence.context

    def _profile(self) -> str:
        return self._get_context().get("discovery", {}).get("project_profile", "UNKNOWN")

    def _add_finding(self, claim: str, score: float, confidence: float,
                     evidence: list[dict] = None, sources: list[str] = None):
        self.findings.append(AgentFinding(
            agent=self.AGENT_NAME, dimension=self.DIMENSION, claim=claim,
            score=score, confidence=confidence, evidence=evidence or [], sources=sources or [],
        ))

    def _add_unknown(self, unknown: str):
        self.unknowns.append(unknown)

    def _evidence_coverage(self) -> float:
        """How much evidence this agent had access to."""
        if not self.ALLOWED_ANALYZERS:
            return 0.0
        available = 0
        for analyzer_id in self.ALLOWED_ANALYZERS:
            for tool_name, result in self.evidence.results.items():
                raw = result.get("raw_data", {})
                if analyzer_id in tool_name.lower() or analyzer_id in raw:
                    available += 1
                    break
        return available / len(self.ALLOWED_ANALYZERS)

    def evaluate(self) -> AgentResult:
        raise NotImplementedError
