"""
MCP Tool Completer
Provides $ + TAB autocomplete for MCP tool names
"""

import re
import time
import requests
from typing import Dict, List, Optional, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from src.errors_handler import handle_exception
from src.utils.config_loader import ConfigLoader


class MCPToolCompleter(Completer):
    """
    Completer for $ prefix that suggests MCP tool names.
    Fetches available tools from the sandbox MCP API.
    """

    def __init__(self, sandbox_url: Optional[str] = None, cache_ttl: int = 60):
        """
        Initialize the MCP tool completer.

        Args:
            sandbox_url: URL of the sandbox service (defaults to config)
            cache_ttl: Time to live for cache in seconds (default: 60)
        """
        self.tools: List[Dict[str, str]] = []
        self.cache_timestamp: float = 0
        self.cache_ttl = cache_ttl

        # Get sandbox URL from config if not provided
        if sandbox_url is None:
            config = ConfigLoader()
            self.sandbox_url = config.get_sandbox_url()
        else:
            self.sandbox_url = sandbox_url

    def _should_refresh_cache(self) -> bool:
        """
        Check if cache should be refreshed.

        Returns:
            True if cache should be refreshed
        """
        current_time = time.time()
        return (not self.tools) or (current_time - self.cache_timestamp) > self.cache_ttl

    def _fetch_mcp_tools(self) -> None:
        """
        Fetch MCP tools from sandbox API and update cache.
        """
        try:
            # First, get list of MCPs
            mcps_response = requests.get(
                f"{self.sandbox_url}/api/mcps",
                timeout=5
            )
            mcps_response.raise_for_status()
            mcps_data = mcps_response.json()

            if not mcps_data.get('success'):
                return

            all_tools = []

            # Get list of enabled MCPs
            enabled_mcps = [
                mcp for mcp in mcps_data.get('mcps', [])
                if mcp.get('enabled')
            ]

            # Fetch MCP details concurrently for better performance
            def fetch_mcp_details(mcp):
                """Fetch details for a single MCP."""
                mcp_id = mcp.get('id')
                try:
                    details_response = requests.get(
                        f"{self.sandbox_url}/api/mcps/{mcp_id}",
                        timeout=5
                    )
                    details_response.raise_for_status()
                    details_data = details_response.json()

                    if details_data.get('success'):
                        mcp_info = details_data.get('mcp', {})
                        tools = mcp_info.get('tools', [])
                        mcp_name = mcp_info.get('name', mcp_id)

                        # Add MCP name context to each tool
                        return [
                            {
                                'name': tool.get('name', ''),
                                'description': tool.get('description', ''),
                                'mcp_id': mcp_id,
                                'mcp_name': mcp_name
                            }
                            for tool in tools
                        ]
                    return []

                except Exception as e:
                    # Log but don't fail - just skip this MCP
                    handle_exception(e, context={
                        'function': 'MCPToolCompleter._fetch_mcp_tools',
                        'operation': 'fetching MCP details',
                        'mcp_id': mcp_id
                    })
                    return []

            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all fetch tasks
                future_to_mcp = {
                    executor.submit(fetch_mcp_details, mcp): mcp
                    for mcp in enabled_mcps
                }

                # Collect results as they complete
                for future in as_completed(future_to_mcp):
                    try:
                        tools = future.result()
                        all_tools.extend(tools)
                    except Exception as e:
                        mcp = future_to_mcp[future]
                        handle_exception(e, context={
                            'function': 'MCPToolCompleter._fetch_mcp_tools',
                            'operation': 'processing MCP future',
                            'mcp_id': mcp.get('id')
                        })
                        continue

            self.tools = all_tools
            self.cache_timestamp = time.time()

        except requests.exceptions.RequestException as e:
            handle_exception(e, context={
                'function': 'MCPToolCompleter._fetch_mcp_tools',
                'operation': 'fetching MCP list',
                'sandbox_url': self.sandbox_url
            })
            # Don't update cache on failure - keep old data if available
        except Exception as e:
            handle_exception(e, context={
                'function': 'MCPToolCompleter._fetch_mcp_tools',
                'operation': 'processing MCP tools'
            })

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """
        Generate completions for $ prefix.

        Args:
            document: The current document
            complete_event: The completion event

        Yields:
            Completion objects for matching MCP tools
        """
        try:
            text_before_cursor = document.text_before_cursor

            # Match pattern $word (where word is partial or complete tool name)
            match = re.search(r'\$([^\s]*)$', text_before_cursor)

            if not match:
                return

            prefix = match.group(1).lower()

            # Refresh cache if needed
            if self._should_refresh_cache():
                self._fetch_mcp_tools()

            # Filter tools that match the prefix
            for tool in self.tools:
                tool_name = tool.get('name', '')

                if tool_name.lower().startswith(prefix):
                    description = tool.get('description', '')
                    mcp_name = tool.get('mcp_name', '')

                    # Truncate description for display
                    display_desc = description[:80] + '...' if len(description) > 80 else description

                    # Create display text
                    display = f"${tool_name}"

                    # Create meta info (shown on the right)
                    display_meta = f"[{mcp_name}] {display_desc}"

                    yield Completion(
                        text=tool_name,
                        start_position=-len(prefix),
                        display=display,
                        display_meta=display_meta
                    )

        except Exception as e:
            handle_exception(e, context={
                'function': 'MCPToolCompleter.get_completions',
                'operation': 'generating completions',
                'text_before_cursor': text_before_cursor if 'text_before_cursor' in locals() else 'N/A'
            })

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, str]]:
        """
        Get information about a specific tool.

        Args:
            tool_name: The name of the tool

        Returns:
            Dictionary with tool info, or None if not found
        """
        try:
            # Refresh cache if needed
            if self._should_refresh_cache():
                self._fetch_mcp_tools()

            # Find the tool
            for tool in self.tools:
                if tool.get('name') == tool_name:
                    return tool

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': 'MCPToolCompleter.get_tool_info',
                'operation': 'getting tool info',
                'tool_name': tool_name
            })
            return None
