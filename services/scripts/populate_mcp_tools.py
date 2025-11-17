#!/usr/bin/env python3
"""
Populate MCP tools lists in Redis by querying MCP servers.
This script should be run from the host machine (not inside Docker)
after starting the sandbox service.
"""

import json
import subprocess
import sys
from pathlib import Path
import redis

# Paths
VUHITRA_DIR = Path(__file__).parent.parent.parent
EXECUTOR_SERVER = VUHITRA_DIR / 'mcps' / 'executor' / 'server.py'
MIRROR_VANISHER_SERVER = VUHITRA_DIR / 'mcps' / 'mirror_vanisher_dev' / 'server.py'

def query_mcp_tools(server_path):
    """Query an MCP server for its tools list"""
    if not server_path.exists():
        print(f"❌ Server not found: {server_path}")
        return None
    
    try:
        # Send tools/list request via stdio
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        result = subprocess.run(
            ['python3', str(server_path)],
            input=json.dumps(request) + '\n',
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"❌ MCP server returned error code {result.returncode}")
            if result.stderr:
                print(f"   stderr: {result.stderr}")
            return None
        
        # Parse JSON-RPC response
        for line in result.stdout.strip().split('\n'):
            try:
                response = json.loads(line)
                if response.get('id') == 1 and 'result' in response:
                    tools_data = response['result'].get('tools', [])
                    # Simplify for UI (name + truncated description)
                    tools = [
                        {
                            'name': tool['name'],
                            'description': tool['description'][:200] + '...' 
                                if len(tool['description']) > 200 
                                else tool['description']
                        }
                        for tool in tools_data
                    ]
                    return tools
            except json.JSONDecodeError:
                continue
        
        print(f"❌ No valid JSON-RPC response found")
        return None
        
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout querying MCP server")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Main entry point"""
    print("🔧 Populating MCP tools lists in Redis...")
    
    # Connect to Redis
    try:
        # Try to load password from secrets.yaml
        secrets_file = VUHITRA_DIR / 'secrets.yaml'
        redis_password = None
        if secrets_file.exists():
            import yaml
            with open(secrets_file) as f:
                secrets = yaml.safe_load(f)
                redis_password = secrets.get('redis', {}).get('password')
        
        if not redis_password:
            print("❌ Redis password not found in secrets.yaml")
            return 1
        
        r = redis.Redis(
            host='localhost',
            port=6379,
            password=redis_password,
            decode_responses=True
        )
        r.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return 1
    
    # Query Executor MCP
    print("\n📋 Querying Executor MCP...")
    executor_tools = query_mcp_tools(EXECUTOR_SERVER)
    if executor_tools:
        print(f"✅ Found {len(executor_tools)} tools")
        r.set('mcp:executor:tools', json.dumps(executor_tools))
        print("✅ Stored in Redis: mcp:executor:tools")
    else:
        print("❌ Failed to query Executor MCP")
    
    # Query Mirror+Vanisher Dev MCP
    print("\n📋 Querying Mirror+Vanisher Dev MCP...")
    mirror_tools = query_mcp_tools(MIRROR_VANISHER_SERVER)
    if mirror_tools:
        print(f"✅ Found {len(mirror_tools)} tools")
        r.set('mcp:mirror-vanisher-dev:tools', json.dumps(mirror_tools))
        print("✅ Stored in Redis: mcp:mirror-vanisher-dev:tools")
    else:
        print("❌ Failed to query Mirror+Vanisher Dev MCP")
    
    print("\n✨ Done!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
