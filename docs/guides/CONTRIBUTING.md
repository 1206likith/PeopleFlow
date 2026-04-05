# Contributing to PeopleFlow

Thank you for your interest in contributing to PeopleFlow. This document provides guidelines and instructions for contributing.

## Project Structure

PeopleFlow is organized into multiple modules:

- `apps/backend/` - FastAPI backend (Backend Developer)
- `apps/unity/` - Unity 3D simulation (Unity Developer)
- `modules/ai_engine/` - ML models and pathfinding (AI Engineer)
- `research/analytics/` - Visualization scripts (Data Engineer)

## Branch Strategy

We use a feature branch workflow:

- `main` - Production-ready code
- `dev` - Integration branch for all features
- `backend-dev` - Backend features
- `unity-dev` - Unity simulation features
- `ai-dev` - AI/ML model development
- `docs` - Documentation updates

## Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes:
   - Follow code style guidelines
   - Write or update tests
   - Update documentation

3. Commit your changes:
   ```bash
   git commit -m "feat: add new feature"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation
   - `style:` - Code style
   - `refactor:` - Code refactoring
   - `test:` - Tests
   - `chore:` - Maintenance

4. Push and create PR:
   ```bash
   git push origin feature/your-feature-name
   ```

   Create a Pull Request to `dev`.

5. Code review:
   - Address review comments
   - Ensure all tests pass
   - Update documentation if needed

## Module-Specific Guidelines

### Backend (FastAPI)
- Follow FastAPI best practices
- Use type hints
- Write API documentation
- Include error handling

### Unity
- Follow C# naming conventions
- Comment complex logic
- Optimize for performance
- Test in WebGL build

### AI Engine
- Document algorithms
- Include unit tests
- Use notebooks for experiments
- Save models in `modules/ai_engine/data/saved_models/`

### Analytics
- Make scripts executable
- Include command-line arguments
- Output to `output/` directory
- Document data formats

## Testing

- Write tests for new features
- Ensure existing tests pass
- Test integration between modules
- Update test documentation

## Documentation

- Update `README.md` if needed
- Add docstrings to functions and classes
- Update API documentation
- Include examples in `docs/`

## Reporting Issues

Use GitHub Issues with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Environment details

## Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests added or updated and passing
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Branch is up to date with `dev`

## Questions

- Open a GitHub Discussion
- Check existing documentation
- Review code examples

Thank you for contributing.
