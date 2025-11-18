#!/usr/bin/env python3
"""
Populate MCP tools lists in Redis by querying MCP servers.
This script should be run from the host machine (not inside Docker)
after starting the sandbox service.

Dynamically discovers all MCP servers in the mcps/ directory.
"""

import json
import subprocess
import sys
from pathlib import Path
import redis

# Paths
VUHITRA_DIR = Path(__file__).parent.parent.parent
MCPS_DIR = VUHITRA_DIR / 'mcps'

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
            port=16379,
            password=redis_password,
            decode_responses=True
        )
        r.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return 1
    
    if not MCPS_DIR.exists():
        print(f"❌ MCPs directory not found: {MCPS_DIR}")
        return 1
    
    # Discover all MCP servers
    mcp_servers = []
    for mcp_dir in MCPS_DIR.iterdir():
        if not mcp_dir.is_dir() or mcp_dir.name.startswith('.'):
            continue
        
        server_file = mcp_dir / 'server.py'
        if server_file.exists():
            # Convert directory name to MCP ID (e.g., mirror_vanisher_dev -> mirror-vanisher-dev)
            mcp_id = mcp_dir.name.replace('_', '-')
            mcp_servers.append((mcp_id, server_file))
            print(f"📋 Found MCP: {mcp_id} at {server_file.relative_to(VUHITRA_DIR)}")
    
    if not mcp_servers:
        print("❌ No MCP servers found")
        return 1
    
    print(f"\n🔍 Discovered {len(mcp_servers)} MCP server(s)\n")
    
    # Query each MCP server
    success_count = 0
    for mcp_id, server_path in mcp_servers:
        print(f"📋 Querying {mcp_id}...")
        tools = query_mcp_tools(server_path)
        if tools:
            print(f"✅ Found {len(tools)} tools")
            r.set(f'mcp:{mcp_id}:tools', json.dumps(tools))
            print(f"✅ Stored in Redis: mcp:{mcp_id}:tools")
            success_count += 1
        else:
            print(f"❌ Failed to query {mcp_id}")
        print()
    
    print(f"✨ Done! Successfully populated {success_count}/{len(mcp_servers)} MCP(s)")
    return 0 if success_count == len(mcp_servers) else 1


if __name__ == '__main__':
    sys.exit(main())
