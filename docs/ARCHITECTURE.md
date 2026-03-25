# SwarmKit Architecture

## Overview

SwarmKit is built around three core abstractions: **Agent**, **Task**, and **Swarm**. These are implemented as Pydantic models for type safety and validation, with async methods for concurrent execution.

## Core Components

### Agent

An `Agent` represents a single participant in the swarm. Each agent has:

- **name** — human-readable identifier
- **role** — describes the agent's purpose (e.g., "researcher", "writer")
- **capabilities** — list of strings defining what the agent can do
- **inbox** — internal message queue for broadcast communication

Key methods:
- `execute(task)` — run a task and return results (async)
- `cast_vote(options)` — participate in voting rounds (async)
- `evaluate_proposal(proposal)` — score a proposal for consensus (async)
- `receive(message)` / `get_messages()` — broadcast communication

### Task

A `Task` is a unit of work with:

- **description** — what needs to be done
- **requirements** — capabilities needed (used for agent matching)
- **priority** — 0-10 scale for execution ordering

### Swarm

The `Swarm` is the orchestrator. It manages a pool of agents and coordinates their work:

- **Agent management** — `add_agent()`, `remove_agent()`
- **Task assignment** — `assign_task()` matches tasks to agents via capability overlap
- **Execution** — `run(tasks)` executes tasks concurrently with `asyncio.gather`
- **Voting** — `vote(options)` implements plurality voting
- **Consensus** — `consensus(proposals)` uses weighted scoring with configurable thresholds
- **Communication** — `broadcast(message)` sends to all agents
- **Results** — `collect_results()` aggregates and returns accumulated outputs

## Data Flow

```
User
 │
 ▼
Swarm.run(tasks)
 │
 ├─ sort tasks by priority
 ├─ for each task:
 │   ├─ match_agent_to_task() → best Agent
 │   └─ asyncio.create_task(agent.execute(task))
 │
 ├─ asyncio.gather(*coroutines)
 │
 └─ return results[]
```

## Utility Layer (`utils.py`)

Stateless helper functions used by the core:

| Function | Purpose |
|----------|---------|
| `capability_overlap()` | Score agent-task fit (0.0-1.0) |
| `match_agent_to_task()` | Find best agent for a task |
| `plurality_vote()` | First-past-the-post voting |
| `borda_count()` | Ranked-choice voting |
| `approval_vote()` | Approval-based voting |
| `weighted_consensus()` | Threshold-based consensus |
| `aggregate_results()` | Clean and index results |
| `summary_stats()` | Compute success rates |

## Configuration

`SwarmConfig` (Pydantic model) controls runtime behavior:

- `max_agents` — capacity limit per swarm
- `task_timeout` — per-task timeout in seconds
- `consensus_threshold` — minimum score for consensus
- `log_level` — logging verbosity

All values can be set via environment variables (`SWARMKIT_*`).

## Extension Points

To customize agent behavior, subclass `Agent` and override:

- `execute(task)` — e.g., call an LLM API
- `cast_vote(options)` — implement domain-specific voting logic
- `evaluate_proposal(proposal)` — custom scoring

The Swarm class works with any `Agent` subclass without modification.
