"""
LLM-based Plan Generator - Step 4+ of the Pillars Methodology

Uses LLM (Ollama) to generate comprehensive, context-aware implementation plans
based on loaded vanisher content, pillars documentation, and MCP tool descriptions.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

# Add project root to path to import from src
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent import generate as ollama_generate
from src.utils.config_loader import ConfigLoader
from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class LLMPlanGenerator:
    """LLM-based plan generator with embeddings and context awareness using Ollama."""

    def __init__(self, manager):
        """Initialize LLM plan generator.

        Args:
            manager: MirrorVanisherManager instance
        """
        self.manager = manager
        self.config = None
        self.ollama_model = None
        self.embedding_model = None
        self.tool_embeddings = None
        self._initialize_llm()
        self._initialize_embeddings()

    def _initialize_llm(self) -> None:
        """Initialize Ollama LLM configuration."""
        try:
            self.config = ConfigLoader()

            # Get default model based on environment (local or remote)
            ollama_mode = self.config.get('ollama', 'use', default='local')
            self.ollama_model = self.config.get('model', 'default', ollama_mode, default='llama3.1:8b')

            # For plan generation, prefer more capable models
            available_models = self.config.get('model', 'available', default=[])

            # Prioritize coding models for plan generation
            preferred_models = [
                'qwen2.5-coder:7b',
                'qwen2.5-coder:7b-instruct-q5_K_M',
                'llama3.1:8b',
                'qwen3:latest'
            ]

            for model in preferred_models:
                if model in available_models:
                    self.ollama_model = model
                    break

            logger.info(f"Ollama LLM initialized with model: {self.ollama_model}")

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._initialize_llm',
                'operation': 'initializing Ollama configuration'
            })
            # Fallback to default
            self.ollama_model = 'llama3.1:8b'

    def _initialize_embeddings(self) -> None:
        """Initialize sentence transformer for embeddings."""
        try:
            from sentence_transformers import SentenceTransformer

            # Use a lightweight model for embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model initialized")

        except ImportError:
            logger.error("sentence-transformers package not installed. Run: pip install sentence-transformers")
        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._initialize_embeddings',
                'operation': 'initializing embedding model'
            })

    def _load_pillars_documentation(self) -> str:
        """Load pillars documentation for context.

        Returns:
            Combined pillars documentation as string
        """
        try:
            # Path to pillars documentation (relative to project root)
            project_root = Path(__file__).parent.parent.parent.parent
            pillars_dir = project_root / 'pillars'

            if not pillars_dir.exists():
                logger.warning(f"Pillars directory not found: {pillars_dir}")
                return ""

            # Load key pillar documents
            pillar_files = [
                '00_overview.md',
                '04_planning.md',  # Most important for planning
                '09_prompts.md',
                '10_advanced_tips.md'
            ]

            documentation = []
            for filename in pillar_files:
                filepath = pillars_dir / filename
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        documentation.append(f"# {filename}\n\n{content}\n")
                        logger.debug(f"Loaded pillar: {filename}")

            combined = "\n\n".join(documentation)
            logger.info(f"Loaded {len(pillar_files)} pillar documents")
            return combined

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._load_pillars_documentation',
                'operation': 'loading pillars documentation'
            })
            return ""

    def _get_mcp_tool_descriptions(self, tools: Dict[str, Dict[str, Any]]) -> str:
        """Get formatted MCP tool descriptions.

        Args:
            tools: Dictionary of MCP tools

        Returns:
            Formatted tool descriptions
        """
        try:
            descriptions = ["# Available MCP Tools\n"]

            for tool_name, tool_info in tools.items():
                desc = tool_info.get('description', 'No description')
                schema = tool_info.get('inputSchema', {})

                descriptions.append(f"## {tool_name}")
                descriptions.append(f"{desc}\n")

                # Add input parameters
                if 'properties' in schema:
                    descriptions.append("**Parameters:**")
                    for param, param_info in schema['properties'].items():
                        param_desc = param_info.get('description', '')
                        param_type = param_info.get('type', 'unknown')
                        descriptions.append(f"- `{param}` ({param_type}): {param_desc}")
                descriptions.append("")

            return "\n".join(descriptions)

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._get_mcp_tool_descriptions',
                'operation': 'formatting tool descriptions'
            })
            return ""

    def _create_tool_embeddings(self, tools: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Create embeddings for MCP tool descriptions.

        Args:
            tools: Dictionary of MCP tools

        Returns:
            Dictionary mapping tool names to embeddings
        """
        try:
            if not self.embedding_model:
                logger.warning("Embedding model not initialized")
                return {}

            embeddings = {}
            for tool_name, tool_info in tools.items():
                desc = tool_info.get('description', '')
                if desc:
                    embedding = self.embedding_model.encode(desc)
                    embeddings[tool_name] = embedding

            logger.info(f"Created embeddings for {len(embeddings)} tools")
            return embeddings

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._create_tool_embeddings',
                'operation': 'creating tool embeddings'
            })
            return {}

    def _find_relevant_tools(self, step_description: str, tools: Dict[str, Dict[str, Any]],
                            top_k: int = 3) -> List[str]:
        """Find relevant tools for a plan step using embeddings.

        Args:
            step_description: Description of the plan step
            tools: Dictionary of MCP tools
            top_k: Number of top tools to return

        Returns:
            List of relevant tool names
        """
        try:
            if not self.embedding_model or not self.tool_embeddings:
                return []

            import numpy as np

            # Create embedding for the step description
            step_embedding = self.embedding_model.encode(step_description)

            # Calculate similarity with each tool
            similarities = {}
            for tool_name, tool_embedding in self.tool_embeddings.items():
                # Cosine similarity
                similarity = np.dot(step_embedding, tool_embedding) / (
                    np.linalg.norm(step_embedding) * np.linalg.norm(tool_embedding)
                )
                similarities[tool_name] = similarity

            # Get top-k tools
            top_tools = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
            return [tool_name for tool_name, _ in top_tools]

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._find_relevant_tools',
                'operation': 'finding relevant tools',
                'step_description': step_description
            })
            return []

    def generate_plan(self, task: str, path: str, tools: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive implementation plan using LLM.

        Args:
            task: Task description from user
            path: Path to the vanisher directory
            tools: Dictionary of available MCP tools

        Returns:
            Dictionary with generated plan and metadata
        """
        try:
            # Verify vanisher is loaded and is a directory
            verification = self.manager.verify_mirror_vanisher(path)
            if not verification.get('success') or not verification.get('is_valid'):
                return {
                    'success': False,
                    'error': 'A vanisher of directory type must be loaded to generate a plan',
                    'details': verification.get('reason', 'Unknown error')
                }

            # Verify it's a directory type
            mirror_info = self.manager.mirrors.get(path, {})
            is_directory = (mirror_info.get('type') == 'directory' or
                           mirror_info.get('is_file') == False)

            if not is_directory:
                return {
                    'success': False,
                    'error': 'Only directory-type vanishers are supported for plan generation',
                    'path': path
                }

            # Load context
            pillars_docs = self._load_pillars_documentation()
            tool_descriptions = self._get_mcp_tool_descriptions(tools)

            # Create tool embeddings if not already created
            if not self.tool_embeddings:
                self.tool_embeddings = self._create_tool_embeddings(tools)

            # Get vanisher context (relevant files)
            vanisher_context = self._get_vanisher_context(path)

            # Check if LLM is available
            if not self.ollama_model:
                return {
                    'success': False,
                    'error': 'Ollama model not configured. Check config.yaml for Ollama settings.'
                }

            # Generate plan using LLM
            plan = self._call_llm_for_plan(task, pillars_docs, tool_descriptions, vanisher_context)

            # Enhance plan with tool recommendations for each step
            enhanced_plan = self._enhance_plan_with_tools(plan, tools)

            return {
                'success': True,
                'plan': enhanced_plan,
                'message': f'Generated comprehensive plan with {len(enhanced_plan.get("steps", []))} steps',
                'metadata': {
                    'task': task,
                    'path': path,
                    'pillars_docs_loaded': bool(pillars_docs),
                    'tools_analyzed': len(tools),
                    'vanisher_files': len(vanisher_context.get('files', []))
                }
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator.generate_plan',
                'task': task,
                'path': path
            })
            return {'success': False, 'error': str(e)}

    def _get_vanisher_context(self, path: str) -> Dict[str, Any]:
        """Get context from loaded vanisher.

        Args:
            path: Path to vanisher

        Returns:
            Dictionary with vanisher context
        """
        try:
            vanisher_info = self.manager.vanishers.get(path)
            if not vanisher_info:
                return {'files': [], 'content': ''}

            # Get file list
            mirror_info = self.manager.mirrors.get(path, {})
            files = mirror_info.get('files', [])

            # Get content summary (limited to avoid context overflow)
            content_parts = []
            for file_path in files[:20]:  # Limit to 20 files
                if Path(file_path).is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read(1000)  # Read first 1000 chars
                            content_parts.append(f"## {Path(file_path).name}\n{content}...\n")
                    except:
                        continue

            return {
                'files': files,
                'content': '\n'.join(content_parts),
                'file_count': len(files)
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._get_vanisher_context',
                'path': path
            })
            return {'files': [], 'content': ''}

    def _call_llm_for_plan(self, task: str, pillars_docs: str, tool_descriptions: str,
                          vanisher_context: Dict[str, Any]) -> Dict[str, Any]:
        """Call Ollama LLM to generate plan.

        Args:
            task: Task description
            pillars_docs: Pillars documentation
            tool_descriptions: MCP tool descriptions
            vanisher_context: Context from vanisher

        Returns:
            Generated plan dictionary
        """
        try:
            # Construct prompt
            prompt = f"""You are an expert software development planner. Generate a comprehensive, detailed implementation plan for the following task.

# Task
{task}

# Codebase Context
The following files are available in the loaded vanisher (directory):
{', '.join(vanisher_context.get('files', [])[:30])}

File count: {vanisher_context.get('file_count', 0)}

Sample content:
{vanisher_context.get('content', '')[:2000]}

# Pillars Methodology
{pillars_docs[:8000]}

# Available MCP Tools
{tool_descriptions[:6000]}

# Instructions
Generate a comprehensive implementation plan following the Pillars methodology (Step 4: Planning).

The plan MUST include:
1. **type**: One of: bugfix, refactoring, feature_implementation, general
2. **task**: The task description
3. **steps**: Array of steps, each with:
   - step: Step number (integer)
   - action: Brief action description
   - details: Detailed explanation
   - files: List of files to read/modify (if applicable)
   - verification: How to verify this step (command to run)
4. **estimated_files_to_modify**: List of file paths that will be modified
5. **testing_requirements**: List of testing approaches needed
6. **potential_risks**: List of potential issues or risks
7. **mcp_tools_suggested**: List of MCP tools to use for each pillar step

Return ONLY a valid JSON object with these fields. No explanation text outside the JSON.

Example output format:
{{
  "type": "feature_implementation",
  "task": "Add authentication",
  "steps": [
    {{"step": 1, "action": "Design API", "details": "...", "files": ["src/api.py"], "verification": "pytest tests/"}}
  ],
  "estimated_files_to_modify": ["src/api.py"],
  "testing_requirements": ["Unit tests"],
  "potential_risks": ["Breaking changes"],
  "mcp_tools_suggested": ["explore_structure", "generate_diff"]
}}
"""

            # Call Ollama
            logger.info(f"Calling Ollama with model: {self.ollama_model}")
            response_text, exec_time = ollama_generate(self.ollama_model, prompt)

            logger.info(f"Ollama response received in {exec_time}ms")

            # Check for errors
            if response_text.startswith('ERROR:'):
                raise Exception(response_text)

            # Extract JSON from response (handle potential markdown code blocks)
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)

            # Try to find JSON even if not in code blocks
            if not json_match:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)

            plan = json.loads(response_text)

            logger.info("LLM plan generated successfully")
            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._call_llm_for_plan',
                'task': task,
                'error_type': 'JSONDecodeError'
            })
            # Return a basic plan structure as fallback
            return {
                'type': 'general',
                'task': task,
                'steps': [
                    {'step': 1, 'action': 'Analyze task', 'details': 'Review requirements and codebase'},
                    {'step': 2, 'action': 'Implement changes', 'details': 'Make necessary code changes'},
                    {'step': 3, 'action': 'Test changes', 'details': 'Run tests and verify functionality'}
                ],
                'estimated_files_to_modify': [],
                'testing_requirements': ['Run existing test suite'],
                'potential_risks': ['Unknown - LLM parsing failed'],
                'error': f'LLM response parsing failed: {str(e)}'
            }
        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._call_llm_for_plan',
                'task': task
            })
            # Return a basic plan structure as fallback
            return {
                'type': 'general',
                'task': task,
                'steps': [
                    {'step': 1, 'action': 'Analyze task', 'details': 'Review requirements'},
                    {'step': 2, 'action': 'Implement changes', 'details': 'Make code changes'},
                    {'step': 3, 'action': 'Test changes', 'details': 'Run tests'}
                ],
                'error': f'LLM generation failed: {str(e)}'
            }

    def _enhance_plan_with_tools(self, plan: Dict[str, Any], tools: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Enhance plan steps with relevant MCP tool recommendations.

        Args:
            plan: Generated plan
            tools: Available MCP tools

        Returns:
            Enhanced plan with tool recommendations
        """
        try:
            if 'steps' not in plan:
                return plan

            # Add recommended tools to each step based on embeddings
            for step in plan['steps']:
                step_desc = f"{step.get('action', '')} {step.get('details', '')}"
                relevant_tools = self._find_relevant_tools(step_desc, tools, top_k=3)
                step['recommended_mcp_tools'] = relevant_tools

            logger.info("Plan enhanced with tool recommendations")
            return plan

        except Exception as e:
            handle_exception(e, context={
                'function': 'LLMPlanGenerator._enhance_plan_with_tools'
            })
            return plan
