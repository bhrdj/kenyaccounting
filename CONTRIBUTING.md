# Contributing to KenyAccounting

Welcome to the KenyAccounting project! We are building an open-source, compliant, and production-ready payroll system for Kenya. We value high-quality contributions that are scalable and maintainable.

## Getting Started

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/bhrdj/kenyaccounting.git
    cd kenyaccounting
    ```

2.  **Set Up Environment**:
    We enforce a strict development environment to ensure consistency.
    
    *   **Python Version**: We use **Python 3.10+**.
    *   **Enforcement**: We recommend using [pyenv](https://github.com/pyenv/pyenv). This project includes a `.python-version` file which `pyenv` will automatically detect to switch to the correct version.
    
    ```bash
    # IF using pyenv (Recommended)
    pyenv install 3.10
    
    # Create Virtual Env
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    # Install dev dependencies (if not in main requirements)
    pip install black mypy flake8 pytest
    ```

3.  **Run the Application**:
    ```bash
    streamlit run app.py
    ```

## Git Workflow & Branching Strategy

We follow a structured branching model. Please name your branches using the following conventions:

*   **`feature/`**: New capabilities (e.g., `feature/nssf-year-4-logic`).
*   **`fix/`**: Bug fixes for existing releases (e.g., `fix/shif-calculation-floor`).
*   **`hotfix/`**: Critical production fixes requiring immediate release.
*   **`refactor/`**: Code restructuring without changing behavior (e.g., `refactor/optimize-tax-bands`).
*   **`docs/`**: Documentation only changes.
*   **`chore/`**: Maintenance tasks, dependency updates, or build config changes.

### Daily Workflow

To ensure a smooth collaboration, please follow this routine:

1.  **Prioritize Reviews**: Before starting your own work, check for open Pull Requests. Reviewing and unblocking teammates is a higher priority than writing new code.
2.  **Sync First**: Always fetch the latest changes from the remote `main` branch before creating a new branch or starting work.
    ```bash
    git check out main
    git pull origin main
    ```

## Code Quality Standards

To maintain a production-ready codebase, all contributions must adhere to the following standards:

### 1. Style & Formatting
*   **Black is Mandatory**: All Python code must be formatted using [Black](https://github.com/psf/black).
    ```bash
    black .
    ```
*   **Linting**: Code should be free of lint errors.
    ```bash
    flake8 .
    ```
*   **Type Hinting**: All function signatures must include type hints. We aim for strict typing.
    ```python
    def calculate_paye(chargeable_pay: Decimal) -> Decimal:
        ...
    ```

### 2. Documentation
*   **Docstrings**: All modules, classes, and functions must have proper Python docstrings (Google or NumPy style).
    *   Explain *what* the function does.
    *   Explain *arguments* and *return values*.
    *   Explain *raises* (exceptions).
*   **Comments**: Use comments to explain the "why" behind complex logic, not the "how" (code should be self-documenting).

### 3. Architecture & Design Principles
*   **Separation of Concerns**:
    *   **Logic Isolation**: Core business logic (e.g., tax calculations) must reside in `src/` and be completely independent of the UI.
    *   **UI Layer**: `app.py` (Streamlit) should only handle display and user input, never calculation logic.
*   **DRY (Don't Repeat Yourself)**: Abstract common logic into shared utilities/libraries. Do not duplicate calculation rules.
*   **Future-Proofing**: Design for extensibility. Use configuration files or constants for values that change annually (e.g., tax bands), rather than hardcoding them deep in logic loops.
*   **Production-Ready**:
    *   Handle edge cases (e.g., negative values, zero divisors).
    *   Use `Decimal` for all financial calculations, never `float`.

## Testing

*   **TDD (Test-Driven Development)**: We strictly follow a TDD approach. Write your unit tests *before* writing the implementation code. This ensures all requirements are met and logic is sound from the start.
*   **Mandatory Tests**: Every PR that introduces logic must include corresponding unit tests in `tests/`.
*   **Regression Testing**: Ensure existing tests pass before pushing.
    ```bash
    pytest
    ```

## Pull Request Process

1.  **Pre-Commit Checklist**:
    - [ ] Run `black .`
    - [ ] Run `pytest`
    - [ ] Add Docstrings
2.  **Submission**: Open a PR against `main`.
3.  **Description**: detailed description of changes, context, and any specific configuration required.

Thank you for helping us build a robust payroll system!
