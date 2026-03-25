"""Tests for SwarmKit core classes."""

import asyncio

import pytest

from swarmkit.core import Agent, Swarm, Task


# ── Agent Tests ──────────────────────────────────────────────────────


class TestAgent:
    def test_agent_creation(self):
        agent = Agent(name="Alice", role="researcher", capabilities=["search", "summarize"])
        assert agent.name == "Alice"
        assert agent.role == "researcher"
        assert "search" in agent.capabilities
        assert len(agent.id) == 8

    def test_agent_receive_and_get_messages(self):
        agent = Agent(name="Bob", role="worker", capabilities=[])
        agent.receive("hello")
        agent.receive("world")
        msgs = agent.get_messages()
        assert msgs == ["hello", "world"]
        # inbox should be cleared
        assert agent.get_messages() == []

    @pytest.mark.asyncio
    async def test_agent_execute(self):
        agent = Agent(name="Eve", role="executor", capabilities=["run"])
        task = Task(description="Do something", requirements=["run"])
        result = await agent.execute(task)
        assert result["agent"] == "Eve"
        assert result["status"] == "completed"
        assert result["task"] == "Do something"


# ── Task Tests ───────────────────────────────────────────────────────


class TestTask:
    def test_task_creation(self):
        task = Task(description="Analyze data", requirements=["analyze"], priority=5)
        assert task.description == "Analyze data"
        assert task.priority == 5
        assert "analyze" in task.requirements


# ── Swarm Tests ──────────────────────────────────────────────────────


class TestSwarm:
    def _make_swarm(self) -> Swarm:
        return Swarm(agents=[
            Agent(name="A1", role="search", capabilities=["search", "fetch"]),
            Agent(name="A2", role="write", capabilities=["write", "edit"]),
            Agent(name="A3", role="review", capabilities=["review", "validate"]),
        ])

    def test_add_and_remove_agent(self):
        swarm = Swarm()
        agent = Agent(name="New", role="helper", capabilities=["help"])
        swarm.add_agent(agent)
        assert len(swarm.agents) == 1
        removed = swarm.remove_agent("New")
        assert removed.name == "New"
        assert len(swarm.agents) == 0

    def test_remove_missing_agent_raises(self):
        swarm = self._make_swarm()
        with pytest.raises(ValueError, match="not found"):
            swarm.remove_agent("NonExistent")

    def test_assign_task_matches_capabilities(self):
        swarm = self._make_swarm()
        task = Task(description="Search the web", requirements=["search"])
        agent = swarm.assign_task(task)
        assert agent.name == "A1"

    def test_assign_task_no_match_raises(self):
        swarm = self._make_swarm()
        task = Task(description="Fly a plane", requirements=["pilot"])
        with pytest.raises(ValueError, match="No agent"):
            swarm.assign_task(task)

    @pytest.mark.asyncio
    async def test_run_tasks(self):
        swarm = self._make_swarm()
        tasks = [
            Task(description="Search docs", requirements=["search"]),
            Task(description="Write report", requirements=["write"]),
        ]
        results = await swarm.run(tasks)
        assert len(results) == 2
        assert all(r["status"] == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_vote(self):
        swarm = self._make_swarm()
        winner = await swarm.vote(options=["search", "write", "review"])
        assert winner in ["search", "write", "review"]

    @pytest.mark.asyncio
    async def test_consensus(self):
        swarm = self._make_swarm()
        result = await swarm.consensus(proposals=["Plan A", "Plan B"])
        assert "proposal" in result
        assert "score" in result
        assert "reached" in result
        assert isinstance(result["all_scores"], dict)

    def test_broadcast(self):
        swarm = self._make_swarm()
        count = swarm.broadcast("sync up")
        assert count == 3
        for agent in swarm.agents:
            msgs = agent.get_messages()
            assert msgs == ["sync up"]

    @pytest.mark.asyncio
    async def test_collect_results(self):
        swarm = self._make_swarm()
        tasks = [Task(description="Fetch data", requirements=["fetch"])]
        await swarm.run(tasks)
        results = swarm.collect_results()
        assert len(results) == 1
        assert results[0]["index"] == 0
        # After collection, internal store should be empty
        assert swarm.collect_results() == []

    def test_max_agents_enforced(self):
        from swarmkit.config import SwarmConfig

        swarm = Swarm(config=SwarmConfig(max_agents=2))
        swarm.add_agent(Agent(name="A", role="r", capabilities=[]))
        swarm.add_agent(Agent(name="B", role="r", capabilities=[]))
        with pytest.raises(ValueError, match="max capacity"):
            swarm.add_agent(Agent(name="C", role="r", capabilities=[]))
