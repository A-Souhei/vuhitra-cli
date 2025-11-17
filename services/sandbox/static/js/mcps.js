// MCP Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadMCPs();
});

function loadMCPs() {
    const container = document.getElementById('mcpContainer');
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted mt-2">Loading MCPs...</p>
        </div>
    `;

    fetch('/api/mcps')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayMCPs(data.mcps, data.coding_mode);
                updateCodingModeIndicator(data.coding_mode);
            } else {
                showError('Failed to load MCPs: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            showError('Error loading MCPs: ' + error.message);
        });
}

function updateCodingModeIndicator(codingMode) {
    const indicator = document.getElementById('codingModeIndicator');
    if (codingMode) {
        indicator.innerHTML = `
            <span class="badge bg-success">
                <i class="bi bi-code-square"></i> Coding Mode: ENABLED
            </span>
        `;
    } else {
        indicator.innerHTML = `
            <span class="badge bg-secondary">
                <i class="bi bi-code-square"></i> Coding Mode: DISABLED
            </span>
        `;
    }
}

function displayMCPs(mcps, codingMode) {
    const container = document.getElementById('mcpContainer');

    if (mcps.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> No MCPs registered yet.
            </div>
        `;
        return;
    }

    let html = '<div class="row">';

    mcps.forEach(mcp => {
        const statusBadge = mcp.enabled
            ? '<span class="badge bg-success" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;">Enabled</span>'
            : '<span class="badge bg-secondary" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;">Disabled</span>';

        const alwaysEnabledBadge = mcp.always_enabled
            ? '<span class="badge bg-primary" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;">Always ON</span>'
            : '';

        const toggleDisabled = !mcp.can_toggle ? 'disabled' : '';
        const toggleTooltip = !mcp.can_toggle
            ? 'title="This MCP is automatically managed by coding mode"'
            : '';

        html += `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100 mcp-card">
                    <div class="card-body d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="card-title">
                                <i class="bi bi-plugin"></i> ${mcp.name}
                            </h5>
                            <div class="d-flex gap-2 align-items-center flex-shrink-0">
                                ${statusBadge}
                                ${alwaysEnabledBadge}
                            </div>
                        </div>
                        <p class="card-text text-muted small">${mcp.description}</p>
                        <div class="mcp-stats mt-3 mb-3">
                            <div class="d-flex justify-content-between">
                                <span>
                                    <i class="bi bi-tools"></i> ${mcp.tools_count} Tools
                                </span>
                                <span>
                                    <i class="bi bi-file-earmark"></i> ${mcp.resources_count} Resources
                                </span>
                            </div>
                        </div>
                        <div class="d-flex gap-2 mt-auto">
                            <a href="/mcps/${mcp.id}" class="btn btn-sm btn-outline-primary flex-grow-1">
                                <i class="bi bi-info-circle"></i> Details
                            </a>
                            <div class="form-check form-switch d-flex align-items-center ms-2" ${toggleTooltip}>
                                <input class="form-check-input" type="checkbox"
                                       id="toggle-${mcp.id}"
                                       ${mcp.enabled ? 'checked' : ''}
                                       ${toggleDisabled}
                                       onchange="toggleMCP('${mcp.id}', this.checked)">
                            </div>
                        </div>
                    </div>
                    <div class="card-footer text-muted small">
                        Registered: ${formatDate(mcp.registered_at)}
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

function toggleMCP(mcpId, enabled) {
    fetch(`/api/mcps/${mcpId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(`MCP ${enabled ? 'enabled' : 'disabled'} successfully`);
        } else {
            showError(data.error || 'Failed to toggle MCP');
            // Revert checkbox
            document.getElementById(`toggle-${mcpId}`).checked = !enabled;
        }
    })
    .catch(error => {
        showError('Error toggling MCP: ' + error.message);
        // Revert checkbox
        document.getElementById(`toggle-${mcpId}`).checked = !enabled;
    });
}

// Details are now shown on a separate page, not in modal

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showSuccess(message) {
    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="bi bi-check-circle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    setTimeout(() => messageDiv.innerHTML = '', 5000);
}

function showError(message) {
    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-triangle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}
