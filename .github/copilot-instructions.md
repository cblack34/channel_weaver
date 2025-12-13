---
applyTo: "**"
---
# Channel Weaver Development Guidelines

## Import Standards
- **ALWAYS use absolute imports** from the `src` package (e.g., `from src.config import ChannelConfig`)
- **NEVER use relative imports** (e.g., `from ..config import ChannelConfig`)
- Import order: standard library, third-party packages, local modules
- Group imports by category with blank lines between groups

## Code Quality Standards
- **SOLID Principles**: Follow Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion
- **Type Hints**: Use complete type annotations for all function parameters and return values
- **Docstrings**: Write comprehensive docstrings following Google/NumPy style for all public methods
- **Error Handling**: Use custom exceptions from `src.exceptions` instead of generic ones
- **Logging**: Use the `logging` module instead of `print()` statements for operational messages

## Project Structure
- **Package Organization**: All code in `src/` directory as proper Python package
- **Module Separation**: Models in `models.py`, exceptions in `exceptions.py`, constants in `constants.py`
- **Validation Logic**: Extract validation to dedicated classes (e.g., `ChannelValidator`, `BusValidator`)
- **Configuration**: Keep user-editable config at module level in `main.py`

## Pydantic Usage
- **Pydantic v2 API**: Use `@field_validator` with `@classmethod` decorator (not deprecated `@validator`)
- **Model Validators**: Use `@model_validator(mode='after')` for cross-field validation
- **Field Definitions**: Use `Field()` with proper descriptions and constraints

## Audio Processing
- **Memory Efficiency**: Process files in chunks, use temporary files for large datasets
- **Bit Depth Handling**: Support SOURCE preservation and conversion to 16/24-bit integer or 32-bit float
- **File Validation**: Check sample rate, channel count, and bit depth consistency across files
- **Error Messages**: Provide clear, actionable error messages for audio processing failures

## CLI Design
- **Typer Framework**: Use type hints and proper option definitions
- **Rich Console**: Use Rich for progress bars and formatted output
- **Path Handling**: Use `pathlib.Path` for all file operations with proper cross-platform support
- **Version Callback**: Use `is_eager=True` for version options

## Testing and Validation
- **Pydantic Validation**: Leverage Pydantic's built-in validation for user inputs
- **Runtime Checks**: Validate channel counts and bus assignments after file discovery
- **Edge Cases**: Handle missing channels, invalid configurations, and file system errors
- **Cleanup**: Ensure temporary files are cleaned up unless `--keep-temp` is specified

## Naming Conventions
- **Classes**: PascalCase (e.g., `ChannelConfig`, `AudioExtractor`)
- **Methods**: snake_case (e.g., `extract_segments()`, `validate_channels()`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `AUDIO_CHUNK_SIZE`)
- **Variables**: snake_case with descriptive names
- **Enums**: PascalCase for class names, UPPER_SNAKE_CASE for values

## Dependencies
- **Core Libraries**: numpy, pydantic, pysoundfile, rich, tqdm, typer
- **Version Constraints**: Pin to compatible versions in `pyproject.toml`
- **Import Efficiency**: Import only what's needed, avoid wildcard imports

## Python Execution
- **Use uv for Python execution**: Always use `uv run python` or `uv run python -m` instead of direct `python` calls
- **Module execution**: Use `uv run python -m src.main` for running the main module
- **Script execution**: Use `uv run python script.py` for running standalone scripts
- **Virtual environment**: uv automatically manages the virtual environment, no manual activation needed

## Documentation
- **README**: Keep updated with correct commands and usage examples
- **PRD Compliance**: Ensure all features match Product Requirements Document
- **Code Comments**: Use clear, concise comments explaining complex logic
- **Commit Messages**: Write descriptive commit messages following conventional format