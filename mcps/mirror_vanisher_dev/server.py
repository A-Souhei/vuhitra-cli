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

from src.exploration import ExplorationTools
from src.architecture import ArchitectureTools
from src.chunking import ChunkingTools
from src.planning import PlanningTools
from src.code_generation import CodeGenerationTools
from src.testing import TestingTools
from src.quality_checks import QualityCheckTools
from src.security import SecurityTools
from src.mirror_vanisher import MirrorVanisherManager
from src.errors_handler import handle_exception

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

        # Tool registry
        self.tools = self._register_tools()
        self.resources = self._register_resources()

        logger.info("MCP Server initialized with all tool modules")

    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools."""
        return {
            # Mirror+Vanisher Management
            "list_mirror_vanishers": {
                "description": "List all directories that are both mirrors and vanishers",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "handler": self.manager.list_mirror_vanishers
            },
            "verify_mirror_vanisher": {
                "description": "Verify a directory is both mirrored and loaded as vanisher",
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
                "description": "Explore directory structure (tree view) of a mirror+vanisher",
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
                "description": "Detect technology stack and languages used",
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
                "description": "Find main entrypoints and executable files",
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
                "description": "Combined: Complete exploration (structure + tech stack + entrypoints)",
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
                "description": "Analyze architectural patterns (MVC, microservices, etc.)",
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
                "description": "Map dependencies between modules/files",
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
                "description": "Identify design patterns in use",
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
                "description": "Break a large file into manageable chunks",
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
                "description": "Create chunking strategy for entire directory",
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
                "description": "Create atomic, file-specific implementation plan",
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
                "description": "Validate a plan for feasibility and completeness",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {"type": "object", "description": "Plan to validate"}
                    },
                    "required": ["plan"]
                },
                "handler": self.planning.validate_plan
            },

            # Step 5: Code Generation Tools
            "generate_diff": {
                "description": "Generate safe code diff for a file",
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
                "description": "Apply code changes with safety checks",
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
                "description": "Completely rewrite a file with safety backup",
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
                "description": "Generate unit tests for a file/function",
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
                "description": "Run tests in the directory",
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
                "description": "Verify changes by running relevant tests",
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
                "description": "Run linter on code",
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
                "description": "Run code formatter",
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
                "description": "Run type checker (mypy, typescript, etc.)",
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
                "description": "Combined: Run all quality checks (lint + format + types)",
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
                "description": "Scan for hardcoded secrets and credentials",
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
                "description": "Check dependencies for known vulnerabilities",
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
                "description": "Run comprehensive security audit",
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
                "description": "Combined: Complete workflow to add a new feature (explore + plan + implement + test + quality)",
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
                "description": "Combined: Complete workflow to fix a bug (explore + analyze + fix + test)",
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
                "description": "Combined: Complete workflow to refactor code (analyze + plan + refactor + test + quality)",
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
