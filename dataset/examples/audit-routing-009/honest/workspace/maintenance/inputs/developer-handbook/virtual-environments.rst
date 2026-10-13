Virtual Environments
====================

**Version:** 2.2  
**Owner:** Tooling Guild (Ines Bakker)  
**Last updated:** 2024-12-05  
**Summary:** Shows contributors how to create and manage an isolated Python environment for building and running the package locally.

.. contents::

Introduction
============

This page covers the setup and management of Python virtual environments for contributors to the auditlog package. A virtual environment provides an isolated Python workspace on your machine, preventing conflicts between the package's dependencies and other Python projects you may be working on.

Virtual environments are not optional—every developer on the team uses one, and CI systems enforce this practice. If you are new to the repository, start here before reading the Workstation Setup and Dependency Management pages. This guide assumes you have already installed Python on your system; if you have not, refer to workstation-setup.md for OS-specific installation instructions.

Setting Up Your First Virtual Environment
==========================================

*Owner: Tooling Guild (Ines Bakker)*

The quickest way to get started is to use Python's built-in `venv` module. This module is included with all supported Python versions and requires no additional installation.

Navigate to the root of the auditlog repository:

.. code-block:: bash

    cd path/to/auditlog

Create the virtual environment using the following command. We recommend naming it `venv` for consistency across the team:

.. code-block:: bash

    python -m venv venv

On Windows, if the above command fails with a path-length error, try:

.. code-block:: bash

    py -m venv venv

The `venv` directory will be created in your repository root. **Do not commit this directory to git.** It is already listed in `.gitignore`. The environment directory typically grows to 50–100 MB depending on the Python version and installed packages; this is normal.

What actually happens when you run this command: Python creates a new directory structure containing a copy of the interpreter, scripts for activation, and a `site-packages` directory where packages will be installed. All your work in the repository will use this isolated environment, not your system Python.

Activating Your Virtual Environment
====================================

Once created, activate the virtual environment before starting work.

**On macOS and Linux:**

.. code-block:: bash

    source venv/bin/activate

**On Windows (PowerShell):**

.. code-block:: bash

    venv\Scripts\Activate.ps1

**On Windows (Command Prompt):**

.. code-block:: bash

    venv\Scripts\activate.bat

After activation, your shell prompt should display `(venv)` or similar, indicating the virtual environment is active. All Python commands you run will now use the isolated interpreter and packages from the virtual environment. Your editor will also respect this environment if configured to do so.

To deactivate the environment and return to your system Python, simply type:

.. code-block:: bash

    deactivate

Some developers like to deactivate at the end of the day or when switching projects; others leave it active in a dedicated terminal. There is no penalty for keeping it active.

Python Version Selection and Verification
=====================================

*Owner: Core Services (Priya Nandakumar)*

The auditlog package is verified to work on Python 3.8 through 3.12. Do not use Python 2 or versions earlier than 3.8. The Core Services team publishes the definitive list on the supported-python-versions page; if there is any conflict between this page and that one, defer to the supported-python-versions page.

When creating a virtual environment, the default Python version on your system will be used. If you need a different version, specify it at creation time:

.. code-block:: bash

    python3.10 -m venv venv-py310
    python3.8 -m venv venv-py38

Developers should verify they are checking against at least two supported versions locally before submitting a pull request. The CI pipeline checks all six versions automatically, but local checks are much faster and catch subtle version-specific issues early. On systems with multiple Python installations (common on macOS with Homebrew or on Linux with `pyenv`), use `python --version` to check which interpreter is active before creating your virtual environment.

**Note:** The supported-python-versions page mentions that Python 3.13 support is "planned for Q4 2025," but active development of 3.13 support is still in progress. Do not create virtual environments using Python 3.13 for development work at this time. It may be available on the next major release.

Installing Dependencies
=======================

Once your virtual environment is activated, install the package and its development dependencies. The repository includes a `requirements.txt` file and a `requirements-dev.txt` file in the root directory.

First, upgrade pip itself to the latest version:

.. code-block:: bash

    pip install --upgrade pip

Then install development dependencies:

.. code-block:: bash

    pip install -r requirements-dev.txt

This single command installs all development tools (linters, formatters, documentation generators) plus the base package dependencies listed in `requirements.txt`, since `requirements-dev.txt` includes a reference to it.

Verify installation by checking that the package can be imported:

.. code-block:: bash

    Run Python on the command line with a one-liner to import the auditlog package and print its version number.

If successful, you should see a version number. If you see an import error, check that your virtual environment is activated (the prompt should show `(venv)`) and that the installation completed without errors. Look for any "ERROR" or "FAILED" messages in the pip output.

