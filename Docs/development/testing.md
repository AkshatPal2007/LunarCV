# Testing Guide

Write and run tests for LunarCV backend and frontend.

## Backend Testing

### Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures
├── test_api/
│   ├── __init__.py
│   ├── test_health.py       # Health endpoint tests
│   ├── test_upload.py       # Upload tests
│   └── test_registration.py # Registration job tests
└── test_lunarcv/
    ├── __init__.py
    ├── test_matching.py     # Feature matcher tests
    ├── test_outlier.py      # MAGSAC++ tests
    └── test_transform.py    # Transform tests
```

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_api/test_health.py

# Run specific test
pytest tests/test_api/test_health.py::test_health_check

# Run with coverage
pytest --cov=app --cov=lunarcv --cov-report=html

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Writing Tests

#### API Tests

Use FastAPI's `TestClient` for endpoint testing:

```python
# tests/test_api/test_health.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

#### Upload Tests

```python
# tests/test_api/test_upload.py
def test_upload_valid_image(client, tmp_path):
    # Create test image
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"fake image data")
    
    with open(img_path, "rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.png", f, "image/png")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == "test.png"

def test_upload_invalid_extension(client):
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.exe", b"data", "application/exe")}
    )
    assert response.status_code == 400
```

#### CV Pipeline Tests

```python
# tests/test_lunarcv/test_matching.py
import numpy as np
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher

def test_lightglue_matcher():
    matcher = LightGlueFeatureMatcher(max_dim=512, max_keypoints=128)
    
    # Create synthetic test images
    img_src = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
    img_ref = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
    
    # Run matching
    pts_src, pts_ref, conf = matcher.match(img_src, img_ref)
    
    # Verify output format
    assert pts_src.shape[1] == 2  # (N, 2) coordinates
    assert pts_ref.shape[1] == 2
    assert len(conf) == len(pts_src)
    assert np.all((conf >= 0) & (conf <= 1))  # Confidence in [0,1]
```

### Fixtures

Share test setup via `conftest.py`:

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)

@pytest.fixture
def test_images(tmp_path):
    """Create temporary test images."""
    source = tmp_path / "source.png"
    reference = tmp_path / "reference.png"
    
    # Create fake images
    source.write_bytes(b"fake source")
    reference.write_bytes(b"fake reference")
    
    return {"source": source, "reference": reference}
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import patch, MagicMock

@patch('lunarcv.matching.lightglue_matcher.LightGlueFeatureMatcher')
def test_registration_with_mock(mock_matcher, client):
    # Mock matcher behavior
    mock_instance = MagicMock()
    mock_instance.match.return_value = (
        np.array([[0, 0], [10, 10]]),  # pts_src
        np.array([[0, 0], [10, 10]]),  # pts_ref
        np.array([0.9, 0.8])            # confidence
    )
    mock_matcher.return_value = mock_instance
    
    # Test with mock
    response = client.post("/api/v1/register", json={...})
    assert response.status_code == 200
```

### Parametrized Tests

Test multiple scenarios:

```python
@pytest.mark.parametrize("matcher,expected", [
    ("lightglue", 200),
    ("loftr", 200),
    ("invalid", 400),
])
def test_register_with_matchers(client, matcher, expected):
    response = client.post("/api/v1/register", json={
        "source_image_id": "test-src",
        "reference_image_id": "test-ref",
        "matcher": matcher
    })
    assert response.status_code == expected
```

### Async Tests

For async code:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Test Coverage

Generate coverage reports:

```bash
# Terminal report
pytest --cov=app --cov=lunarcv

# HTML report
pytest --cov=app --cov=lunarcv --cov-report=html
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
```

**Coverage Goals:**
- API routes: >90%
- Core CV algorithms: >80%
- Overall: >80%

## Frontend Testing

*(Not yet implemented - contribution opportunity)*

### Planned Stack

- **Test Framework**: Vitest
- **Component Testing**: React Testing Library
- **E2E Testing**: Playwright

### Setup (Future)

```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
```

### Example Component Test

```javascript
// src/components/UploadButton.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import UploadButton from './UploadButton';

