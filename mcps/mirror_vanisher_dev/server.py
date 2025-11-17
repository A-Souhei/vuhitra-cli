#!/usr/bin/env python3
"""
Stdio MCP Server for Mirror+Vanisher Development Operations

This MCP server provides tools for LLM-driven development operations on
directories that are both mirrored (synced to sandbox) and vanishers (loaded in context).

It implements all operations from the pillars methodology:
- Exploration, Architecture Analysis, Chunking, Planning
- Code Generation, Testing, Quality Checks, Security Scanning
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from exploration import ExplorationTools
from architecture import ArchitectureTools
from chunking import ChunkingTools
from planning import PlanningTools
from code_generation import CodeGenerationTools
from testing import TestingTools
from quality_checks import QualityCheckTools
from security import SecurityTools
from mirror_vanisher import MirrorVanisherManager
from llm_plan_generator import LLMPlanGenerator
from errors_handler import handle_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Stdio MCP Server for development operations on mirror+vanisher directories."""

    def __init__(self):
        """Initialize the MCP server and all tool modules."""
        self.manager = MirrorVanisherManager()

        # Initialize all tool modules
        self.exploration = ExplorationTools(self.manager)
        self.architecture = ArchitectureTools(self.manager)
        self.chunking = ChunkingTools(self.manager)
        self.planning = PlanningTools(self.manager)
        self.code_generation = CodeGenerationTools(self.manager)
        self.testing = TestingTools(self.manager)
        self.quality = QualityCheckTools(self.manager)
        self.security = SecurityTools(self.manager)
        self.llm_planner = LLMPlanGenerator(self.manager)

        # Tool registry
        self.tools = self._register_tools()
        self.resources = self._register_resources()

        logger.info("MCP Server initialized with all tool modules")

    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools."""
        return {
            # Mirror+Vanisher Management
            "list_mirror_vanishers": {
                "description": "List and enumerate all directories that are simultaneously mirrors (synced to sandbox) and vanishers (loaded into LLM context). Use this when you need to discover available projects, see what codebases are ready for development operations, check which directories are properly configured for mirror+vanisher workflows, or find projects to work on. Returns directory names, paths, file counts, and synchronization status for each mirror+vanisher combination.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "handler": self.manager.list_mirror_vanishers
            },
            "verify_mirror_vanisher": {
                "description": "Verify and validate that a specific directory is correctly configured as both a mirror (synced to sandbox) and a vanisher (loaded into LLM context). Use this before starting any development work to confirm proper setup, check if a directory meets mirror+vanisher requirements, troubleshoot configuration issues, or validate that both mirroring and vanisher loading are active. Provides detailed status including mirror existence, vanisher loading state, directory type validation, and specific reasons for any failures.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to verify"}
                    },
                    "required": ["path"]
                },
                "handler": self.manager.verify_mirror_vanisher
            },

            # Step 1: Exploration Tools
            "explore_structure": {
                "description": "Explore and visualize the hierarchical directory structure and file organization of a codebase using a tree view representation. Use this when you need to understand how a project is organized, see the folder hierarchy, identify directory patterns, examine file layout, navigate large codebases, or get an overview of project structure before making changes. Generates a recursive tree showing directories and files up to a configurable depth, filtering out common ignored directories like node_modules, __pycache__, .git, and hidden files. Returns tree structure with file counts and directory statistics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to explore"},
                        "max_depth": {"type": "integer", "description": "Maximum depth", "default": 3}
                    },
                    "required": ["path"]
                },
                "handler": self.exploration.explore_structure
            },
            "detect_tech_stack": {
                "description": "Detect and identify the technology stack, programming languages, frameworks, and build tools used in a codebase. Use this when you need to understand what technologies a project uses, identify the primary programming language, discover frameworks and libraries, find build tools and package managers, assess technology choices, or prepare for development work. Analyzes file extensions to detect languages (Python, JavaScript, TypeScript, Java, Go, Rust, etc.), identifies configuration files (package.json, requirements.txt, Cargo.toml, pom.xml, etc.) to detect frameworks (Node.js, Flask, React, etc.), and discovers build tools (Make, Docker, Maven, Gradle, etc.). Returns comprehensive report with language breakdown, framework list, build tool identification, and configuration file locations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to analyze"}
                    },
                    "required": ["path"]
                },
                "handler": self.exploration.detect_tech_stack
            },
            "find_entrypoints": {
                "description": "Find and locate main entrypoints, executable files, and program starting points in a codebase. Use this when you need to discover how to run the application, find the main files that start execution, locate executable scripts, identify program entry points, understand application startup, or find files with main() functions. Searches for common entrypoint filenames (main.py, app.py, index.js, main.go, etc.), detects Python files with __main__ blocks, identifies executable files with execution permissions, and categorizes entrypoints by type (named entrypoint, Python main block, executable script, etc.). Returns list of entrypoints with file paths, types, and execution information.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to search"}
                    },
                    "required": ["path"]
                },
                "handler": self.exploration.find_entrypoints
            },
            "full_exploration": {
                "description": "Perform comprehensive and complete codebase exploration by running all exploration operations together: directory structure visualization, technology stack detection, and entrypoint discovery. Use this as the first step when starting work on any unfamiliar codebase, when you need a complete overview before implementing features, to understand a project thoroughly before refactoring, when analyzing a new codebase for the first time, or when you want all exploration data in one operation. Executes explore_structure, detect_tech_stack, and find_entrypoints sequentially, combining their results into a unified exploration report. Returns comprehensive analysis including tree structure, file/directory statistics, primary language, complete language breakdown, frameworks, build tools, all entrypoints, and a summary with key metrics. This is the recommended starting point for any development workflow.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to explore"},
                        "max_depth": {"type": "integer", "description": "Maximum depth", "default": 3}
                    },
                    "required": ["path"]
                },
                "handler": self.exploration.full_exploration
            },

            # Step 2: Architecture Tools
            "analyze_architecture": {
                "description": "Analyze and identify architectural patterns, software design approaches, and structural organization in a codebase. Use this when you need to understand the architecture style (MVC, microservices, layered, clean/hexagonal, feature-based), plan refactoring to align with architectural patterns, assess code organization quality, determine if the project follows architectural best practices, or understand system design before making significant changes. Detects common patterns by analyzing directory structure (models/views/controllers for MVC, services for microservices, domain/application/infrastructure for Clean Architecture), identifies layered architecture (services, repositories, DAO, models), recognizes feature-based organization, and checks for tests, documentation, configuration, and scripts directories. Returns architecture type, detected patterns, directory list, and detailed analysis of project organization.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to analyze"}
                    },
                    "required": ["path"]
                },
                "handler": self.architecture.analyze_architecture
            },
            "map_dependencies": {
                "description": "Map and analyze dependencies, imports, and relationships between modules, files, and components in a codebase. Use this when you need to understand code coupling, identify which files depend on which, analyze module relationships, find circular dependencies, plan refactoring to reduce coupling, understand data flow between components, or create dependency graphs. Scans Python files for import statements (from/import), extracts module names and dependencies, builds a comprehensive dependency map showing what each file imports, and calculates dependency statistics (total dependencies per file, overall dependency count). Returns detailed dependency map with file-to-imports relationships, file count, and total dependency metrics. Useful for understanding codebase interconnections and planning modular changes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to analyze"}
                    },
                    "required": ["path"]
                },
                "handler": self.architecture.map_dependencies
            },
            "identify_patterns": {
                "description": "Identify and recognize software design patterns used in the codebase such as Singleton, Factory, Strategy, Observer, Decorator, and other Gang of Four patterns. Use this when you need to understand what design patterns are implemented, assess code design quality, find examples of specific patterns, plan refactoring to use appropriate patterns, understand architectural decisions, or learn from existing pattern implementations. Searches for pattern indicators in file names (singleton, factory, strategy, observer, decorator, listener, etc.), identifies potential pattern usage, and catalogs all discovered patterns with their locations. Returns list of identified patterns with file paths and pattern types. Helpful for understanding design sophistication and recognizing reusable design solutions in the code.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to analyze"}
                    },
                    "required": ["path"]
                },
                "handler": self.architecture.identify_patterns
            },

            # Step 3: Chunking Tools
            "chunk_file": {
                "description": "Break down and divide a large source code file into smaller, manageable, overlapping chunks for analysis or processing. Use this when you need to handle files that exceed context window limits, process large files in smaller pieces, analyze specific sections of very long files, work with files over 500-1000 lines, or prepare code for chunk-by-chunk review. Splits file by lines with configurable chunk size and overlap, creates sequential chunks with line number tracking, ensures context preservation through overlap, and maintains readability. Returns array of chunks with chunk numbers, start/end line numbers, line counts, and full content for each chunk. Configurable chunk size (default 100 lines) and overlap (default 10 lines) allow flexible chunking strategies. Essential for handling large codebases that don't fit in single context windows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to chunk"},
                        "chunk_size": {"type": "integer", "description": "Lines per chunk", "default": 100},
                        "overlap": {"type": "integer", "description": "Overlap lines", "default": 10}
                    },
                    "required": ["file_path"]
                },
                "handler": self.chunking.chunk_file
            },
            "chunk_directory": {
                "description": "Analyze an entire directory and create a comprehensive chunking strategy identifying which files need to be split into chunks due to size. Use this when you need to plan how to process a large codebase, identify files that exceed size limits, create a processing strategy for large projects, understand which files need chunking before analysis, or prepare a systematic approach for reviewing code. Scans all files in directory recursively, measures file sizes in lines, categorizes files as large (need chunking) or small (processable as-is), calculates estimated chunk counts for large files, and provides statistics. Returns files needing chunks (with line counts and estimated chunk numbers), small files list, and summary statistics (total large files, total small files). Configurable max_file_size threshold (default 500 lines) determines the chunking boundary. Critical for planning large codebase analysis workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory to analyze"},
                        "max_file_size": {"type": "integer", "description": "Max file size in lines", "default": 500}
                    },
                    "required": ["path"]
                },
                "handler": self.chunking.chunk_directory
            },

            # Step 4: Planning Tools
            "create_plan": {
                "description": "Create detailed, atomic, and file-specific implementation plans for development tasks including feature implementation, bug fixes, or refactoring. Use this when you need to plan how to implement a feature, create step-by-step approach for bug fixes, organize refactoring work, break down complex tasks into manageable steps, identify files to modify, define testing requirements, or establish clear implementation roadmap. Analyzes task description to automatically detect task type (bugfix, refactoring, feature_implementation, general), generates appropriate step-by-step plan with specific actions and details for each step, identifies potential risks and considerations, defines testing requirements (unit tests, integration tests, edge cases), and incorporates context from exploration and architecture analysis. Returns comprehensive plan with task type, ordered steps with actions and details, estimated files to modify, potential risks, and testing requirements. Plans are tailored to task type with specific recommendations (e.g., bug fixes include test reproduction steps, refactoring includes behavior preservation verification, features include API design and documentation).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory"},
                        "task": {"type": "string", "description": "Task description"},
                        "context": {"type": "object", "description": "Additional context"}
                    },
                    "required": ["path", "task"]
                },
                "handler": self.planning.create_plan
            },
            "validate_plan": {
                "description": "Validate and verify that an implementation plan is complete, feasible, and well-structured before execution. Use this when you need to check if a plan has all necessary steps, verify plan completeness before starting work, identify missing elements in implementation plans, ensure plans have proper structure, validate testing requirements are defined, or catch planning issues early. Checks for required plan fields (task, steps, testing_requirements), validates step structure (action, details, proper numbering), identifies missing information, flags warnings about incomplete sections, and provides detailed validation results. Returns validation status (valid/invalid), list of critical issues that must be fixed, list of warnings for improvements, and clear validation message. Ensures plans are thorough before development begins, preventing incomplete or poorly thought-out implementations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {"type": "object", "description": "Plan to validate"}
                    },
                    "required": ["plan"]
                },
                "handler": self.planning.validate_plan
            },
            "generate_llm_plan": {
                "description": "Generate comprehensive, AI-powered implementation plans using Ollama (local LLM) with context from loaded vanisher, pillars methodology, and MCP tool recommendations. Use this when you receive a [plan] prefix in user prompts, need intelligent plan generation based on codebase analysis, want automatic tool recommendations for each step, require context-aware planning with embeddings, need plans that follow the 8-pillar methodology, or want to leverage AI to create detailed implementation strategies with complete privacy. REQUIRES a vanisher of directory type to be loaded. Uses local Ollama (configured in config.yaml) for offline, private plan generation. Validates vanisher is loaded and is directory type, loads pillars documentation (especially Step 4: Planning), analyzes MCP tool descriptions and creates embeddings, reads vanisher context (file list and sample content), calls Ollama with preferred coding model (qwen2.5-coder:7b or llama3.1:8b) to generate comprehensive plan, enhances plan steps with relevant tool recommendations using semantic similarity, and provides detailed metadata about plan generation. Returns success status, generated plan with type/task/steps/files/testing/risks, tool recommendations per step based on embeddings, and metadata about context used. Plan includes: task type detection (bugfix/refactoring/feature/general), atomic file-specific steps with actions/details/verification, estimated files to modify, testing requirements, potential risks, and MCP tools suggested for each pillar step. This is the most advanced planning tool - use it when you want AI-assisted comprehensive planning with complete privacy using local LLMs and no API keys required.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description from user (after [plan] prefix)"},
                        "path": {"type": "string", "description": "Path to the loaded vanisher directory"}
                    },
                    "required": ["task", "path"]
                },
                "handler": lambda task, path: self.llm_planner.generate_plan(task, path, self.tools)
            },

            # Step 5: Code Generation Tools
            "generate_diff": {
                "description": "Generate safe, reviewable code diffs showing proposed changes to a file before applying them. Use this when you need to preview changes before modifying files, create diffs for code review, see what will change before committing, generate patches for specific modifications, plan code changes safely, or prepare changes for approval. Analyzes original file content, creates diff preview structure, performs safety checks (file exists, writable, needs backup), validates file accessibility, and provides change metadata. Returns diff generation status, file path, change description, original line count, safety check results (file existence, writability, backup recommendation), and preparation message. This is a planning/preview tool - use apply_changes to actually modify files. Critical for safe code modification workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to modify"},
                        "changes": {"type": "string", "description": "Description of changes"},
                        "context": {"type": "object", "description": "Additional context"}
                    },
                    "required": ["file_path", "changes"]
                },
                "handler": self.code_generation.generate_diff
            },
            "apply_changes": {
                "description": "Apply code changes and modifications to files with automatic safety checks including backup creation and dry-run preview capability. Use this when you need to modify source code files, implement planned changes, apply generated diffs, update code safely with automatic backups, test changes with dry-run mode before committing, or make production code modifications. Creates automatic timestamped backups before modifications, supports dry-run mode for previewing without changes, validates file existence and permissions, applies diffs or direct modifications, and tracks backup locations. Returns success status, file path modified, backup file path (with timestamp), dry-run indicator if previewing, and operation result message. Use dry_run=true to preview changes without modifying files. Essential safety tool for code modification workflows ensuring changes can always be reverted.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to modify"},
                        "diff": {"type": "string", "description": "Diff to apply"},
                        "dry_run": {"type": "boolean", "description": "Preview only", "default": False}
                    },
                    "required": ["file_path", "diff"]
                },
                "handler": self.code_generation.apply_changes
            },
            "rewrite_file": {
                "description": "Completely replace and rewrite entire file contents with new content while maintaining safety through automatic backup creation. Use this when you need to completely replace file content, rewrite files from scratch, update configuration files entirely, regenerate source files, replace implementations completely, or make comprehensive file changes. Creates automatic timestamped backup of original content (optional but recommended), writes entirely new content to file, validates file paths and permissions, tracks backup locations, and handles encoding properly. Returns success status, file path, backup path (if created), new line count, and completion message. Unlike apply_changes which applies diffs, this tool performs complete file replacement. Critical for major file updates while maintaining ability to restore original content. Default creates backups (backup=true) to prevent data loss.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to rewrite"},
                        "new_content": {"type": "string", "description": "New file content"},
                        "backup": {"type": "boolean", "description": "Create backup", "default": True}
                    },
                    "required": ["file_path", "new_content"]
                },
                "handler": self.code_generation.rewrite_file
            },

            # Step 6: Testing Tools
            "generate_tests": {
                "description": "Generate test templates, test file structures, and testing recommendations for source code files or functions. Use this when you need to create unit tests for new code, generate integration test structures, build edge case test templates, establish testing frameworks for untested code, create test files following best practices, or get testing recommendations for specific test types. Detects appropriate test framework (pytest, unittest for Python; jest, mocha for JavaScript), generates test file paths following naming conventions (test_*.py, *.test.js), creates test templates based on test type (unit, integration, edge cases), provides framework-specific recommendations, and suggests testing strategies. Returns test generation status, source file path, generated test file path, test type (unit/integration/edge), detected test framework, and detailed recommendations for the test type. Supports unit testing (isolated function tests with mocks), integration testing (component interaction tests), and edge case testing (boundary conditions, error scenarios). Foundation for comprehensive test coverage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to test"},
                        "test_type": {"type": "string", "enum": ["unit", "integration", "edge"], "default": "unit"}
                    },
                    "required": ["file_path"]
                },
                "handler": self.testing.generate_tests
            },
            "run_tests": {
                "description": "Execute and run automated tests in a directory or file using the appropriate testing framework with support for pytest, unittest, jest, and mocha. Use this when you need to verify code functionality, check if tests pass, validate recent changes, ensure no regressions, run continuous integration checks, execute test suites, or verify implementation correctness. Automatically detects testing framework (pytest.ini/pyproject.toml for pytest, jest.config.js for jest, etc.), runs framework-specific test commands, captures stdout and stderr output, reports test results with pass/fail status, shows exit codes, and handles timeouts. Returns test execution success status, framework used, exit code (0 for success), complete stdout output, stderr output, and result message. Supports verbose output, test discovery, and framework auto-detection. Essential for test-driven development and continuous validation workflows. Helps ensure code quality and catch bugs early.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory or file to test"},
                        "test_framework": {"type": "string", "description": "Test framework (auto-detect if not provided)"}
                    },
                    "required": ["path"]
                },
                "handler": self.testing.run_tests
            },
            "verify_changes": {
                "description": "Verify and validate code changes by automatically finding and running relevant tests for modified files. Use this when you need to check if changes broke existing functionality, run tests related to specific file modifications, verify changes before committing, execute targeted tests for changed files, ensure modifications don't cause regressions, or get quick feedback on recent changes. Finds test files related to changed files (test_*.py for *.py files), runs tests only for modified files (not entire suite), reports results per changed file, identifies files without tests, and provides aggregated pass/fail status. Returns verification success status, whether all tests passed, results array with test outcomes per file, count of files tested, and count of files without tests. More efficient than running entire test suite - focuses on relevant tests for changed code. Critical for rapid development iteration with confidence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "files_changed": {"type": "array", "items": {"type": "string"}, "description": "Changed files"}
                    },
                    "required": ["files_changed"]
                },
                "handler": self.testing.verify_changes
            },

            # Step 7: Quality Check Tools
            "run_linter": {
                "description": "Run static code analysis linters to detect code quality issues, style violations, potential bugs, and anti-patterns with optional auto-fix capability. Use this when you need to check code quality, identify style violations, find potential bugs before runtime, enforce coding standards, clean up code formatting issues automatically, or prepare code for review. Automatically detects and uses appropriate linter (ruff/flake8 for Python, eslint for JavaScript/TypeScript), runs linting analysis on files/directories, supports automatic fixing of violations (--fix flag), captures linting output and issues, reports violation counts, and provides detailed linting results. Returns linting success status (clean code or issues found), linter used, exit code, stdout with violations, stderr output, whether auto-fix was applied, and result message. Supports ruff (fast modern Python linter), flake8 (traditional Python linter), and eslint (JavaScript/TypeScript linter). Essential for maintaining code quality and consistency.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to lint"},
                        "fix": {"type": "boolean", "description": "Auto-fix issues", "default": False}
                    },
                    "required": ["path"]
                },
                "handler": self.quality.run_linter
            },
            "run_formatter": {
                "description": "Run automatic code formatters to standardize code style, fix formatting inconsistencies, and apply consistent styling across codebase. Use this when you need to format code to match style guidelines, fix indentation and spacing issues, standardize code appearance, prepare code for commits, apply consistent formatting across files, or check if code matches formatting standards. Automatically detects and uses appropriate formatter (ruff format/black for Python, prettier for JavaScript/TypeScript/JSON/CSS), runs formatting operations, supports check-only mode to verify without changes, applies consistent style rules, and reports formatting status. Returns formatting success status, formatter used, exit code, stdout and stderr output, check-only mode indicator, and result message (formatting correct or changes needed). Use check_only=true to verify formatting without modifying files. Use check_only=false to apply formatting changes. Essential for maintaining consistent code style across team development.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to format"},
                        "check_only": {"type": "boolean", "description": "Check without modifying", "default": False}
                    },
                    "required": ["path"]
                },
                "handler": self.quality.run_formatter
            },
            "run_type_checker": {
                "description": "Run static type checkers to verify type correctness, catch type errors before runtime, and ensure type safety in statically-typed or type-annotated code. Use this when you need to verify type annotations, catch type mismatches, check Python type hints, validate TypeScript types, ensure type safety, find type-related bugs early, or enforce strict typing. Automatically detects and uses appropriate type checker (mypy for Python, tsc for TypeScript), analyzes type annotations and declarations, identifies type errors and mismatches, validates type consistency across codebase, reports type violations with locations, and checks type coverage. Returns type checking success status, type checker used, exit code, stdout with type errors, stderr output, and result message (type checking passed or errors found). Supports mypy (Python static type checker) and tsc (TypeScript compiler in type-check mode). Critical for type-safe development and catching type-related bugs before runtime.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to check"}
                    },
                    "required": ["path"]
                },
                "handler": self.quality.run_type_checker
            },
            "full_quality_check": {
                "description": "Run comprehensive quality checks combining linting, code formatting, and type checking in a single operation with optional auto-fix for all fixable issues. Use this when you need to perform complete code quality validation, prepare code for production, check all quality metrics before committing, run pre-commit quality gates, ensure code meets all quality standards, or get complete quality report in one operation. Executes run_linter (with optional auto-fix), run_formatter (with optional formatting application), and run_type_checker sequentially, aggregates results from all three checks, reports whether all checks passed, provides detailed results for each check type, and supports auto-fix mode to automatically resolve fixable issues. Returns comprehensive quality check status, whether all checks passed (true if linting, formatting, and type checking all succeed), detailed results object with individual check outcomes, and summary message. Use fix=true to automatically fix linting and formatting issues. Essential for comprehensive code quality validation before merging or deployment. Recommended for pre-commit hooks and CI/CD pipelines.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to check"},
                        "fix": {"type": "boolean", "description": "Auto-fix issues", "default": False}
                    },
                    "required": ["path"]
                },
                "handler": self.quality.full_quality_check
            },

            # Step 8: Security Tools
            "scan_secrets": {
                "description": "Scan codebase for hardcoded secrets, credentials, API keys, passwords, and sensitive information using pattern matching and heuristics. Use this when you need to find exposed secrets before committing, audit code for security issues, check for accidentally committed credentials, scan for API keys and tokens, identify potential security vulnerabilities, or ensure no sensitive data is in code. Scans all text files recursively, uses regex patterns to detect common secret types (API keys, passwords, AWS credentials, private keys, database passwords, tokens, etc.), identifies files and line numbers with potential secrets, categorizes findings by severity (high/medium/low), provides context around matches (surrounding lines), and generates detailed security report. Returns scan success status, path scanned, complete findings list with file paths, line numbers, secret types, severity levels, and context, total findings count, and severity breakdown. Detects API keys, passwords, secret tokens, AWS access/secret keys, private keys, database passwords, and generic long strings that might be secrets. Critical for preventing credential leaks and maintaining security.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to scan"}
                    },
                    "required": ["path"]
                },
                "handler": self.security.scan_secrets
            },
            "check_vulnerabilities": {
                "description": "Check project dependencies and packages for known security vulnerabilities using vulnerability databases (safety for Python, npm audit for JavaScript/Node.js). Use this when you need to scan dependencies for CVEs, check for vulnerable packages, audit third-party libraries, find outdated packages with security issues, ensure dependency security, or prepare security reports. Automatically detects dependency files (requirements.txt for Python, package.json for JavaScript), uses appropriate security scanner (safety for Python dependencies, npm audit for Node.js), queries vulnerability databases, identifies vulnerable packages with CVE details, reports severity levels and affected versions, and provides remediation recommendations. Returns vulnerability scan status, path checked, results array with scanner-specific outputs, vulnerability counts, whether vulnerabilities were found, and detailed vulnerability information. Supports Python (safety scanner for requirements.txt), JavaScript/Node.js (npm audit for package.json). Essential for dependency security management and compliance requirements. Helps prevent using packages with known security flaws.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to check"}
                    },
                    "required": ["path"]
                },
                "handler": self.security.check_vulnerabilities
            },
            "security_audit": {
                "description": "Run complete and comprehensive security audit combining secret scanning and dependency vulnerability checking in a single thorough security assessment. Use this when you need to perform full security review, check all security aspects before deployment, audit codebase for security compliance, prepare security reports, validate no security issues exist, or get complete security status. Executes scan_secrets to find hardcoded credentials and sensitive data, runs check_vulnerabilities to audit dependencies, combines results into unified security report, identifies all security issues across code and dependencies, reports whether any security issues exist, and provides detailed findings for both secret exposure and vulnerable dependencies. Returns comprehensive audit status, path audited, complete secrets_scan results (all findings with locations and types), complete vulnerabilities_check results (all vulnerable dependencies), whether security issues were found (true if either secrets or vulnerabilities detected), and summary message. Essential for pre-deployment security validation, compliance checks, and security-first development. Recommended to run before every release and periodically on codebases. Critical for maintaining security posture.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to audit"}
                    },
                    "required": ["path"]
                },
                "handler": self.security.security_audit
            },

            # Multi-Step Workflow Tools
            "complete_feature_workflow": {
                "description": "Execute complete end-to-end workflow for implementing a new feature from initial exploration through planning and guidance for implementation, testing, and quality checks. Use this when you need to add a new feature to a codebase, implement new functionality systematically, follow best practices for feature development, get structured guidance for implementation, ensure all development steps are covered, or execute a comprehensive development process. Runs full_exploration to understand codebase, creates detailed implementation plan with create_plan, provides ready status and guidance for implementation (use generate_diff/apply_changes to code), provides ready status and guidance for testing (use generate_tests/run_tests), provides ready status and guidance for quality checks (use full_quality_check), and returns complete workflow with all step results. Returns workflow ID, workflow type (feature_implementation), exploration results (structure, tech stack, entrypoints), detailed implementation plan with steps, implementation ready status with next action guidance, testing ready status with test generation instructions, quality check ready status with validation instructions, and workflow completion message. This workflow guides you through all steps but requires LLM assistance for actual code generation, testing, and quality validation. Recommended starting point for all feature development work. Ensures systematic and thorough feature implementation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory"},
                        "feature_description": {"type": "string", "description": "Feature to implement"}
                    },
                    "required": ["path", "feature_description"]
                },
                "handler": self.complete_feature_workflow
            },
            "bugfix_workflow": {
                "description": "Execute complete end-to-end workflow for fixing bugs systematically from initial exploration through architecture analysis and guidance for bug fixing and verification. Use this when you need to fix a bug in existing code, resolve issues methodically, understand bug context before fixing, follow systematic bug resolution process, ensure bug fixes don't cause regressions, or get structured guidance for debugging. Runs full_exploration to understand codebase context, executes analyze_architecture to understand system design around bug, creates detailed bugfix plan with reproduction steps and fix strategy, provides ready status and guidance for implementing fix (use generate_diff/apply_changes), provides ready status and guidance for verification (use run_tests), and returns complete workflow with all step results. Returns workflow ID, workflow type (bug_fix), exploration results (structure, tech stack), architecture analysis (patterns, organization), detailed fix plan with root cause analysis, implementation ready status with fix guidance, verification ready status with testing instructions, and workflow completion message. This workflow helps you understand bug context before fixing and ensures systematic resolution. Recommended for all bug fixing work. Critical for preventing regression bugs and ensuring quality fixes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory"},
                        "bug_description": {"type": "string", "description": "Bug to fix"}
                    },
                    "required": ["path", "bug_description"]
                },
                "handler": self.bugfix_workflow
            },
            "refactor_workflow": {
                "description": "Execute complete end-to-end workflow for refactoring code systematically while maintaining functionality from architecture analysis through planning and guidance for implementation, testing, and quality validation. Use this when you need to refactor code to improve design, restructure code while preserving behavior, improve code quality and maintainability, apply better design patterns, reduce technical debt, or modernize legacy code. Runs analyze_architecture to understand current design, creates detailed refactoring plan with behavior preservation strategy, provides ready status and guidance for refactoring implementation (use generate_diff/apply_changes), provides ready status and guidance for testing to ensure behavior unchanged (use run_tests), provides ready status and guidance for quality validation (use full_quality_check), and returns complete workflow with all step results. Returns workflow ID, workflow type (refactoring), architecture analysis results (patterns, structure), detailed refactoring plan with steps and risks, refactoring ready status with implementation guidance, testing ready status emphasizing behavior preservation, quality check ready status with validation instructions, and workflow completion message. This workflow ensures refactoring doesn't break functionality and improves code quality. Recommended for all refactoring work. Critical for safe code restructuring and technical debt reduction.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory"},
                        "refactor_goal": {"type": "string", "description": "Refactoring goal"}
                    },
                    "required": ["path", "refactor_goal"]
                },
                "handler": self.refactor_workflow
            }
        }

    def _register_resources(self) -> Dict[str, Dict[str, Any]]:
        """Register available resources."""
        return {
            "mirror_vanisher_list": {
                "uri": "mirror-vanisher://list",
                "name": "Mirror+Vanisher Directories",
                "description": "List of all directories that are both mirrors and vanishers",
                "mimeType": "application/json"
            },
            "workflow_status": {
                "uri": "workflow://status",
                "name": "Workflow Status",
                "description": "Status of ongoing multi-step workflows",
                "mimeType": "application/json"
            }
        }

    def complete_feature_workflow(self, path: str, feature_description: str) -> Dict[str, Any]:
        """Complete workflow to add a new feature."""
        try:
            workflow_id = f"feature_{Path(path).name}_{hash(feature_description) % 10000}"
            results = {
                "workflow_id": workflow_id,
                "type": "feature_implementation",
                "steps": []
            }

            # Step 1: Exploration
            logger.info(f"[{workflow_id}] Step 1: Exploration")
            exploration = self.exploration.full_exploration(path)
            results["steps"].append({"step": "exploration", "result": exploration})

            # Step 2: Planning
            logger.info(f"[{workflow_id}] Step 2: Planning")
            plan = self.planning.create_plan(path, feature_description, {"exploration": exploration})
            results["steps"].append({"step": "planning", "result": plan})

            # Step 3: Implementation (will be done by LLM using generate_diff/apply_changes)
            logger.info(f"[{workflow_id}] Step 3: Implementation ready")
            results["steps"].append({
                "step": "implementation",
                "result": {
                    "status": "ready",
                    "message": "Use generate_diff and apply_changes tools to implement the plan",
                    "plan": plan
                }
            })

            # Step 4: Testing
            logger.info(f"[{workflow_id}] Step 4: Testing preparation")
            results["steps"].append({
                "step": "testing",
                "result": {
                    "status": "pending",
                    "message": "Use generate_tests and run_tests after implementation"
                }
            })

            # Step 5: Quality Checks
            logger.info(f"[{workflow_id}] Step 5: Quality checks preparation")
            results["steps"].append({
                "step": "quality",
                "result": {
                    "status": "pending",
                    "message": "Use full_quality_check after tests pass"
                }
            })

            return {
                "success": True,
                "workflow": results,
                "message": "Feature workflow initialized. Follow the steps to complete implementation."
            }

        except Exception as e:
            handle_exception(e, context={"function": "complete_feature_workflow", "path": path})
            return {"success": False, "error": str(e)}

    def bugfix_workflow(self, path: str, bug_description: str) -> Dict[str, Any]:
        """Complete workflow to fix a bug."""
        try:
            workflow_id = f"bugfix_{Path(path).name}_{hash(bug_description) % 10000}"
            results = {
                "workflow_id": workflow_id,
                "type": "bug_fix",
                "steps": []
            }

            # Step 1: Exploration
            logger.info(f"[{workflow_id}] Step 1: Exploration")
            exploration = self.exploration.full_exploration(path)
            results["steps"].append({"step": "exploration", "result": exploration})

            # Step 2: Architecture Analysis
            logger.info(f"[{workflow_id}] Step 2: Architecture Analysis")
            architecture = self.architecture.analyze_architecture(path)
            results["steps"].append({"step": "architecture", "result": architecture})

            # Step 3: Planning
            logger.info(f"[{workflow_id}] Step 3: Planning")
            plan = self.planning.create_plan(path, f"Fix bug: {bug_description}", {
                "exploration": exploration,
                "architecture": architecture
            })
            results["steps"].append({"step": "planning", "result": plan})

            # Step 4: Implementation
            results["steps"].append({
                "step": "implementation",
                "result": {
                    "status": "ready",
                    "message": "Use generate_diff and apply_changes to fix the bug",
                    "plan": plan
                }
            })

            # Step 5: Verification
            results["steps"].append({
                "step": "verification",
                "result": {
                    "status": "pending",
                    "message": "Use run_tests to verify the fix"
                }
            })

            return {
                "success": True,
                "workflow": results,
                "message": "Bugfix workflow initialized. Follow the steps to complete the fix."
            }

        except Exception as e:
            handle_exception(e, context={"function": "bugfix_workflow", "path": path})
            return {"success": False, "error": str(e)}

    def refactor_workflow(self, path: str, refactor_goal: str) -> Dict[str, Any]:
        """Complete workflow to refactor code."""
        try:
            workflow_id = f"refactor_{Path(path).name}_{hash(refactor_goal) % 10000}"
            results = {
                "workflow_id": workflow_id,
                "type": "refactoring",
                "steps": []
            }

            # Step 1: Architecture Analysis
            logger.info(f"[{workflow_id}] Step 1: Architecture Analysis")
            architecture = self.architecture.analyze_architecture(path)
            results["steps"].append({"step": "architecture", "result": architecture})

            # Step 2: Planning
            logger.info(f"[{workflow_id}] Step 2: Planning")
            plan = self.planning.create_plan(path, f"Refactor: {refactor_goal}", {
                "architecture": architecture
            })
            results["steps"].append({"step": "planning", "result": plan})

            # Step 3: Refactoring
            results["steps"].append({
                "step": "refactoring",
                "result": {
                    "status": "ready",
                    "message": "Use generate_diff and apply_changes to refactor",
                    "plan": plan
                }
            })

            # Step 4: Testing
            results["steps"].append({
                "step": "testing",
                "result": {
                    "status": "pending",
                    "message": "Use run_tests to ensure refactoring didn't break functionality"
                }
            })

            # Step 5: Quality Checks
            results["steps"].append({
                "step": "quality",
                "result": {
                    "status": "pending",
                    "message": "Use full_quality_check to verify code quality improvements"
                }
            })

            return {
                "success": True,
                "workflow": results,
                "message": "Refactor workflow initialized. Follow the steps to complete refactoring."
            }

        except Exception as e:
            handle_exception(e, context={"function": "refactor_workflow", "path": path})
            return {"success": False, "error": str(e)}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "mirror-vanisher-dev-mcp",
                            "version": "1.0.0"
                        },
                        "capabilities": {
                            "tools": {},
                            "resources": {}
                        }
                    }
                }

            elif method == "tools/list":
                tools_list = []
                for name, tool in self.tools.items():
                    tools_list.append({
                        "name": name,
                        "description": tool["description"],
                        "inputSchema": tool["inputSchema"]
                    })

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")

                handler = self.tools[tool_name]["handler"]
                result = handler(**arguments)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }

            elif method == "resources/list":
                resources_list = []
                for uri, resource in self.resources.items():
                    resources_list.append(resource)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": resources_list}
                }

            elif method == "resources/read":
                uri = params.get("uri")

                if uri == "mirror-vanisher://list":
                    result = self.manager.list_mirror_vanishers()
                elif uri == "workflow://status":
                    result = {"workflows": [], "message": "No active workflows"}
                else:
                    raise ValueError(f"Unknown resource: {uri}")

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }

            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            handle_exception(e, context={"method": method, "params": params})
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    def run(self):
        """Run the stdio MCP server."""
        logger.info("Starting Mirror+Vanisher Development MCP Server")
        logger.info("Reading from stdin, writing to stdout")

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                handle_exception(e, context={"operation": "request_processing"})
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": "Internal error"
                    }
                }
                print(json.dumps(error_response), flush=True)


def main():
    """Main entry point."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