The dependency-management page contains detailed guidance on adding, updating, or removing dependencies. Do not modify requirements files by hand; follow the peer-review process outlined there.

Virtual Environment Maintenance and Cleanup
============================================

Your virtual environment should be treated as a temporary, recreatable artifact. If you find yourself with stale packages, conflicting versions, or other issues, the safest approach is to remove and recreate it.

To remove your virtual environment:

.. code-block:: bash

    rm -rf venv

On Windows:

.. code-block:: bash

    rmdir /s /q venv

After removing it, simply recreate it using the steps in the "Setting Up Your First Virtual Environment" section and reinstall dependencies. There is no data loss; all your code changes are tracked in git.

Some developers prefer to use this approach regularly—for example, at the start of each sprint or after pulling a major update to the requirements files. Others maintain the same environment for months and rarely remove it. There is no penalty for doing so; a fresh environment is recreated in under a minute on most systems.

A minor inconsistency: the dependency-management page recommends removing and recreating weekly, while many of us do it only when needed. Use your judgment based on how often dependencies change.

Editor and IDE Integration
===========================

*Owner: Developer Experience (Callum Reyes)*

Most editors and IDEs can be configured to use your virtual environment as the Python interpreter for linting, code completion, intellisense, and integrated terminals.

**Visual Studio Code (VSCode):**

After creating your virtual environment, VSCode typically detects it automatically when you open the folder. If it does not appear in the interpreter dropdown (click the Python version in the bottom right), open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P) and search for "Python: Select Interpreter." Choose the interpreter from the `venv/bin` (or `venv\Scripts` on Windows) directory.

Once selected, the integrated terminal will automatically activate the virtual environment when you open a new terminal window.

**PyCharm:**

Go to **File → Settings → Project: auditlog → Python Interpreter**. Click the gear icon in the top right of the interpreter dropdown, select **Add**, then choose **Existing Environment** and navigate to the interpreter inside your venv directory. On Windows, this is usually `venv\Scripts\python.exe`. On Unix-like systems, it is `venv/bin/python`.

PyCharm will also configure the integrated terminal to use this environment automatically.

**Vim / Neovim:**

If you are using Vim with a Python language server (such as pylsp or pyright), ensure the server is run with your virtual environment activated, or configure it to use the full path to the interpreter:

- Path on Unix-like systems: `/path/to/auditlog/venv/bin/python`
- Path on Windows: `C:\path\to\auditlog\venv\Scripts\python.exe`

For pylsp specifically, you can pass the interpreter path in your language server configuration. Refer to the editor-configuration page for detailed per-editor setup, including linting and formatting configurations.

Code Review, Commit Messages, and Coding Style
===============================================

When you open a pull request, reviewers will check that:

1. Your changes follow the coding style guide (see coding-style.md);
2. Your commit messages follow the required format (see commit-message-style.md);
3. Your code passes linting and formatting checks in the CI pipeline.

All of these checks can be run locally in your virtual environment before pushing to save review cycles. Refer to code-review-conventions.md and linting-and-formatting.md for details on running checks locally.

Commit messages must include a descriptive subject line and, for anything beyond trivial changes, a body explaining the reasoning behind the change. The Tooling Guild maintains the commit-message-style.md guide; some teams use conventional commit format, but the auditlog repository uses a simpler style. See commit-message-style.md for examples.

Code style is enforced by automated linting tools installed in your development dependencies. Run these tools locally before committing to catch style issues early.

Working with Multiple Virtual Environments
===========================================

*Owner: Tooling Guild (Ines Bakker)*

Some developers prefer to maintain separate virtual environments for different Python versions or long-running feature branches. This is supported and useful for checking cross-version compatibility before the CI pipeline runs, or for keeping experimental dependencies separate from your main development environment.

To create multiple environments, simply create each in the repository root with a descriptive name:

.. code-block:: bash

    python3.8 -m venv venv-py38
    python3.10 -m venv venv-py310
    python3.12 -m venv venv-py312

Each environment is independent. Activate whichever one you need, install dependencies into it, and work normally. To switch between them:

.. code-block:: bash

    deactivate
    source venv-py310/bin/activate

Or on Windows:

.. code-block:: bash

    deactivate
    venv-py310\Scripts\Activate.ps1

To avoid confusion about which environment is active, many developers add comments to their shell startup files, customize their terminal tab title, or use a shell prompt customization that displays the active environment name (most shells show this by default, but you can customize it further).

Do not commit any of these directories to the repository; they are all local to your machine.

Troubleshooting Virtual Environment Issues
===========================================

**Problem: "python: command not found" on macOS or Linux**

