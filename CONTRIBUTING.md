# Contributing to SwarmKit

Thank you for your interest in contributing to SwarmKit! This guide will help you get started.

## Development Setup

1. **Fork and clone** the repository:

   ```bash
   git clone https://github.com/your-username/swarmkit.git
   cd swarmkit
   ```

2. **Create a virtual environment** and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   make install
   ```

3. **Run tests** to verify everything works:

   ```bash
   make test
   ```

## Making Changes

1. Create a new branch from `main`:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and add tests for any new functionality.

3. Ensure linting and tests pass:

   ```bash
   make lint
   make test
   ```

4. Commit with a clear message following [Conventional Commits](https://www.conventionalcommits.org/):

   ```
   feat: add new voting algorithm
   fix: handle empty agent list in consensus
   docs: update quickstart example
   ```

5. Push and open a Pull Request against `main`.

## Code Style

- We use **Ruff** for linting and formatting.
- Type hints are required for all public functions.
- **mypy** strict mode must pass.

## Adding a New Voting Algorithm

1. Implement the function in `src/swarmkit/utils.py`.
2. Add a method on `Swarm` in `src/swarmkit/core.py` that calls it.
3. Write tests in `tests/test_core.py`.

## Reporting Issues

Open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
