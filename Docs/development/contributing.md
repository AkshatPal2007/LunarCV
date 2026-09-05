# Contributing Guide

Thank you for contributing to LunarCV! This guide will help you get started.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/LunarCV.git
   cd LunarCV
   ```
3. **Set up development environment**:
   ```bash
   make install
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### 1. Make Your Changes

Follow the [code style guide](code-style.md) and project conventions.

**Backend changes:**
```bash
cd backend
# Make changes to app/ or lunarcv/
ruff check --fix .  # Auto-fix linting issues
pytest  # Run tests
```

**Frontend changes:**
```bash
cd frontend
# Make changes to src/
npm run lint  # Check for issues
npm run dev  # Test in browser
```

### 2. Write Tests

All new features and bug fixes should include tests.

**Backend tests:**
```python
# backend/tests/test_registration.py
def test_registration_job_creation():
    response = client.post("/api/v1/register", json={
        "source_image_id": "test-source",
        "reference_image_id": "test-reference",
        "matcher": "lightglue"
    })
    assert response.status_code == 200
```

**Run tests:**
```bash
cd backend
pytest
pytest tests/test_registration.py::test_registration_job_creation  # Single test
pytest -v  # Verbose output
```

### 3. Commit Your Changes

Follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(api): add batch registration endpoint"
git commit -m "fix(matching): handle edge case in LightGlue when no features detected"
git commit -m "docs(setup): clarify GPU requirements in README"
```

**Multi-line commits:**
```bash
git commit -m "feat(registration): add TPS transform for polar regions

Thin-plate spline transform handles non-rigid deformation better
than homography for high-relief terrain. Automatically falls back
when homography RMSE > 2.0 pixels.

Closes #123"
```

### 4. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Create a PR on GitHub with:
- **Clear title** (follows conventional commit format)
- **Description** explaining:
  - What changed and why
  - How to test
  - Related issues (e.g., "Closes #123")
- **Screenshots** (for UI changes)

## Pull Request Guidelines

### Before Submitting

- [ ] Code passes all tests (`pytest` or `npm test`)
- [ ] Linting passes (`ruff check .` or `npm run lint`)
- [ ] No unnecessary dependencies added
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventional format
- [ ] Branch is up to date with `main`

### PR Template

```markdown
## What

Brief description of the change.

## Why

Motivation and context. Link related issues.

## How

Technical approach taken. Call out anything non-obvious.

## Testing

How to verify the change works:
1. Step 1
2. Step 2
3. Expected result

## Screenshots

(if applicable)

Closes #123
```

### Review Process

1. **Automated checks** run (linting, tests)
2. **Maintainer review** - typically within 2-3 days
3. **Revisions** - address feedback, push updates
4. **Approval** - maintainer approves PR
5. **Merge** - maintainer merges to `main`

## Code Style

### Python (Backend)

- **Formatter**: Ruff
- **Linter**: Ruff
- **Style**: PEP 8

**Run checks:**
```bash
cd backend
ruff check .
ruff format .
```

**Key conventions:**
- Type hints for function signatures
- Docstrings for public functions (Google style)
- Maximum line length: 88 characters
- Use `pathlib.Path` over string paths

**Example:**
```python
def load_image(img_path: Path, dtype: str = "uint8") -> np.ndarray:
    """Load image via memory mapping.
    
    Args:
        img_path: Path to image file
        dtype: NumPy dtype for array
        
    Returns:
        Memory-mapped array
    """
    return np.memmap(img_path, dtype=dtype, mode="r")
```

### JavaScript/React (Frontend)

- **Linter**: Oxlint
- **Style**: Airbnb-ish (enforced by linter)

**Run checks:**
```bash
cd frontend
npm run lint
```

**Key conventions:**
- Use functional components with hooks
- Props destructuring
- Meaningful variable names
- Avoid inline styles (use Tailwind)

**Example:**
```javascript
function UploadButton({ onUpload, isLoading }) {
  return (
    <button 
      onClick={onUpload}
      disabled={isLoading}
      className="px-4 py-2 bg-blue-500 text-white rounded"
    >
      {isLoading ? 'Uploading...' : 'Upload Image'}
    </button>
  );
}
```

## Testing Guidelines

### Backend Tests

**Structure:**
```
backend/tests/
├── test_api/
│   ├── test_upload.py
│   ├── test_registration.py
│   └── test_health.py
└── test_lunarcv/
    ├── test_matching.py
    ├── test_outlier_rejection.py
    └── test_transform.py
```

**Use pytest fixtures:**
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

**Test coverage goal:** >80%

### Frontend Tests

**Structure:**
```
frontend/src/
├── components/
│   ├── UploadButton.jsx
│   └── UploadButton.test.jsx
```

(Tests not yet set up - contribution opportunity!)

## Documentation

Update documentation when:
- Adding a new API endpoint → `docs/api/endpoints.md`
- Adding a CV algorithm → `docs/architecture/cv-pipeline.md`
- Changing setup steps → `docs/development/setup.md`
- Adding configuration → `docs/setup/configuration.md`

## Common Tasks

### Adding a New API Endpoint

1. **Define schema** in `backend/app/schemas/`:
   ```python
   class MyRequest(BaseModel):
       field: str
   ```

2. **Create route** in `backend/app/api/routes/`:
   ```python
   @router.post("/my-endpoint")
   async def my_endpoint(request: MyRequest):
       return {"result": "success"}
   ```

3. **Add to main app** in `backend/app/main.py`:
   ```python
   app.include_router(my_router, prefix="/api/v1", tags=["my-tag"])
   ```

4. **Write tests** in `backend/tests/test_api/`

5. **Document** in `docs/api/endpoints.md`

### Adding a New Feature Matcher

1. **Implement matcher** in `backend/lunarcv/matching/`:
   ```python
   class MyMatcher:
       def match(self, img_src, img_ref):
           # Implementation
           return pts_src, pts_ref, confidence
   ```

2. **Update service** in `backend/app/services/registration_service.py`:
   ```python
   if matcher == "mymatcher":
       feature_matcher = MyMatcher()
   ```

3. **Add tests** verifying matcher output format

4. **Document** algorithm in `docs/architecture/cv-pipeline.md`

## Reporting Issues

### Bug Reports

Use the bug report template:

**Title:** `bug(component): brief description`

**Body:**
```markdown
## Describe the bug
Clear description of what's wrong.

## To Reproduce
1. Step 1
2. Step 2
3. Observe error

## Expected behavior
What should happen instead.

## Environment
- OS: Windows 11
- Python: 3.11.5
- Docker: 24.0.7

## Logs
Paste relevant error messages.
```

### Feature Requests

Use the feature request template:

**Title:** `feat(component): brief description`

**Body:**
```markdown
## Problem
What problem does this solve?

## Proposed Solution
How should it work?

## Alternatives Considered
Other approaches you thought about.

## Additional Context
Any other relevant info.
```

## Community Guidelines

- Be respectful and constructive
- Assume good intent
- Focus on the code, not the person
- Help others learn

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Check [documentation](../README.md)
- Ask in issues or discussions
- Reach out to maintainers

Thank you for contributing! 🚀
