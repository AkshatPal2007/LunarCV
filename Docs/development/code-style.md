# Code Style Guide

Coding conventions and style guidelines for LunarCV.

## Python (Backend)

### Tools

- **Formatter**: Ruff
- **Linter**: Ruff
- **Type Checker**: MyPy (planned)

### Running Checks

```bash
cd backend

# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check specific file
ruff check app/api/routes/upload.py
```

### Style Rules

**PEP 8 Compliance**
- Maximum line length: **88 characters** (Black/Ruff default)
- Indentation: **4 spaces** (never tabs)
- Blank lines: 2 between top-level definitions, 1 between methods

**Naming Conventions**
```python
# Classes: PascalCase
class LightGlueFeatureMatcher:
    pass

# Functions/variables: snake_case
def compute_registration(pts_src, pts_ref):
    inlier_count = len(pts_src)

# Constants: UPPER_SNAKE_CASE
MAX_UPLOAD_SIZE = 1073741824
API_V1_STR = "/api/v1"

# Private: leading underscore
def _internal_helper():
    pass
```

**Type Hints**
```python
from pathlib import Path
import numpy as np

# Always type function signatures
def load_image(
    img_path: Path,
    dtype: str = "uint8",
    shape: tuple[int, int] | None = None
) -> np.ndarray:
    """Load image via memory mapping."""
    ...

# Use modern syntax (Python 3.11+)
from typing import Optional  # ❌ Old
def foo(x: Optional[int]) -> list[str]:

def foo(x: int | None) -> list[str]:  # ✅ New
```

**Imports**
```python
# Order: stdlib, third-party, local
import json
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter

from app.config import settings
from lunarcv.matching import LightGlueFeatureMatcher

# Avoid star imports
from module import *  # ❌
from module import specific_function  # ✅
```

**Docstrings**

Use Google style for public functions:

```python
def magsac_filter(
    mkpts_src: np.ndarray,
    mkpts_ref: np.ndarray,
    conf: np.ndarray,
    model: str = "homography"
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply MAGSAC++ geometric outlier rejection.
    
    Args:
        mkpts_src: Source keypoints (N, 2)
        mkpts_ref: Reference keypoints (N, 2)
        conf: Match confidence scores (N,)
        model: Geometric model ("homography" or "affine")
        
    Returns:
        Tuple of (clean_src, clean_ref, clean_conf, H_matrix, inlier_mask)
    """
```

**Skip docstrings for:**
- Private functions
- Obvious one-liners
- Test functions

**Comments**

Default to **zero comments**. Only comment when:
- Non-obvious algorithm (cite paper)
- Workaround for external bug
- Performance-critical section
- Subtle invariant

```python
# ❌ Don't comment the obvious
def add(a, b):
    # Add two numbers
    return a + b

# ✅ Comment the non-obvious
def compute_homography(pts_ref, pts_src):
    # MAGSAC++ expects reference->source mapping, opposite of cv2.warpPerspective
    H, mask = cv2.findHomography(pts_ref, pts_src, method=cv2.USAC_MAGSAC)
```

**Error Handling**

Be specific, catch narrow exceptions:

```python
# ❌ Too broad
try:
    result = risky_operation()
except Exception:
    pass

# ✅ Specific
try:
    result = risky_operation()
except FileNotFoundError as e:
    raise ValueError(f"Input file not found: {path}") from e
```

**Path Handling**

Always use `pathlib.Path`:

```python
# ❌ String paths
import os
path = os.path.join("data", "uploads", "file.png")
if os.path.exists(path):
    with open(path, "rb") as f:
        ...

# ✅ pathlib.Path
from pathlib import Path
path = Path("data") / "uploads" / "file.png"
if path.exists():
    data = path.read_bytes()
```

## JavaScript/React (Frontend)

### Tools

- **Linter**: Oxlint
- **Formatter**: (configured in oxlintrc)

### Running Checks

```bash
cd frontend

# Lint
npm run lint

# (No auto-fix yet with Oxlint)
```

### Style Rules

**Naming Conventions**

```javascript
// Components: PascalCase
function UploadButton({ onUpload }) { ... }

// Functions/variables: camelCase
const handleUpload = () => { ... };
const isLoading = false;

// Constants: UPPER_SNAKE_CASE
const MAX_FILE_SIZE = 1024 * 1024 * 1024;
const API_BASE_URL = import.meta.env.VITE_API_URL;

// Private: leading underscore (by convention)
function _internalHelper() { ... }
```

**Components**

Functional components with hooks:

```javascript
// ✅ Preferred
function UploadButton({ onUpload, isLoading }) {
  const [file, setFile] = useState(null);
  
  const handleClick = () => {
    if (file) onUpload(file);
  };
  
  return (
    <button 
      onClick={handleClick}
      disabled={isLoading}
      className="px-4 py-2 bg-blue-500"
    >
      {isLoading ? 'Uploading...' : 'Upload'}
    </button>
  );
}

// ❌ Avoid class components
class UploadButton extends React.Component { ... }
```

**Props Destructuring**

```javascript
// ✅ Destructure props
function Card({ title, description, onClick }) {
  return <div onClick={onClick}>...</div>;
}

// ❌ Don't use props object
function Card(props) {
  return <div onClick={props.onClick}>{props.title}</div>;
}
```

**Styling**

Use Tailwind classes, avoid inline styles:

```javascript
// ✅ Tailwind utility classes
<button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded">
  Click Me
</button>

// ❌ Inline styles
<button style={{ padding: '16px', backgroundColor: 'blue' }}>
  Click Me
</button>
```

**Imports**

```javascript
// Order: React, third-party, local, styles
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

import Button from './components/Button';
import { uploadImage } from './api/client';
```

**Async/Await**

```javascript
// ✅ Async/await with error handling
async function handleUpload(file) {
  try {
    const result = await uploadImage(file);
    console.log('Success:', result);
  } catch (error) {
    console.error('Upload failed:', error);
  }
}

// ❌ Unhandled promises
function handleUpload(file) {
  uploadImage(file).then(result => {
    console.log(result);
  });
}
```

## File Organization

### Backend Structure

```
backend/
├── app/                    # FastAPI application
│   ├── api/
│   │   └── routes/        # One file per resource
│   ├── schemas/           # Pydantic models
│   ├── services/          # Business logic
│   └── config.py          # Settings
├── lunarcv/               # Core CV library
│   ├── io/
│   ├── matching/
│   ├── registration/
│   └── config.py
└── scripts/               # CLI tools
```

### Frontend Structure

```
frontend/
└── src/
    ├── api/              # API client
    ├── components/       # Reusable components
    ├── pages/            # Page components (future)
    └── utils/            # Helper functions
```

## Git Commit Messages

Follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructure
- `test`: Tests
- `chore`: Maintenance

**Examples:**

```bash
feat(api): add batch registration endpoint

Allows registering multiple image pairs in a single request.
Each pair is processed as a separate background job.

Closes #45

---

fix(matching): handle zero features edge case

LightGlue crashes when an image has no detectable features.
Now returns empty arrays instead of raising exception.

---

docs(setup): add Windows-specific setup steps

---

chore(deps): update pytorch to 2.6.0
```

## Configuration Files

### .editorconfig

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 88

[*.{js,jsx,json}]
indent_style = space
indent_size = 2
```

### Ruff Configuration

Already in `backend/pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "S", "B", "A", "C4", "PT", "SIM"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S105", "S106"]  # Allow asserts, hardcoded passwords in tests
```

## Pre-commit Hooks

Install pre-commit hooks to enforce style automatically:

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

## Code Review Checklist

Before submitting PR:

- [ ] Code passes `ruff check .`
- [ ] Code passes `ruff format .`
- [ ] All tests pass (`pytest`)
- [ ] New code has tests
- [ ] Type hints on public functions
- [ ] No commented-out code
- [ ] No `print()` statements (use logging)
- [ ] No hardcoded secrets or paths
- [ ] Commit messages follow convention

## IDE Configuration

### VS Code

Create `.vscode/settings.json`:

```json
{
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.rulers": [88]
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm

1. Settings → Tools → Ruff → Enable Ruff
2. Settings → Editor → Code Style → Python → Set line length to 88
3. Settings → Editor → Inspections → Enable PEP 8 checks

## Anti-Patterns to Avoid

### Python

```python
# ❌ Mutable default arguments
def add_item(item, items=[]):
    items.append(item)
    return items

# ✅ Use None
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items

# ❌ Catching Exception
try:
    ...
except Exception:
    pass

# ✅ Catch specific exceptions
try:
    ...
except (ValueError, KeyError) as e:
    logger.error(f"Error: {e}")
```

### JavaScript

```javascript
// ❌ Prop drilling
<Parent>
  <Child1 data={data}>
    <Child2 data={data}>
      <Child3 data={data} />

// ✅ Use context or state management
const DataContext = createContext();

// ❌ Inline arrow functions in renders
<button onClick={() => handleClick(id)}>

// ✅ Memoize callbacks
const handleClick = useCallback(() => {...}, [id]);
<button onClick={handleClick}>
```

## Resources

- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [React Best Practices](https://react.dev/learn)
- [Conventional Commits](https://www.conventionalcommits.org/)