describe('UploadButton', () => {
  it('calls onUpload when clicked', () => {
    const mockUpload = vi.fn();
    render(<UploadButton onUpload={mockUpload} />);
    
    const button = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(button);
    
    expect(mockUpload).toHaveBeenCalledOnce();
  });
});
```

## Integration Testing

Test full registration workflow:

```python
# tests/test_integration.py
def test_full_registration_workflow(client, test_images):
    # 1. Upload source image
    with open(test_images["source"], "rb") as f:
        upload_src = client.post("/api/v1/upload", files={"file": f})
    source_id = upload_src.json()["file_id"]
    
    # 2. Upload reference image
    with open(test_images["reference"], "rb") as f:
        upload_ref = client.post("/api/v1/upload", files={"file": f})
    reference_id = upload_ref.json()["file_id"]
    
    # 3. Create registration job
    job_resp = client.post("/api/v1/register", json={
        "source_image_id": source_id,
        "reference_image_id": reference_id,
        "matcher": "lightglue"
    })
    assert job_resp.status_code == 200
    job_id = job_resp.json()["job_id"]
    
    # 4. Poll until complete (with timeout)
    import time
    for _ in range(30):
        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        status = status_resp.json()["status"]
        if status in ["completed", "failed"]:
            break
        time.sleep(1)
    
    # 5. Get results
    results_resp = client.get(f"/api/v1/jobs/{job_id}/results")
    assert results_resp.status_code == 200
    results = results_resp.json()
    
    if results["status"] == "completed":
        assert "metrics" in results
        assert results["registered_image_url"] is not None
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install uv
          uv sync
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov=lunarcv --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./backend/coverage.xml
```

## Performance Testing

Test registration speed:

```python
# tests/test_performance.py
import pytest
import time

def test_registration_performance(client, test_images):
    # Upload images
    # ... (upload code)
    
    # Start job
    start = time.time()
    job_resp = client.post("/api/v1/register", json={...})
    job_id = job_resp.json()["job_id"]
    
    # Wait for completion
    while True:
        status = client.get(f"/api/v1/jobs/{job_id}").json()
        if status["status"] != "processing":
            break
        time.sleep(0.5)
    
    elapsed = time.time() - start
    
    # Assert reasonable time (e.g., <60s for small test images)
    assert elapsed < 60, f"Registration took {elapsed}s, expected <60s"
```

## Test Data

### Real Test Images

For accurate testing, use small real lunar images:

```
backend/tests/data/
├── ohrc_patch_small.png    # 512x512 Chandrayaan-2 OHRC
└── lro_patch_small.png     # 512x512 LRO NAC
```

Download from project datasets or generate synthetic test patches.

### Fixtures vs Test Data

- **Fixtures** (`conftest.py`): Reusable test setup (clients, mocks)
- **Test Data** (`tests/data/`): Static files (images, CSVs)

## Debugging Tests

### Run with pdb

```bash
pytest --pdb  # Drop into debugger on failure
```

### Print statements

```python
def test_something():
    result = function_under_test()
    print(f"DEBUG: result = {result}")  # Shows in pytest output with -s
    assert result == expected
```

Run with:
```bash
pytest -s  # Show print statements
```

### Verbose output

```bash
pytest -vv  # Very verbose
```

## Best Practices

1. **One assertion per test** (when possible)
2. **Descriptive test names** - `test_upload_rejects_invalid_extension`
3. **Arrange-Act-Assert** pattern
4. **Mock external dependencies** (APIs, databases)
5. **Test edge cases** - empty inputs, large inputs, invalid data
6. **Fast tests** - Unit tests <1s, integration tests <10s
7. **Independent tests** - Tests should not depend on each other
8. **Clean up** - Use fixtures to handle setup/teardown

## Troubleshooting

### Tests pass locally but fail in CI

**Common causes:**
- Path differences (Windows vs Linux)
- Missing dependencies
- Race conditions in async code

**Fix:** Use `tmp_path` fixture for temp files, pin all dependencies.

### ImportError

**Error:** `ModuleNotFoundError: No module named 'app'`

**Fix:** Install package in editable mode:
```bash
cd backend
pip install -e .
```

### Slow tests

**Symptoms:** Test suite takes >1 minute

**Fix:**
- Mock expensive operations (GPU inference, large file I/O)
- Use smaller test images
- Run slow tests separately: `pytest -m slow`

Mark slow tests:
```python
@pytest.mark.slow
def test_full_registration_on_large_images():
    ...
```

## Next Steps

- [Code Style Guide](code-style.md)
- [Contributing Guide](contributing.md)
- [CI/CD Setup](../deployment/production.md)
