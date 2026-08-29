"""
Phase 2 Core Schema — Finding schema, severity model, confidence levels,
analyzer base class, and registry.
"""
from __future__ import annotations
import time, uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

class Severity(str, Enum):
    CRITICAL = "critical"; HIGH = "high"; MEDIUM = "medium"; LOW = "low"; INFO = "info"

class Status(str, Enum):
    PASS = "PASS"; WARN = "WARN"; FAIL = "FAIL"; INFO = "INFO"
    UNKNOWN = "UNKNOWN"; NOT_APPLICABLE = "NOT_APPLICABLE"; NOT_RUN = "NOT_RUN"; ERROR = "ERROR"

class ProjectProfile(str, Enum):
    CLI = "CLI"; LIBRARY = "LIBRARY"; WEB_APP = "WEB_APP"; API = "API"
    BACKEND_SERVICE = "BACKEND_SERVICE"; FRONTEND = "FRONTEND"; DATA_SCIENCE = "DATA_SCIENCE"
    ML = "ML"; MONOREPO = "MONOREPO"; INFRASTRUCTURE = "INFRASTRUCTURE"
    SCRIPT = "SCRIPT"; EDUCATIONAL = "EDUCATIONAL"; EXPERIMENT = "EXPERIMENT"; UNKNOWN = "UNKNOWN"

@dataclass
class Finding:
    id: str; category: str; severity: str; status: str; title: str
    description: str = ""; confidence: float = 0.0
    files: list[dict] = field(default_factory=list)
    evidence: str = ""; impact: str = ""; recommendation: str = ""
    references: list[str] = field(default_factory=list)
    owasp_category: Optional[str] = None; cwe_id: Optional[str] = None
    primary_category: Optional[str] = None
    secondary_impacts: list[str] = field(default_factory=list)
    suppressed: bool = False; suppression_reason: Optional[str] = None
    def to_dict(self): return asdict(self)

@dataclass
class ToolResult:
    tool_name: str; status: str
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    raw_data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    analyzer_version: str = "2.0.0"
    repository_revision: Optional[str] = None
    def to_dict(self):
        return {"tool_name": self.tool_name, "status": self.status,
                "findings": [f.to_dict() for f in self.findings], "metrics": self.metrics,
                "raw_data": self.raw_data, "errors": self.errors,
                "execution_time_seconds": round(self.execution_time_seconds, 3),
                "analyzer_version": self.analyzer_version, "repository_revision": self.repository_revision}

class AnalyzerBase:
    ANALYZER_ID: str = ""; ANALYZER_NAME: str = ""; CATEGORY: str = ""
    REQUIRES: list[str] = []; SUPPORTS_PROFILES: list[str] = []; VERSION: str = "2.0.0"
    def __init__(self):
        self.findings: list[Finding] = []; self.metrics: dict[str, Any] = {}
        self.raw_data: dict[str, Any] = {}; self.errors: list[str] = []
    def analyze(self, repo_path: str, context: dict) -> ToolResult:
        raise NotImplementedError
    def _add_finding(self, f: Finding): self.findings.append(f)
    def _add_metric(self, k, v): self.metrics[k] = v
    def _set_raw_data(self, k, v): self.raw_data[k] = v
    def _error(self, msg): self.errors.append(msg)
    def _build_result(self, elapsed: float) -> ToolResult:
        if self.errors: status = Status.ERROR.value
        elif any(f.status == Status.FAIL.value for f in self.findings): status = Status.FAIL.value
        elif any(f.status == Status.WARN.value for f in self.findings): status = Status.WARN.value
        elif self.findings: status = Status.PASS.value
        else: status = Status.UNKNOWN.value
        return ToolResult(tool_name=self.ANALYZER_NAME, status=status, findings=self.findings,
                          metrics=self.metrics, raw_data=self.raw_data, errors=self.errors,
                          execution_time_seconds=elapsed, analyzer_version=self.VERSION)

class AnalyzerRegistry:
    _analyzers: dict[str, type[AnalyzerBase]] = {}
    _instances: dict[str, AnalyzerBase] = {}
    @classmethod
    def register(cls, ac): cls._analyzers[ac.ANALYZER_ID] = ac
    @classmethod
    def get_all(cls): return dict(cls._analyzers)
    @classmethod
    def get_applicable(cls, profile):
        return {k: v for k, v in cls._analyzers.items()
                if not v.SUPPORTS_PROFILES or profile in v.SUPPORTS_PROFILES}
    @classmethod
    def get_instance(cls, aid):
        if aid in cls._analyzers:
            return cls._analyzers[aid]()
        return None
    @classmethod
    def clear(cls): cls._analyzers.clear(); cls._instances.clear()

def register_analyzer(cls):
    AnalyzerRegistry.register(cls); return cls

def severity_weight(s):
    return {"critical": 100, "high": 50, "medium": 20, "low": 5, "info": 0}.get(s, 0)

def grade_from_score(score):
    if score >= 95: return "A+"
    elif score >= 85: return "A"
    elif score >= 75: return "B+"
    elif score >= 65: return "B"
    elif score >= 55: return "C+"
    elif score >= 45: return "C"
    elif score >= 30: return "D"
    else: return "F"

def maturity_from_score(score):
    if score >= 90: return 5
    elif score >= 75: return 4
    elif score >= 60: return 3
    elif score >= 40: return 2
    elif score >= 20: return 1
    else: return 0
