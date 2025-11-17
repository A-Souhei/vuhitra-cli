# MCP Management System

## Overview

The MCP (Model Context Protocol) Management System provides a web-based interface for managing MCP servers, their tools, and resources within the Vuhitra CLI sandbox environment.

## Features

### 1. Automatic MCP Registration
- MCPs are automatically registered in Redis on startup
- Each MCP tracks: name, description, tool count, resource count, enabled status
- The Mirror+Vanisher Development MCP is automatically registered

### 2. Coding Mode Integration
- **Coding Mode Disabled**: Mirror+Vanisher MCP can be toggled on/off
- **Coding Mode Enabled**: Mirror+Vanisher MCP is always enabled (cannot be disabled)
- Mode status displayed in the UI with a badge

### 3. Web UI (`/mcps`)
- View all registered MCPs in card format
- See tool and resource counts for each MCP
- Toggle MCPs on/off (if allowed)
- View detailed information about each MCP's tools
- Responsive design matching the Vuhitra CLI UI style

## Architecture

### Backend (main.py)

#### Redis Storage
MCPs are stored in Redis with the key pattern `mcp:{mcp_id}`:
```python
{
    'id': 'mirror-vanisher-dev',
    'name': 'Mirror+Vanisher Development MCP',
    'description': '...',
    'tools_count': 18,
    'resources_count': 0,
    'enabled': 'true',
    'always_enabled': 'false',
    'registered_at': '2025-11-17T07:26:29.928289'
}
```

#### Functions
- `get_coding_mode_status()` - Checks if `VUHITRA_CODING_MODE` env var is set
- `get_all_mcps_from_redis()` - Retrieves all MCPs from Redis
- `register_mcp_in_redis()` - Registers a new MCP
- `toggle_mcp_enabled()` - Enables/disables an MCP (respects `always_enabled`)

#### API Endpoints

**GET /api/mcps**
- Lists all registered MCPs
- Returns: `{success, mcps[], coding_mode, count}`

**GET /api/mcps/{mcp_id}**
- Gets detailed MCP information
- Returns: `{success, mcp: {id, name, description, tools[], resources[]}}`

**POST /api/mcps/{mcp_id}/toggle**
- Toggles MCP enabled status
- Body: `{enabled: true/false}`
- Returns: `{success}` or `{success: false, error: ...}`

**GET /mcps**
- Web UI page for MCP management

### Frontend

#### HTML (mcps.html)
- Bootstrap 5 based responsive design
- Navigation bar with MCP link
- Card-based MCP display
- Modal for MCP details
- Coding mode indicator

#### JavaScript (mcps.js)
- `loadMCPs()` - Fetches and displays MCPs
- `toggleMCP(id, enabled)` - Toggles MCP status via API
- `showMCPDetails(id)` - Shows detailed MCP info in modal
- `updateCodingModeIndicator()` - Updates coding mode badge

#### CSS (mcps.css)
- MCP card hover effects
- Badge styling
- Modal layouts
- Switch toggle styling

## Mirror+Vanisher Development MCP

### Tools (18 total)

#### Verification & Listing (2)
1. **list_mirror_vanishers** - List all mirror+vanisher directories
2. **verify_mirror_vanisher** - Verify a path is valid

#### Step 1: Exploration (4)
3. **explore_structure** - Generate directory tree
4. **detect_tech_stack** - Identify languages and frameworks
5. **find_entrypoints** - Locate main executable files
6. **full_exploration** - Combined exploration tool

#### Step 2: Architecture (3)
7. **analyze_architecture** - Identify architectural patterns
8. **map_dependencies** - Map imports and dependencies
9. **identify_patterns** - Find design patterns

#### Step 3: Chunking (2)
10. **chunk_file** - Break a file into chunks
11. **chunk_directory** - Create chunking strategy

#### Step 4: Planning (1)
12. **create_plan** - Generate implementation plan

#### Step 6: Testing (1)
13. **run_tests** - Execute tests

#### Step 7: Quality Checks (1)
14. **full_quality_check** - Run linter, formatter, type checker

#### Step 8: Security (2)
15. **scan_secrets** - Find hardcoded secrets
16. **security_audit** - Complete security audit

#### Workflows (2)
17. **complete_feature_workflow** - End-to-end feature implementation
18. **bugfix_workflow** - Systematic bug fixing

## Usage

