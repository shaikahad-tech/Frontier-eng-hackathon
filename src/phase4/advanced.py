"""Phase 4 — Advanced Multi-Agent Evaluation Entry Point

Imports agents, verification, and orchestrator modules.

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
    SpecialistAgent, StructureAgent, TestAgent,
    CodeQualityAgent, MaintenanceAgent, EvidenceCollector,
    AgentFinding, AgentResult, DEFAULT_WEIGHTS, PROFILE_WEIGHTS, HARD_GATES,
)
from src.phase4.verification import VerificationAgent, VerificationResult
from src.phase4.orchestrator import Orchestrator, evaluate_advanced, track_disagreements
