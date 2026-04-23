"""Core classes for SwarmKit: Agent, Task, and Swarm."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

from swarmkit.config import SwarmConfig
from swarmkit.utils import (
    aggregate_results,
    match_agent_to_task,
    plurality_vote,
    weighted_consensus,
)

logger = logging.getLogger(__name__)


class Agent(BaseModel):
    """An individual agent in the swarm.

    Each agent has a name, a role describing its purpose, and a list of
    capabilities that determine which tasks it can handle.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    role: str
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    _inbox: list[str] = []

    class Config:
        arbitrary_types_allowed = True

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "_inbox", [])

    def receive(self, message: str) -> None:
        """Receive a broadcast message."""
        self._inbox.append(message)
        logger.debug("Agent %s received message: %s", self.name, message)

    def get_messages(self) -> list[str]:
        """Return and clear the inbox."""
        messages = list(self._inbox)
        self._inbox.clear()
        return messages

    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute a task and return a result dict.

        Subclasses can override this to implement real work (e.g. calling an
        LLM).  The default implementation simulates task completion.
        """
        logger.info("Agent %s executing task: %s", self.name, task.description)
        await asyncio.sleep(0)  # yield control
        return {
            "agent": self.name,
            "agent_id": self.id,
            "task": task.description,
            "task_id": task.id,
            "status": "completed",
        }

    async def cast_vote(self, options: list[str]) -> str:
        """Cast a vote for one of the given options.

        Default implementation picks the first option whose name shares a
        substring with any of the agent's capabilities; otherwise picks the
        first option.  Override for smarter voting.
        """
        await asyncio.sleep(0)
        for option in options:
            for cap in self.capabilities:
                if cap.lower() in option.lower() or option.lower() in cap.lower():
                    return option
        # Deterministic fallback: hash agent id to pick
        idx = hash(self.id) % len(options)
        return options[idx]

    async def evaluate_proposal(self, proposal: str) -> float:
        """Return a score between 0.0 and 1.0 for a proposal.

        Default scores based on keyword overlap with capabilities.
        """
        await asyncio.sleep(0)
        words = set(proposal.lower().split())
        cap_words = {w.lower() for cap in self.capabilities for w in cap.split()}
        if not cap_words:
            return 0.5
        overlap = len(words & cap_words)
        return min(1.0, 0.3 + 0.2 * overlap)

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, role={self.role!r}, capabilities={self.capabilities})"


class Task(BaseModel):
    """A unit of work to be executed by an agent in the swarm."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str
    requirements: list[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=10)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Task(description={self.description!r}, requirements={self.requirements})"


class Swarm(BaseModel):
    """Orchestrates a group of agents to collaboratively solve tasks.

    Provides methods for task assignment, voting, consensus building,
    broadcasting, and result collection.
    """

    agents: list[Agent] = Field(default_factory=list)
    config: SwarmConfig = Field(default_factory=SwarmConfig)
    _results: list[dict[str, Any]] = []

    class Config:
        arbitrary_types_allowed = True

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "_results", [])

    # ── Agent management ─────────────────────────────────────────────

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the swarm."""
        if len(self.agents) >= self.config.max_agents:
            raise ValueError(
                f"Swarm has reached max capacity ({self.config.max_agents} agents)"
            )
        self.agents.append(agent)
        logger.info("Added agent %s to swarm (total: %d)", agent.name, len(self.agents))

    def remove_agent(self, agent_name: str) -> Agent:
        """Remove and return an agent by name.  Raises ValueError if not found."""
        for i, agent in enumerate(self.agents):
            if agent.name == agent_name:
                removed = self.agents.pop(i)
                logger.info("Removed agent %s from swarm", removed.name)
                return removed
        raise ValueError(f"Agent '{agent_name}' not found in swarm")

    # ── Task assignment ──────────────────────────────────────────────

    def assign_task(self, task: Task) -> Agent:
        """Find the best agent for a task based on capability matching.

        Returns the assigned Agent.  Raises ValueError if no suitable agent
        is found.
        """
        if not self.agents:
            raise ValueError("Swarm has no agents")

        best_agent = match_agent_to_task(self.agents, task)
        if best_agent is None:
            raise ValueError(
                f"No agent has capabilities matching task requirements: {task.requirements}"
            )
        logger.info("Assigned task '%s' to agent %s", task.description, best_agent.name)
        return best_agent

    # ── Execution ────────────────────────────────────────────────────

    async def run(self, tasks: list[Task]) -> list[dict[str, Any]]:
        """Run a list of tasks across the swarm concurrently.

        Each task is matched to the best-fit agent.  Tasks whose requirements
        cannot be matched are skipped with a warning.  Returns a list of
        result dicts.
        """
        coros: list[asyncio.Task[dict[str, Any]]] = []
        for task in sorted(tasks, key=lambda t: t.priority, reverse=True):
            try:
                agent = self.assign_task(task)
            except ValueError as exc:
                logger.warning("Skipping task '%s': %s", task.description, exc)
                continue
            coros.append(asyncio.create_task(agent.execute(task)))

        results = await asyncio.gather(*coros, return_exceptions=True)
        collected: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, BaseException):
                logger.error("Task failed: %s", r)
                collected.append({"status": "error", "error": str(r)})
            else:
                collected.append(r)

        self._results.extend(collected)
        return collected

    # ── Voting ───────────────────────────────────────────────────────

    async def vote(self, options: list[str]) -> str:
        """Have all agents vote and return the winning option (plurality)."""
        if not options:
            raise ValueError("No options provided for voting")
        if not self.agents:
            raise ValueError("Swarm has no agents to vote")

        votes: list[str] = await asyncio.gather(
            *(agent.cast_vote(options) for agent in self.agents)
        )
        winner = plurality_vote(votes, options)
        logger.info("Vote result: %s (from %d votes)", winner, len(votes))
        return winner

    # ── Consensus ────────────────────────────────────────────────────

    async def consensus(self, proposals: list[str]) -> dict[str, Any]:
        """Evaluate proposals and return the one with highest consensus.

        Each agent scores every proposal 0.0-1.0.  The proposal whose average
        score exceeds the configured threshold AND is highest wins.
        """
        if not proposals:
            raise ValueError("No proposals provided")
        if not self.agents:
            raise ValueError("Swarm has no agents")

        scores: dict[str, list[float]] = {p: [] for p in proposals}
        for proposal in proposals:
            agent_scores = await asyncio.gather(
                *(agent.evaluate_proposal(proposal) for agent in self.agents)
            )
            scores[proposal] = list(agent_scores)

        return weighted_consensus(scores, self.config.consensus_threshold)

    # ── Communication ────────────────────────────────────────────────

    def broadcast(self, message: str) -> int:
        """Send a message to every agent in the swarm.  Returns agent count."""
        for agent in self.agents:
            agent.receive(message)
        logger.info("Broadcast to %d agents: %s", len(self.agents), message)
        return len(self.agents)

    # ── Results ──────────────────────────────────────────────────────

    def collect_results(self) -> list[dict[str, Any]]:
        """Return all accumulated results and clear the internal store."""
        results = aggregate_results(list(self._results))
        self._results.clear()
        return results

    def __repr__(self) -> str:
        return f"Swarm(agents={len(self.agents)}, config={self.config})"