### Accessing the MCP UI
1. Navigate to `http://localhost:18001/mcps` in your browser
2. View all registered MCPs
3. Click "Details" to see tools and resources
4. Use the toggle switch to enable/disable MCPs (if allowed)

### Enabling Coding Mode
```bash
export VUHITRA_CODING_MODE=true
docker restart vuhitra-sandbox
```

When coding mode is enabled:
- Mirror+Vanisher MCP becomes always enabled
- Toggle switch is disabled
- Badge shows "Always ON"

### Registering a New MCP
```python
register_mcp_in_redis(
    mcp_id='my-custom-mcp',
    name='My Custom MCP',
    description='Custom tools for XYZ',
    tools_count=5,
    resources_count=2,
    always_enabled=False  # Can be toggled
)
```

### API Usage Examples

**List all MCPs:**
```bash
curl http://localhost:18001/api/mcps | jq .
```

**Get MCP details:**
```bash
curl http://localhost:18001/api/mcps/mirror-vanisher-dev | jq .mcp
```

**Enable an MCP:**
```bash
curl -X POST http://localhost:18001/api/mcps/my-mcp/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

## Navigation Integration

The MCP link has been added to all page navigation bars:
- Home
- Eternals
- Pillars
- Ephemerals
- Vanishers
- Mirrors
- **MCPs** (new)

The home page also includes an MCP card with:
- Description of MCP functionality
- Link to management page
- Note about automatic enabling in coding mode

## File Locations

### Backend
- `/home/toavina/Apps/vuhitra-cli/services/sandbox/src/main.py` (lines 1474-1672)

### Frontend
- `/home/toavina/Apps/vuhitra-cli/services/sandbox/templates/mcps.html`
- `/home/toavina/Apps/vuhitra-cli/services/sandbox/static/js/mcps.js`
- `/home/toavina/Apps/vuhitra-cli/services/sandbox/static/css/mcps.css`

### Updated Files
All navigation bars updated to include MCP link:
- home.html
- eternals.html
- pillars.html
- ephemerals.html
- vanishers.html
- mirrors.html

## Testing

### Test MCP API
```bash
# List MCPs
curl -s http://localhost:18001/api/mcps | jq .

# Get MCP details
curl -s http://localhost:18001/api/mcps/mirror-vanisher-dev | jq .

# Toggle MCP (will fail if always_enabled=true)
curl -X POST http://localhost:18001/api/mcps/mirror-vanisher-dev/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Expected Behavior

**Without Coding Mode:**
- Mirror+Vanisher MCP: `enabled=false`, `always_enabled=false`, `can_toggle=true`
- Can be toggled on/off via UI or API

**With Coding Mode:**
- Mirror+Vanisher MCP: `enabled=true`, `always_enabled=true`, `can_toggle=false`
- Toggle switch disabled in UI
- API returns error: "This MCP is always enabled and cannot be disabled"

## Future Enhancements

1. **Dynamic MCP Discovery** - Automatically detect and register MCPs from config files
2. **Tool Statistics** - Track tool usage and success rates
3. **MCP Health Checks** - Monitor MCP server status
4. **Resource Management** - Add support for managing MCP resources
5. **MCP Configuration** - Allow editing MCP settings via UI
6. **Multi-MCP Support** - Support for multiple concurrent MCPs
7. **MCP Marketplace** - Browse and install community MCPs

## Troubleshooting

### MCP not showing in UI
- Check Redis connection: `docker exec vuhitra-redis redis-cli -a redis_pwd KEYS mcp:*`
- Verify MCP registration in startup logs
- Restart sandbox: `docker restart vuhitra-sandbox`

### Toggle not working
- Check if MCP has `always_enabled=true`
- Verify coding mode status: `echo $VUHITRA_CODING_MODE`
- Check API response for error message

### Template not found error
- Ensure `mcps.html` exists in `/app/templates/` in container
- Copy template: `docker cp services/sandbox/templates/mcps.html vuhitra-sandbox:/app/templates/`
- Restart sandbox

## Summary

The MCP Management System provides a complete solution for managing Model Context Protocol servers in the Vuhitra CLI environment:

✅ Web-based UI for easy management
✅ Automatic registration and configuration
✅ Coding mode integration
✅ Toggle functionality with safety checks
✅ Detailed tool and resource information
✅ API for programmatic access
✅ Integrated with existing UI navigation

The Mirror+Vanisher Development MCP is now fully integrated and can be managed through the web interface at `/mcps`.