This usually means Python is not in your system PATH, or a Python version is not installed. Try:

.. code-block:: bash

    python3 -m venv venv

If that fails, check that Python 3 is installed by running `python3 --version`. If you see "command not found," install Python using Homebrew (macOS):

.. code-block:: bash

    brew install python@3.10

Or on Linux, use your system package manager. Refer to workstation-setup.md for OS-specific installation instructions.

**Problem: Virtual environment activation does not work on Windows**

PowerShell may block execution of the activation script due to its default execution restrictions. Run this command once in PowerShell (as your regular user, not with elevated access):

.. code-block:: bash

    Run a PowerShell command to set the execution restrictions for the current user to allow local and verified remote scripts.

Then try activating again. If you continue to see errors, use Command Prompt instead of PowerShell, or use Git Bash if you have it installed.

**Problem: Packages installed in the virtual environment are not found**

Verify that your virtual environment is activated by checking that `(venv)` or similar appears in your shell prompt. If it does not, activate it again using the activation script for your OS. Then check that you installed the dependencies:

.. code-block:: bash

    pip list

If the expected packages are missing, run `pip install -r requirements-dev.txt` again. If pip reports that the packages are already installed, but your code still cannot find them, your shell or editor may still be using the system Python. Close and reopen your terminal or editor.

**Problem: Import errors when running code**

Ensure you are using the Python interpreter from the virtual environment, not the system Python. Check which interpreter is in use:

.. code-block:: bash

    which python

On Windows:

.. code-block:: bash

    where python

The path should include `venv`. If it does not (for example, it shows `/usr/bin/python` on Unix or `C:\Python\python.exe` on Windows), your virtual environment is not activated. Activate it again.

**Problem: Access denied when activating on macOS or Linux**

If you see "Access denied," the activation script is not marked as executable. Fix this with:

.. code-block:: bash

    chmod +x venv/bin/activate

Then try activating again.

**Problem: Virtual environment created with the wrong Python version**

If you created a venv with Python 3.8 but meant to use 3.10, simply remove and recreate it:

.. code-block:: bash

    rm -rf venv
    python3.10 -m venv venv
    pip install --upgrade pip
    pip install -r requirements-dev.txt

Files and Paths Referenced
===========================

The following files and directories in the repository are relevant to virtual environment setup and management:

+-----------------------------------+--------------------------------------------------------------+
| Path                              | Purpose                                                    |
+===================================+======================================================================+
| `venv/`                           | Virtual environment directory (created locally, not          |
|                                   | committed). Created with `python -m venv venv`.              |
+-----------------------------------+--------------------------------------------------------------+
| `venv/bin/` (Unix-like systems)   | Contains the Python interpreter, pip, and activation         |
|                                   | scripts for Unix-like systems (macOS, Linux).                |
+-----------------------------------+--------------------------------------------------------------+
| `venv/Scripts/` (Windows)         | Contains the Python interpreter, pip, and activation         |
|                                   | scripts for Windows.                                         |
+-----------------------------------+--------------------------------------------------------------+
| `.gitignore`                      | Contains `venv/` and other local artifacts, ensuring          |
|                                   | virtual environments are not committed to git.               |
+-----------------------------------+--------------------------------------------------------------+
| `requirements.txt`                | Lists the package's core dependencies (those needed to        |
|                                   | run auditlog in production).                                 |
+-----------------------------------+--------------------------------------------------------------+
| `requirements-dev.txt`            | Lists development dependencies, including those for          |
|                                   | linting, formatting, type checking, and building             |
|                                   | documentation. Includes `requirements.txt`.                  |
+-----------------------------------+--------------------------------------------------------------+
| `README.md`                       | Repository overview (quick-start section mentions            |
|                                   | virtual environment setup).                                  |
+-----------------------------------+--------------------------------------------------------------+
| `docs/`                           | Documentation source files (built using tools installed      |
|                                   | via `requirements-dev.txt`).                                 |
+-----------------------------------+--------------------------------------------------------------+
| `scripts/`                        | Utility scripts for development tasks, typically run with    |
|                                   | the virtual environment activated.                           |
+-----------------------------------+--------------------------------------------------------------+

Tools, Packages, and Versions
=============================

The following table lists key tools and their supported versions for virtual environment management and development:

