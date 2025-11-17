#!/usr/bin/env python3
"""
Stdio MCP Server for Executor Operations

This MCP server provides tools for code execution and file operations on
directories that are both mirrored (synced to sandbox) and vanishers (loaded in context).

It implements execution operations including:
- Code execution (Python, JavaScript, shell commands)
- File operations (create, update, delete, copy, move)
- Build and compile operations
- Package installation (pip, npm)
- Directory operations (create, delete, copy, move)
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
import json
import logging
import os
from typing import Any, Dict

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_execution import CodeExecutionTools
from file_operations import FileOperationsTools
from build_operations import BuildOperationsTools
from directory_operations import DirectoryOperationsTools
from mirror_vanisher import MirrorVanisherManager
from errors_handler import handle_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Stdio MCP Server for execution operations on mirror+vanisher directories."""

    def __init__(self):
        """Initialize the MCP server and all tool modules."""
        self.manager = MirrorVanisherManager()

        # Initialize all tool modules
        self.code_execution = CodeExecutionTools(self.manager)
        self.file_operations = FileOperationsTools(self.manager)
        self.build_operations = BuildOperationsTools(self.manager)
        self.directory_operations = DirectoryOperationsTools(self.manager)

        # Tool registry
        self.tools = self._register_tools()
        self.resources = self._register_resources()

        logger.info("Executor MCP Server initialized with all tool modules")

    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools."""
        return {
            # Mirror+Vanisher Management
            "list_mirror_vanishers": {
                "description": "List and enumerate all directories that are simultaneously mirrored to sandbox and loaded into LLM context as vanishers for execution operations. Use this when you need to discover available project directories for code execution, find codebases ready for file operations and builds, identify directories configured for executor workflows, or locate projects to run scripts and install packages in. Returns comprehensive directory information including names, paths, file counts, synchronization status, and availability for execution operations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "handler": self.manager.list_mirror_vanishers
            },
            "verify_mirror_vanisher": {
                "description": "Verify and validate that a specific directory is correctly configured as both a mirror synced to sandbox and a vanisher loaded into LLM context, confirming readiness for execution operations. Use this before executing code, creating files, building projects, or installing packages to ensure proper directory setup, validate mirror+vanisher configuration, troubleshoot execution environment issues, or confirm that the directory is accessible for file operations and code execution. Provides detailed validation including mirror synchronization status, vanisher loading state, directory type verification, and specific configuration issues that would prevent execution operations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to verify"}
                    },
                    "required": ["path"]
                },
                "handler": self.manager.verify_mirror_vanisher
            },

            # Code Execution Tools
            "execute_python_code": {
                "description": "Execute and run a Python script file with optional command-line arguments in a mirror+vanisher directory, capturing standard output, standard error, and return code. Use this when you need to run Python programs, execute Python scripts for testing or automation, test Python code functionality, run Python-based tools and utilities, execute data processing scripts, or validate Python implementations. Runs scripts using python3 interpreter, passes command-line arguments, captures all output streams, reports execution success or failure, and provides complete execution context including working directory and command used. Returns execution results with stdout, stderr, return code, and execution status. Essential for running Python code, automating Python tasks, and executing Python-based workflows in development environments.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "script_path": {"type": "string", "description": "Path to Python script relative to working directory"},
                        "args": {"type": "array", "items": {"type": "string"}, "description": "Optional command-line arguments"},
                        "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 30}
                    },
                    "required": ["path", "script_path"]
                },
                "handler": self.code_execution.execute_python_code
            },
            "execute_shell_command": {
                "description": "Execute and run shell commands and bash scripts in a mirror+vanisher directory, capturing standard output, standard error, and return code for any shell operation. Use this when you need to run shell commands for automation, execute bash scripts, run command-line tools and utilities, perform system operations, execute build scripts, run deployment commands, or automate shell-based workflows. Executes commands using shell interpreter, captures all output streams, supports complex shell syntax including pipes and redirections, reports execution success or failure, and provides complete execution context. Returns execution results with stdout, stderr, return code, command executed, and working directory. Essential for shell automation, running system commands, executing build tools, and performing command-line operations in development workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "command": {"type": "string", "description": "Shell command to execute"},
                        "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 30}
                    },
                    "required": ["path", "command"]
                },
                "handler": self.code_execution.execute_shell_command
            },
            "execute_javascript_code": {
                "description": "Execute and run a JavaScript or Node.js script file with optional command-line arguments in a mirror+vanisher directory, capturing standard output, standard error, and return code. Use this when you need to run JavaScript programs using Node.js runtime, execute Node.js scripts for automation or testing, test JavaScript code functionality, run Node.js-based tools and utilities, execute JavaScript data processing or build scripts, or validate JavaScript/TypeScript implementations. Runs scripts using Node.js interpreter, passes command-line arguments, captures all output streams, reports execution success or failure, and provides complete execution context including working directory and command used. Returns execution results with stdout, stderr, return code, and execution status. Essential for running JavaScript code, automating Node.js tasks, and executing JavaScript-based development workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "script_path": {"type": "string", "description": "Path to JavaScript file relative to working directory"},
                        "args": {"type": "array", "items": {"type": "string"}, "description": "Optional command-line arguments"},
                        "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 30}
                    },
                    "required": ["path", "script_path"]
                },
                "handler": self.code_execution.execute_javascript_code
            },
            "execute_code_snippet": {
                "description": "Execute and run code snippets dynamically by creating temporary files and executing them in specified programming languages including Python, JavaScript, and Bash. Use this when you need to quickly test code without creating permanent files, execute dynamic code snippets for prototyping, run ad-hoc code for testing or validation, execute inline scripts for automation, test small code fragments, or run code experiments. Creates temporary files for code execution, supports Python, JavaScript, and Bash languages, executes code with proper interpreters, automatically cleans up temporary files after execution, captures output and errors, and reports execution success. Returns execution results with stdout, stderr, return code, and execution status. Perfect for rapid code testing, prototyping, and executing transient code snippets without file management overhead.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "language": {"type": "string", "enum": ["python", "javascript", "js", "bash"], "description": "Programming language"},
                        "code": {"type": "string", "description": "Code snippet to execute"},
                        "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 30}
                    },
                    "required": ["path", "language", "code"]
                },
                "handler": self.code_execution.execute_code_snippet
            },

            # File Operations Tools
            "create_file": {
                "description": "Create and write a new file with specified content in a mirror+vanisher directory, with optional overwrite capability for existing files. Use this when you need to create new source code files, write configuration files, generate new scripts or documentation, create data files, write output files from processing, or initialize new file-based resources. Creates file with specified content, creates parent directories automatically if needed, supports UTF-8 encoding for text content, optionally overwrites existing files when specified, validates file paths, and reports file creation details. Returns creation status with file path, file size in bytes, line count, and whether file was newly created or overwritten. Essential for code generation, file creation workflows, writing generated content, and initializing new files in development projects.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "file_path": {"type": "string", "description": "Path to the new file relative to working directory"},
                        "content": {"type": "string", "description": "File content to write"},
                        "overwrite": {"type": "boolean", "description": "Whether to overwrite if file exists", "default": False}
                    },
                    "required": ["path", "file_path", "content"]
                },
                "handler": self.file_operations.create_file
            },
            "update_file": {
                "description": "Update and replace the complete content of an existing file with new content in a mirror+vanisher directory, with automatic backup creation before modification. Use this when you need to modify existing source code files, update configuration files, rewrite scripts with new implementations, change documentation content, update data files, or apply complete file modifications. Reads existing file, creates timestamped backup copy before modification (optional), writes new content completely replacing old content, preserves file metadata, and reports update details. Returns update status with file path, old and new file sizes, backup location, line count, and modification success. Essential for code modification workflows, updating existing files safely, applying changes to configuration, and rewriting file content while maintaining backup copies for safety.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "file_path": {"type": "string", "description": "Path to the file relative to working directory"},
                        "content": {"type": "string", "description": "New content to write"},
                        "backup": {"type": "boolean", "description": "Whether to create backup before updating", "default": True}
                    },
                    "required": ["path", "file_path", "content"]
                },
                "handler": self.file_operations.update_file
            },
            "append_to_file": {
                "description": "Append and add new content to the end of an existing file in a mirror+vanisher directory without replacing existing content. Use this when you need to add content to log files, append records to data files, add new entries to configuration files, extend documentation files, append output to existing files, or incrementally build file content. Opens file in append mode, adds new content to end of file preserving existing content, supports UTF-8 encoding, reports size changes, and maintains file integrity. Returns append status with file path, old and new file sizes, and bytes appended. Essential for logging, incremental file building, appending records or entries, extending existing files, and additive file modification workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "file_path": {"type": "string", "description": "Path to the file relative to working directory"},
                        "content": {"type": "string", "description": "Content to append"}
                    },
                    "required": ["path", "file_path", "content"]
                },
                "handler": self.file_operations.append_to_file
            },
            "delete_file": {
                "description": "Delete and remove an existing file from a mirror+vanisher directory with optional backup creation before deletion for safety. Use this when you need to remove obsolete files, clean up temporary files, delete generated files, remove outdated scripts or configuration, eliminate unnecessary files, or perform file cleanup operations. Optionally creates timestamped backup copy in .backups directory before deletion, validates file existence, permanently removes file, and reports deletion details. Returns deletion status with deleted file path, file size, backup location if created, and deletion success. Essential for file cleanup, removing obsolete code, cleaning temporary files, and maintaining clean project directories while preserving backup safety.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "file_path": {"type": "string", "description": "Path to the file relative to working directory"},
                        "backup": {"type": "boolean", "description": "Whether to create backup before deleting", "default": True}
                    },
                    "required": ["path", "file_path"]
                },
                "handler": self.file_operations.delete_file
            },
            "copy_file": {
                "description": "Copy and duplicate a file to a new location within a mirror+vanisher directory, creating exact copies with optional overwrite of existing destination files. Use this when you need to duplicate files for backups, create file copies for modifications, replicate configuration files, copy templates for new files, duplicate source files for different versions, or create file copies for testing. Reads source file content, creates destination parent directories if needed, writes exact copy to destination, preserves file content and metadata, optionally overwrites existing destination, and reports copy details. Returns copy status with source and destination paths, file size copied, and operation success. Essential for file duplication, backup creation, template copying, and file replication workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "source_file": {"type": "string", "description": "Source file path relative to working directory"},
                        "dest_file": {"type": "string", "description": "Destination file path relative to working directory"},
                        "overwrite": {"type": "boolean", "description": "Whether to overwrite if destination exists", "default": False}
                    },
                    "required": ["path", "source_file", "dest_file"]
                },
                "handler": self.file_operations.copy_file
            },
            "move_file": {
                "description": "Move and relocate a file to a new location within a mirror+vanisher directory, renaming or reorganizing files with optional overwrite of destination. Use this when you need to relocate files to different directories, rename files by moving to new paths, reorganize project file structure, move files between directories, restructure codebase organization, or perform file reorganization operations. Moves file from source to destination, creates destination parent directories if needed, optionally overwrites existing destination, removes file from source location, and reports move details. Returns move status with old and new paths, file size, and operation success. Essential for file organization, project restructuring, file renaming, directory reorganization, and codebase structure modifications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "source_file": {"type": "string", "description": "Source file path relative to working directory"},
                        "dest_file": {"type": "string", "description": "Destination file path relative to working directory"},
                        "overwrite": {"type": "boolean", "description": "Whether to overwrite if destination exists", "default": False}
                    },
                    "required": ["path", "source_file", "dest_file"]
                },
                "handler": self.file_operations.move_file
            },

            # Build Operations Tools
            "install_pip_packages": {
                "description": "Install Python packages and dependencies using pip package manager in a mirror+vanisher directory from package names or requirements.txt file. Use this when you need to install Python dependencies for projects, set up Python package requirements, install libraries for Python scripts, add Python packages to environments, install packages from requirements.txt, upgrade existing Python packages, or manage Python project dependencies. Executes pip install commands, supports installing from package list or requirements file, optionally upgrades existing packages, captures installation output and errors, validates package installation success, and reports installed packages. Returns installation status with command executed, stdout/stderr output, installed packages list, and success indicator. Essential for Python dependency management, setting up Python environments, installing required libraries, and managing Python package installations in development workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "packages": {"type": "array", "items": {"type": "string"}, "description": "List of package names to install"},
                        "requirements_file": {"type": "string", "description": "Optional requirements.txt file path"},
                        "upgrade": {"type": "boolean", "description": "Whether to upgrade existing packages", "default": False}
                    },
                    "required": ["path"]
                },
                "handler": self.build_operations.install_pip_packages
            },
            "install_npm_packages": {
                "description": "Install Node.js packages and dependencies using npm package manager in a mirror+vanisher directory from package names or package.json file. Use this when you need to install Node.js dependencies for JavaScript projects, set up npm package requirements, install JavaScript libraries, add packages to Node.js projects, install packages from package.json, install development dependencies, or manage Node.js project dependencies. Executes npm install commands, supports installing from package list or package.json, optionally installs as dev dependencies, captures installation output and errors, validates installation success, and reports installed packages. Returns installation status with command executed, stdout/stderr output, installed packages list, and success indicator. Essential for Node.js dependency management, setting up JavaScript environments, installing required libraries, and managing npm package installations in JavaScript development workflows.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "packages": {"type": "array", "items": {"type": "string"}, "description": "Optional list of package names to install"},
                        "package_json": {"type": "boolean", "description": "Whether to install from package.json", "default": True},
                        "dev": {"type": "boolean", "description": "Whether to install as dev dependencies", "default": False}
                    },
                    "required": ["path"]
                },
                "handler": self.build_operations.install_npm_packages
            },
            "run_build_command": {
                "description": "Execute and run build commands and tools including make, gradle, maven, cargo, or any custom build scripts in a mirror+vanisher directory. Use this when you need to build software projects, compile applications, execute build scripts, run project build tools, compile source code into executables or artifacts, execute deployment build processes, or run project-specific build automation. Executes build commands using shell, supports make, gradle, maven, npm build, cargo build, and custom build tools, captures build output and errors, reports build success or failure, provides complete build logs, and validates build completion. Returns build status with command executed, stdout/stderr output, return code, working directory, and build success indicator. Essential for project compilation, building applications, running automated builds, generating build artifacts, and executing build workflows in development and deployment processes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "build_command": {"type": "string", "description": "Build command to execute (e.g., 'make', 'npm run build')"},
                        "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 300}
                    },
                    "required": ["path", "build_command"]
                },
                "handler": self.build_operations.run_build_command
            },
            "compile_python": {
                "description": "Compile Python source files to bytecode using py_compile module in a mirror+vanisher directory for syntax validation and bytecode generation. Use this when you need to validate Python syntax without running code, compile Python files to .pyc bytecode, check for Python compilation errors, verify Python code syntax correctness, generate Python bytecode files, or perform Python syntax validation. Executes python -m py_compile command, validates Python syntax, generates .pyc bytecode in __pycache__, reports compilation errors, and confirms successful compilation. Returns compilation status with file path, stdout/stderr output, return code, and compilation success indicator. Essential for Python syntax validation, bytecode generation, checking code before execution, and ensuring Python files are syntactically correct.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "file_path": {"type": "string", "description": "Path to Python file relative to working directory"}
                    },
                    "required": ["path", "file_path"]
                },
                "handler": self.build_operations.compile_python
            },
            "create_virtual_env": {
                "description": "Create a Python virtual environment using venv module in a mirror+vanisher directory for isolated Python package management and dependency isolation. Use this when you need to set up isolated Python environments, create project-specific Python environments, isolate Python dependencies per project, set up clean Python environments, create virtual environments for development, or establish isolated Python package spaces. Executes python -m venv command, creates virtual environment directory structure, sets up isolated Python and pip, provides activation command instructions, and validates environment creation. Returns creation status with virtual environment path, activation command, stdout/stderr output, and creation success indicator. Essential for Python environment isolation, managing project-specific dependencies, creating clean Python environments, and establishing isolated development environments for Python projects.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "venv_name": {"type": "string", "description": "Name of the virtual environment directory", "default": "venv"}
                    },
                    "required": ["path"]
                },
                "handler": self.build_operations.create_virtual_env
            },
            "install_in_virtual_env": {
                "description": "Install Python packages in an existing virtual environment using pip in a mirror+vanisher directory. Use this when you need to install packages in an isolated venv, manage venv-specific dependencies, install libraries without affecting global Python, set up project dependencies in virtual environment, or add packages to an existing venv. Locates virtual environment, uses venv's pip executable, installs from package list or requirements.txt, validates venv existence, reports installed packages, and ensures isolation. Returns installation status with venv name, installed packages list, and success indicator. Essential for managing isolated Python dependencies, installing packages in project-specific environments, and maintaining clean dependency separation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "venv_name": {"type": "string", "description": "Name of the virtual environment directory", "default": "venv"},
                        "packages": {"type": "array", "items": {"type": "string"}, "description": "Optional list of package names to install"},
                        "requirements_file": {"type": "string", "description": "Optional requirements.txt file path"}
                    },
                    "required": ["path"]
                },
                "handler": self.build_operations.install_in_virtual_env
            },
            "run_in_virtual_env": {
                "description": "Run commands in an activated virtual environment in a mirror+vanisher directory. Use this when you need to execute Python scripts with venv-installed packages, run commands using venv Python interpreter, test code in isolated environment, execute tools installed in venv, run development commands with project dependencies, or perform operations using venv-specific packages. Activates virtual environment, executes command in venv context, uses venv's Python and packages, captures output, validates venv existence, and reports execution results. Returns execution status with command output, return code, venv name, and success indicator. Essential for running code with isolated dependencies, testing in virtual environments, and executing venv-specific tools and scripts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "venv_name": {"type": "string", "description": "Name of the virtual environment directory", "default": "venv"},
                        "command": {"type": "string", "description": "Command to run in the activated virtual environment"},
                        "timeout": {"type": "integer", "description": "Execution timeout in seconds", "default": 30}
                    },
                    "required": ["path", "command"]
                },
                "handler": self.build_operations.run_in_virtual_env
            },
            "run_docker_build": {
                "description": "Build Docker container images from Dockerfiles in a mirror+vanisher directory with optional build arguments and custom tags for containerization. Use this when you need to build Docker images for applications, containerize applications, create Docker containers from Dockerfiles, build images with specific tags, pass build arguments to Docker builds, create deployable container images, or automate Docker image creation. Executes docker build command, supports custom Dockerfiles, allows image tagging, accepts build arguments, captures build output and logs, validates build success, and reports image creation. Returns build status with image tag, command executed, stdout/stderr output, return code, and build success indicator. Essential for containerization workflows, building application containers, creating Docker images, automating container builds, and deploying containerized applications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "dockerfile": {"type": "string", "description": "Path to Dockerfile relative to working directory", "default": "Dockerfile"},
                        "tag": {"type": "string", "description": "Image tag", "default": "latest"},
                        "build_args": {"type": "object", "description": "Optional build arguments"}
                    },
                    "required": ["path"]
                },
                "handler": self.build_operations.run_docker_build
            },

            # Directory Operations Tools
            "create_directory": {
                "description": "Create a new directory in a mirror+vanisher directory with optional parent directory creation for establishing directory structures. Use this when you need to create new directories for organizing files, establish directory hierarchies, create folders for new modules or components, set up directory structures for projects, create subdirectories for categorization, or prepare directory trees for file organization. Creates directory at specified path, optionally creates all parent directories in path, validates directory creation, prevents duplicate creation, and reports creation details. Returns creation status with directory path, parent creation flag, and operation success. Essential for directory structure creation, organizing project files, establishing folder hierarchies, preparing directory layouts, and setting up organized file storage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "directory_path": {"type": "string", "description": "Path to the new directory relative to working directory"},
                        "parents": {"type": "boolean", "description": "Whether to create parent directories if they don't exist", "default": True}
                    },
                    "required": ["path", "directory_path"]
                },
                "handler": self.directory_operations.create_directory
            },
            "create_directory_structure": {
                "description": "Create complete directory structures and hierarchies from dictionary specifications in a mirror+vanisher directory for establishing complex folder organizations. Use this when you need to create project scaffolding with multiple directories, establish complete directory hierarchies in one operation, set up directory trees for new projects, create organized folder structures, initialize project layouts with multiple directories, or build complex directory organizations. Accepts nested dictionary defining directory structure, recursively creates all directories, creates parent paths automatically, validates structure creation, and reports all created directories. Returns creation status with list of all created directories, directory count, and operation success. Essential for project initialization, creating project templates, establishing directory scaffolds, setting up organized structures, and initializing complex directory layouts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "structure": {"type": "object", "description": "Dictionary defining directory structure: {'dir1': {}, 'dir2': {'subdir1': {}}}"}
                    },
                    "required": ["path", "structure"]
                },
                "handler": self.directory_operations.create_directory_structure
            },
            "delete_directory": {
                "description": "Delete and remove directories from a mirror+vanisher directory with optional recursive deletion and backup archive creation for safety. Use this when you need to remove obsolete directories, clean up empty folders, delete directory trees recursively, remove build output directories, eliminate temporary directories, or perform directory cleanup operations. Optionally deletes directory contents recursively, creates zip backup archive before deletion, validates directory existence, permanently removes directory, and reports deletion details. Returns deletion status with deleted directory path, backup archive location, recursive flag, and operation success. Essential for directory cleanup, removing obsolete folders, cleaning build directories, eliminating temporary storage, and maintaining clean project structures with backup safety.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "directory_path": {"type": "string", "description": "Path to the directory relative to working directory"},
                        "recursive": {"type": "boolean", "description": "Whether to delete directory contents recursively", "default": False},
                        "backup": {"type": "boolean", "description": "Whether to create backup before deleting", "default": True}
                    },
                    "required": ["path", "directory_path"]
                },
                "handler": self.directory_operations.delete_directory
            },
            "copy_directory": {
                "description": "Copy and duplicate entire directory trees to new locations within a mirror+vanisher directory with optional overwrite of existing destinations. Use this when you need to duplicate directory structures, create directory backups, replicate folder trees, copy project templates, duplicate module directories, or create directory copies for modifications. Recursively copies directory and all contents, creates destination parent directories, preserves directory structure, optionally overwrites existing destination, reports file counts, and validates copy operation. Returns copy status with source and destination paths, file count copied, and operation success. Essential for directory duplication, backup creation, template copying, directory replication, and creating working copies of folder structures.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "source_dir": {"type": "string", "description": "Source directory path relative to working directory"},
                        "dest_dir": {"type": "string", "description": "Destination directory path relative to working directory"},
                        "overwrite": {"type": "boolean", "description": "Whether to overwrite if destination exists", "default": False}
                    },
                    "required": ["path", "source_dir", "dest_dir"]
                },
                "handler": self.directory_operations.copy_directory
            },
            "move_directory": {
                "description": "Move and relocate entire directory trees to new locations within a mirror+vanisher directory, renaming or reorganizing directories with optional overwrite. Use this when you need to relocate directories, reorganize project structure, rename directories by moving, restructure folder hierarchies, move modules to different locations, or perform directory reorganization operations. Moves directory and all contents from source to destination, creates destination parent directories, optionally overwrites existing destination, removes directory from source location, reports file counts, and validates move operation. Returns move status with old and new paths, file count moved, and operation success. Essential for directory organization, project restructuring, folder renaming, directory relocation, and codebase structure modifications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "source_dir": {"type": "string", "description": "Source directory path relative to working directory"},
                        "dest_dir": {"type": "string", "description": "Destination directory path relative to working directory"},
                        "overwrite": {"type": "boolean", "description": "Whether to overwrite if destination exists", "default": False}
                    },
                    "required": ["path", "source_dir", "dest_dir"]
                },
                "handler": self.directory_operations.move_directory
            },
            "list_directory_contents": {
                "description": "List and enumerate contents of directories in a mirror+vanisher directory with optional recursive listing and filtering by file type. Use this when you need to see directory contents, list files and subdirectories, explore directory structures, find files in directories, inventory directory contents, list files recursively, or discover what files and folders exist. Lists directory entries, optionally recurses into subdirectories, filters to show only files excluding directories, reports file sizes, shows relative paths, and provides item counts. Returns listing with contents array, file/directory type indicators, sizes, paths, total count, and operation success. Essential for directory exploration, discovering files, understanding folder contents, finding items in directories, and enumerating directory structures.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Working directory (mirror+vanisher)"},
                        "directory_path": {"type": "string", "description": "Directory to list (default: current directory)", "default": "."},
                        "recursive": {"type": "boolean", "description": "Whether to list recursively", "default": False},
                        "files_only": {"type": "boolean", "description": "Whether to list only files (exclude directories)", "default": False}
                    },
                    "required": ["path"]
                },
                "handler": self.directory_operations.list_directory_contents
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
            "execution_history": {
                "uri": "executor://history",
                "name": "Execution History",
                "description": "History of code execution and operations",
                "mimeType": "application/json"
            }
        }

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
                            "name": "executor-mcp",
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
                elif uri == "executor://history":
                    result = {"history": [], "message": "No execution history"}
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
        logger.info("Starting Executor MCP Server")
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
