"""Tests for SwarmKit utility functions."""

import pytest

from swarmkit.core import Agent, Task
from swarmkit.utils import (
    approval_vote,
    borda_count,
    capability_overlap,
    match_agent_to_task,
    plurality_vote,
    rank_agents_for_task,
    summary_stats,
    weighted_consensus,
)

# ── Task Matching ────────────────────────────────────────────────────


class TestTaskMatching:
    def test_capability_overlap_full(self):
        assert capability_overlap(["search", "fetch"], ["search"]) == 1.0

    def test_capability_overlap_partial(self):
        assert capability_overlap(["search"], ["search", "fetch"]) == 0.5

    def test_capability_overlap_no_requirements(self):
        assert capability_overlap([], []) == 1.0

    def test_capability_overlap_is_case_insensitive(self):
        assert capability_overlap(["Search"], ["search"]) == 1.0

    def test_match_agent_to_task_picks_best(self):
        agents = [
            Agent(name="A1", role="r", capabilities=["search"]),
            Agent(name="A2", role="r", capabilities=["write"]),
        ]
        task = Task(description="t", requirements=["write"])
        best = match_agent_to_task(agents, task)
        assert best is not None
        assert best.name == "A2"

    def test_match_agent_to_task_no_overlap_returns_none(self):
        agents = [Agent(name="A1", role="r", capabilities=["search"])]
        task = Task(description="t", requirements=["fly"])
        assert match_agent_to_task(agents, task) is None

    def test_match_agent_to_task_empty_agents_returns_none(self):
        assert match_agent_to_task([], Task(description="t")) is None

    def test_rank_agents_for_task_orders_by_score(self):
        agents = [
            Agent(name="low", role="r", capabilities=["write"]),
            Agent(name="high", role="r", capabilities=["search", "fetch"]),
        ]
        task = Task(description="t", requirements=["search", "fetch"])
        ranked = rank_agents_for_task(agents, task)
        assert [a.name for a, _ in ranked] == ["high", "low"]
        assert ranked[0][1] == 1.0


# ── Voting Algorithms ───────────────────────────────────────────────


class TestVoting:
    def test_plurality_vote_winner(self):
        votes = ["a", "b", "a", "c"]
        assert plurality_vote(votes, ["a", "b", "c"]) == "a"

    def test_plurality_vote_tie_breaks_by_order(self):
        votes = ["a", "b"]
        assert plurality_vote(votes, ["a", "b"]) == "a"

    def test_borda_count(self):
        # "a" ranked first in both rankings -> highest Borda score
        rankings = [["a", "b", "c"], ["a", "c", "b"]]
        assert borda_count(rankings, ["a", "b", "c"]) == "a"

    def test_approval_vote(self):
        approvals = [{"a", "b"}, {"a"}, {"c"}]
        assert approval_vote(approvals, ["a", "b", "c"]) == "a"


# ── Consensus ────────────────────────────────────────────────────────


class TestConsensus:
    def test_weighted_consensus_reached(self):
        result = weighted_consensus({"p1": [0.8, 0.9], "p2": [0.1, 0.2]}, threshold=0.5)
        assert result["proposal"] == "p1"
        assert result["reached"] is True
        assert result["score"] == pytest.approx(0.85)

    def test_weighted_consensus_not_reached(self):
        result = weighted_consensus({"p1": [0.1, 0.2]}, threshold=0.5)
        assert result["proposal"] is None
        assert result["reached"] is False

    def test_weighted_consensus_empty_scores_default_zero(self):
        result = weighted_consensus({"p1": []}, threshold=0.5)
        assert result["all_scores"]["p1"] == 0.0
        assert result["reached"] is False


# ── Result Aggregation ──────────────────────────────────────────────


class TestSummaryStats:
    def test_summary_stats_mixed(self):
        results = [
            {"status": "completed", "agent": "A1"},
            {"status": "completed", "agent": "A2"},
            {"status": "error"},
        ]
        stats = summary_stats(results)
        assert stats["total"] == 3
        assert stats["completed"] == 2
        assert stats["errors"] == 1
        assert stats["success_rate"] == pytest.approx(2 / 3, abs=1e-4)
        assert set(stats["agents_used"]) == {"A1", "A2"}

    def test_summary_stats_empty(self):
        stats = summary_stats([])
        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["agents_used"] == []


# ── Deterministic vote fallback ──────────────────────────────────────


class TestDeterministicVoteFallback:
    @pytest.mark.asyncio
    async def test_cast_vote_fallback_is_stable_for_same_id(self):
        # An agent with no matching capability falls back to a stable, id-derived
        # choice that must not change between calls within or across processes.
        agent = Agent(id="deadbeef", name="A", role="r", capabilities=[])
        options = ["x", "y", "z"]
        first = await agent.cast_vote(options)
        second = await agent.cast_vote(options)
        assert first == second
        assert first in options