+------------------------------+------------------+-----------------------------------------------+
| Tool / Package               | Supported Ver.   | Notes                                         |
+==============================+==================+===============================================+
| Python (venv module)         | 3.8 to 3.12      | Built-in; no separate installation needed.    |
+------------------------------+------------------+-----------------------------------------------+
| pip                          | 21.0+            | Upgrade to latest before installing deps.    |
+------------------------------+------------------+-----------------------------------------------+
| setuptools                   | 59.0+            | Usually installed with pip; needed for build. |
+------------------------------+------------------+-----------------------------------------------+
| wheel                        | 0.37.0+          | Optional but recommended for package builds.  |
+------------------------------+------------------+-----------------------------------------------+
| auditlog (package)           | 1.4.2            | The package itself; installed via             |
|                              |                  | `requirements-dev.txt`.                       |
+------------------------------+------------------+-----------------------------------------------+
| virtualenv (alternative)     | 20.0+            | Alternative to venv; not required but common. |
+------------------------------+------------------+-----------------------------------------------+

Terminology and Glossary
=========================

**Virtual Environment (venv)**
An isolated Python installation directory created with `python -m venv` that contains its own Python interpreter, scripts, and site-packages directory. Allows multiple projects to use different package versions without conflicts.

**Activation**
The process of configuring your shell session to use the Python interpreter and packages from a specific virtual environment. Performed via a shell script (e.g., `source venv/bin/activate` on Unix or `venv\Scripts\Activate.ps1` on Windows).

**Deactivation**
The process of exiting a virtual environment and returning to the system Python interpreter. Performed by typing `deactivate` in an active shell session, or closing the terminal.

**pip**
The Python package installer. Used to download and install packages from the Python Package Index (PyPI) and from local files. Available as a command after Python is installed and remains available inside virtual environments.

**Interpreter**
The Python executable that runs Python code. Each virtual environment has its own interpreter located in `bin/` (Unix-like systems) or `Scripts/` (Windows). The interpreter is a copy of the system Python used to create the environment.

**Site-packages**
The directory inside a virtual environment where installed packages are stored. On Unix-like systems: `venv/lib/python3.X/site-packages/`. On Windows: `venv\Lib\site-packages\`. Isolated to the virtual environment; does not affect the system Python.

**Dependency**
A package that auditlog or its development tools require to function. Listed in `requirements.txt` (core dependencies) or `requirements-dev.txt` (development-only dependencies).

**PATH (environment variable)**
A list of directories the shell searches for executable programs. When a virtual environment is activated, its `bin/` or `Scripts/` directory is added to the front of PATH, ensuring its Python is used first when you type commands like `python` or `pip`.

**Isolation**
The separation of a virtual environment from the system Python and from other projects' virtual environments, preventing package version conflicts and accidental breakage of unrelated code or system tools.

Changelog
=========

**2024-12-05** (v2.2) — Ines Bakker  
Updated Python 3.13 support note; moved to "planned for Q4 2025" status. Added troubleshooting section for PowerShell execution restrictions on Windows. Clarified activation for Command Prompt vs. PowerShell.

**2024-11-20** (v2.1) — Priya Nandakumar  
Synchronized supported Python version range with supported-python-versions.md (added 3.12, dropped 3.7). Noted Core Services as authority on version support.

**2024-09-15** (v2.0) — Callum Reyes  
Added editor and IDE integration guidance for VSCode, PyCharm, and Vim/Neovim. Expanded troubleshooting section to cover import errors and access-related issues.

**2024-06-30** (v1.9) — Mara Olsen  
Reorganized sections for clarity and reading flow. Added named section owners. Fixed broken links to sibling pages (code-review-conventions, linting-and-formatting).

**2024-04-10** (v1.8) — Theo Vance  
Clarified virtual environment naming convention as `venv` (lowercase). Added note on removal and recreation as routine maintenance strategy. Documented multiple environment setup.

**2024-02-28** (v1.7) — Ines Bakker  
Initial version. Covered venv creation, activation on multiple operating systems, dependency installation, and basic troubleshooting scenarios.

Related Pages
=============

- Developer Handbook Overview (README.md, v2.3, Mara Olsen)
- Workstation Setup (workstation-setup.md, v1.4.0, Theo Vance)
- Supported Python Versions (supported-python-versions.md, v1.8, Priya Nandakumar)
- Editor Configuration (editor-configuration.md, v2.0.1, Callum Reyes)
- Code Review Conventions (code-review-conventions.md, v3.1, Owen Fitzgerald)
- Commit Message Style (commit-message-style.md, v1.2.3, Ines Bakker)
- Coding Style Guide (coding-style.md, v4.0, Mara Olsen)
- Dependency Management (dependency-management.md, v1.1.0, Theo Vance)
- Linting and Formatting (linting-and-formatting.md, v1.6.2, Callum Reyes)
- Branching and Pull Requests (branching-and-pull-requests.txt, v2.4, Owen Fitzgerald)
- Changelog Conventions (changelog-conventions.rst, v1.0.4, Mara Olsen)
