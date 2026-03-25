"""Configuration models for SwarmKit."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class SwarmConfig(BaseModel):
    """Global configuration for a Swarm instance."""

    max_agents: int = Field(
        default=int(os.getenv("SWARMKIT_MAX_AGENTS", "50")),
        ge=1,
        description="Maximum number of agents allowed in the swarm.",
    )
    task_timeout: int = Field(
        default=int(os.getenv("SWARMKIT_TASK_TIMEOUT", "30")),
        ge=1,
        description="Default timeout (seconds) for individual agent tasks.",
    )
    consensus_threshold: float = Field(
        default=float(os.getenv("SWARMKIT_CONSENSUS_THRESHOLD", "0.5")),
        ge=0.0,
        le=1.0,
        description="Minimum average score for a proposal to reach consensus.",
    )
    log_level: str = Field(
        default=os.getenv("SWARMKIT_LOG_LEVEL", "INFO"),
        description="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )

    def __repr__(self) -> str:
        return (
            f"SwarmConfig(max_agents={self.max_agents}, "
            f"timeout={self.task_timeout}s, "
            f"consensus={self.consensus_threshold})"
        )
