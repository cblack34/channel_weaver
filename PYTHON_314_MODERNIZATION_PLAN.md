# Python 3.14 Modernization Plan

This document outlines all legacy Python patterns found in the Channel Weaver codebase and the recommended modern Python 3.14 replacements.

## Summary ✅ ALL PHASES COMPLETED

| Category | Files Affected | Priority | Status |
|----------|---------------|----------|--------|
| `from __future__ import annotations` | 4 files | High | ✅ Completed |
| `typing.Optional[X]` → `X \| None` | 4 files | High | ✅ Completed |
| `typing.TypeAlias` → `type` statement | 1 file | Medium | ✅ Completed |
| `typing.Protocol` | 2 files | None (already modern) | ✅ Verified |
| `typing.Self` | 1 file | None (already modern) | ✅ Verified |

---

## 1. Remove `from __future__ import annotations`

**Background:** The `from __future__ import annotations` import was introduced in PEP 563 to enable postponed evaluation of annotations (storing them as strings). In Python 3.14, annotations are natively handled without this import, making it unnecessary.

### Files to Update

| File | Line | Action |
|------|------|--------|
| [src/main.py](src/main.py#L7) | 7 | Remove import |
| [src/cli/app.py](src/cli/app.py#L2) | 2 | Remove import |
| [src/cli/utils.py](src/cli/utils.py#L2) | 2 | Remove import |
| [src/cli/commands.py](src/cli/commands.py#L2) | 2 | Remove import |

### Changes Required

```python
# Before
from __future__ import annotations

# After
# (simply remove the line)
```

---

## 2. Replace `Optional[X]` with `X | None`

**Background:** Python 3.10 introduced the union operator (`|`) for type hints. `Optional[X]` is now considered legacy syntax and should be replaced with `X | None` for clarity and consistency.

### Files to Update

| File | Line | Current | Replacement |
|------|------|---------|-------------|
| [src/cli/commands.py](src/cli/commands.py#L6) | 6 | `from typing import Optional` | Remove import |
| [src/cli/commands.py](src/cli/commands.py#L43) | 43 | `Optional[Path]` | `Path \| None` |
| [src/cli/commands.py](src/cli/commands.py#L54) | 54 | `Optional[Path]` | `Path \| None` |
| [src/cli/utils.py](src/cli/utils.py#L5) | 5 | `from typing import Optional` | Remove import |
| [src/cli/utils.py](src/cli/utils.py#L28) | 28 | `Optional[Path]` | `Path \| None` |
| [src/cli/utils.py](src/cli/utils.py#L36) | 36 | `Optional[Path]` | `Path \| None` |
| [src/processing/builder.py](src/processing/builder.py#L4) | 4 | `from typing import Optional` | Remove import |
| [src/processing/builder.py](src/processing/builder.py#L34) | 34 | `Optional[Console]` | `Console \| None` |
| [src/audio/extractor.py](src/audio/extractor.py#L4) | 4 | `from typing import Optional` | Remove import |
| [src/audio/extractor.py](src/audio/extractor.py#L36) | 36 | `Optional[Console]` | `Console \| None` |

### Changes Required

```python
# Before
from typing import Optional

def func(arg: Optional[Path] = None) -> Optional[str]:
    ...

# After
def func(arg: Path | None = None) -> str | None:
    ...
```

---

## 3. Replace `TypeAlias` with `type` Statement

**Background:** Python 3.12 introduced the `type` statement for declaring type aliases (PEP 695). This replaces the `typing.TypeAlias` annotation which is now considered legacy.

### Files to Update

| File | Current Pattern | Lines |
|------|-----------------|-------|
| [src/config/types.py](src/config/types.py) | Uses `TypeAlias` annotation | 3, 5-8 |

### Current Code

```python
from typing import TypeAlias, TypedDict

SegmentMap: TypeAlias = dict[int, list[Path]]
ChannelData: TypeAlias = dict[str, object]
BusData: TypeAlias = dict[str, object]
AudioInfo: TypeAlias = tuple[int, int, str]
```

### Modern Python 3.14 Code

```python
from typing import TypedDict

type SegmentMap = dict[int, list[Path]]
type ChannelData = dict[str, object]
type BusData = dict[str, object]
type AudioInfo = tuple[int, int, str]
```

---

## 4. Already Modern Patterns (No Changes Needed)

The following patterns are already using modern Python syntax:

### `typing.Protocol` ✅
Used correctly in:
- [src/processing/converters/protocols.py](src/processing/converters/protocols.py) - `BitDepthConverter` protocol
- [src/output/protocols.py](src/output/protocols.py) - `OutputHandler` protocol

`Protocol` is still the correct way to define structural subtyping interfaces.

### `typing.Self` ✅
Used correctly in:
- [src/config/models.py](src/config/models.py#L3) - `from typing import Self`
- [src/config/models.py](src/config/models.py#L35) - `-> Self` return type

`Self` (introduced in Python 3.11) is the modern replacement for the old `TypeVar` pattern for methods returning `self`.

### Built-in Generic Types ✅
The codebase already uses modern built-in generics:
- `list[X]` instead of `typing.List[X]`
- `dict[X, Y]` instead of `typing.Dict[X, Y]`
- `tuple[X, ...]` instead of `typing.Tuple[X, ...]`
- `set[X]` instead of `typing.Set[X]`

### Union Operator `|` ✅
Already used in several places:
- [src/processing/builder.py](src/processing/builder.py#L29) - `BitDepth | None`
- [src/audio/extractor.py](src/audio/extractor.py#L37) - `OutputHandler | None`

---

## 5. Implementation Checklist

### Phase 1: Remove `__future__` Imports (4 files) ✅ COMPLETED
- [x] `src/main.py` - Remove line 7
- [x] `src/cli/app.py` - Remove line 2
- [x] `src/cli/utils.py` - Remove line 2
- [x] `src/cli/commands.py` - Remove line 2

### Phase 2: Replace `Optional[X]` with `X | None` (4 files) ✅ COMPLETED
- [x] `src/cli/commands.py` - Remove `Optional` import, update type hints
- [x] `src/cli/utils.py` - Remove `Optional` import, update type hints
- [x] `src/processing/builder.py` - Remove `Optional` import, update type hints
- [x] `src/audio/extractor.py` - Remove `Optional` import, update type hints

### Phase 3: Convert `TypeAlias` to `type` Statement (1 file) ✅ COMPLETED
- [x] `src/config/types.py` - Replace `TypeAlias` with `type` statements

### Phase 4: Validation ✅ COMPLETED
- [x] Run `uv run python -m py_compile` on all modified files
- [x] Run the application: `uv run python -m src.main --help`
- [x] Test with actual processing: `uv run python -m src.main <input_dir> --output <output_dir>`

---

## 6. Python 3.14 Features Not Yet Adopted

These are additional Python 3.14 features that could be considered for future adoption:

### Type Alias Star Unpacking (Python 3.14)
```python
type Alias = tuple[int, str]
type Unpacked = tuple[bool, *Alias]  # New in 3.14
```

### Generic Functions with Type Parameter Syntax (Python 3.12+)
```python
# Current (still valid)
from typing import TypeVar
T = TypeVar('T')
def first(items: list[T]) -> T: ...

# Modern alternative
def first[T](items: list[T]) -> T: ...
```

This is optional and the current approach is still valid.

---

## 7. Deprecated Patterns to Avoid

The following `typing` module features are deprecated and should NOT be introduced:

| Deprecated | Removal Version | Replacement |
|------------|-----------------|-------------|
| `typing.AnyStr` | 3.18 | Use type parameter syntax |
| `typing.no_type_check_decorator()` | 3.15 | N/A |
| `typing.ByteString` | 3.14 | `bytes \| bytearray \| memoryview` |
| `typing.List`, `typing.Dict`, etc. | N/A | `list`, `dict` (built-in generics) |

---

## 8. Testing Commands

After making changes, validate with:

```powershell
# Compile check all Python files
uv run python -m py_compile src/**/*.py

# Import check
uv run python -c "from src.main import *; from src.cli import *; from src.config import *"

# Full application test
uv run python -m src.main --help

# Run with actual data
uv run python -m src.main "path/to/input" --output "path/to/output"
```
