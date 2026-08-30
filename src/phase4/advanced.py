"""Phase 4 — Advanced Multi-Agent Evaluation Entry Point

Imports agents, specialists, verification, and orchestrator modules.

Architecture:
    Repository → Phase 2 Tool Layer →
        Structure Agent ─┐
        Test Agent ─────┤
        Code Quality Agent ─┤
        Maintenance Agent ─┘
            → Verification Agent → Orchestrator → Final Evaluation

Agents operate from actual Phase 2 tool output, not invented facts.
"""
from src.phase4.agents import (
    SpecialistAgent, EvidenceCollector,
    AgentFinding, AgentResult, DEFAULT_WEIGHTS, PROFILE_WEIGHTS, HARD_GATES,
)
from src.phase4.specialists import (
    StructureAgent, TestAgent, CodeQualityAgent, MaintenanceAgent,
)
from src.phase4.verification import VerificationAgent, VerificationResult
from src.phase4.orchestrator import (
    Orchestrator, evaluate_advanced, evaluate_advanced_no_verification,
    track_disagreements, VERIFICATION_WEIGHTS,
)

__all__ = [
    "SpecialistAgent", "EvidenceCollector",
    "AgentFinding", "AgentResult", "DEFAULT_WEIGHTS", "PROFILE_WEIGHTS", "HARD_GATES",
    "StructureAgent", "TestAgent", "CodeQualityAgent", "MaintenanceAgent",
    "VerificationAgent", "VerificationResult",
    "Orchestrator", "evaluate_advanced", "evaluate_advanced_no_verification",
    "track_disagreements", "VERIFICATION_WEIGHTS",
]
