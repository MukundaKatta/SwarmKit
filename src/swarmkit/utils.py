"""Utility functions for SwarmKit.

Provides task matching, voting algorithms, and result aggregation helpers
used by the core Swarm class.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from swarmkit.core import Agent, Task


# ── Task Matching ────────────────────────────────────────────────────


def capability_overlap(agent_capabilities: list[str], task_requirements: list[str]) -> float:
    """Return a 0.0-1.0 score representing how well an agent matches a task.

    Score = |intersection| / |requirements|.  If the task has no requirements
    every agent scores 1.0.
    """
    if not task_requirements:
        return 1.0
    agent_set = {c.lower() for c in agent_capabilities}
    req_set = {r.lower() for r in task_requirements}
    return len(agent_set & req_set) / len(req_set)


def match_agent_to_task(agents: list[Agent], task: Task) -> Agent | None:
    """Return the agent with the highest capability overlap for *task*.

    Returns ``None`` when no agent has any overlap (and the task has
    requirements).
    """
    if not agents:
        return None

    scored = [(agent, capability_overlap(agent.capabilities, task.requirements)) for agent in agents]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    best_agent, best_score = scored[0]
    if best_score == 0.0 and task.requirements:
        return None
    return best_agent


def rank_agents_for_task(agents: list[Agent], task: Task) -> list[tuple[Agent, float]]:
    """Return agents sorted by descending match score for *task*."""
    scored = [(agent, capability_overlap(agent.capabilities, task.requirements)) for agent in agents]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


# ── Voting Algorithms ───────────────────────────────────────────────


def plurality_vote(votes: list[str], options: list[str]) -> str:
    """Return the option with the most votes (plurality / first-past-the-post).

    Ties are broken by the original ordering in *options*.
    """
    counts = Counter(votes)
    max_count = max(counts.values())
    # Preserve option order for tie-breaking
    for option in options:
        if counts.get(option, 0) == max_count:
            return option
    # Fallback (should never reach here if votes are valid)
    return options[0]


def borda_count(rankings: list[list[str]], options: list[str]) -> str:
    """Borda count: each ranking awards points inversely to position.

    ``rankings`` is a list of per-agent orderings (best-first).
    """
    n = len(options)
    scores: dict[str, int] = {o: 0 for o in options}
    for ranking in rankings:
        for position, option in enumerate(ranking):
            if option in scores:
                scores[option] += n - 1 - position
    best = max(scores, key=lambda o: scores[o])
    return best


def approval_vote(approvals: list[set[str]], options: list[str]) -> str:
    """Each agent approves a subset of options; the most-approved wins."""
    counts: dict[str, int] = {o: 0 for o in options}
    for approved in approvals:
        for option in approved:
            if option in counts:
                counts[option] += 1
    best = max(counts, key=lambda o: counts[o])
    return best


# ── Consensus ────────────────────────────────────────────────────────


def weighted_consensus(
    scores: dict[str, list[float]],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Determine consensus from per-proposal score lists.

    Returns a dict with:
      - ``proposal``: the winning proposal (or None)
      - ``score``: its average score
      - ``reached``: whether the threshold was met
      - ``all_scores``: average scores for every proposal
    """
    averages: dict[str, float] = {}
    for proposal, agent_scores in scores.items():
        averages[proposal] = sum(agent_scores) / len(agent_scores) if agent_scores else 0.0

    best_proposal = max(averages, key=lambda p: averages[p])
    best_score = averages[best_proposal]

    return {
        "proposal": best_proposal if best_score >= threshold else None,
        "score": round(best_score, 4),
        "reached": best_score >= threshold,
        "all_scores": {p: round(s, 4) for p, s in averages.items()},
    }


# ── Result Aggregation ──────────────────────────────────────────────


def aggregate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clean and return aggregated results.

    Filters out error placeholders and adds a sequential index.
    """
    aggregated: list[dict[str, Any]] = []
    for idx, result in enumerate(results):
        entry = {**result, "index": idx}
        aggregated.append(entry)
    return aggregated


def summary_stats(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary statistics over a list of result dicts."""
    total = len(results)
    completed = sum(1 for r in results if r.get("status") == "completed")
    errors = sum(1 for r in results if r.get("status") == "error")
    agents_used = list({r.get("agent", "unknown") for r in results if r.get("agent")})

    return {
        "total": total,
        "completed": completed,
        "errors": errors,
        "success_rate": round(completed / total, 4) if total else 0.0,
        "agents_used": agents_used,
    }
