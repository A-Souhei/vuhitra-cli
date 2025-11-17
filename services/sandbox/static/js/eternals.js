// Eternals Context Management JavaScript

async function loadEternals() {
    try {
        // Note: This endpoint needs to be implemented in the backend
        const response = await fetch('/api/contexts/eternals');

        if (!response.ok) {
            throw new Error('Failed to load eternals');
        }

        const data = await response.json();
        const contexts = data.contexts || [];

        if (contexts.length === 0) {
            document.getElementById('eternalContainer').innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <h4>No Eternal Contexts Found</h4>
                    <p>Create your first eternal context using the CLI:</p>
                    <div class="cli-hint">
                        <code>/eternal load @docs/api.md api "API documentation"</code>
                    </div>
                </div>
            `;
            return;
        }

        const tableHTML = `
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th><i class="bi bi-tag"></i> Label</th>
                            <th><i class="bi bi-file-text"></i> File Path</th>
                            <th><i class="bi bi-arrows-fullscreen"></i> Size</th>
                            <th class="d-none d-lg-table-cell"><i class="bi bi-layers"></i> Chunks</th>
                            <th class="d-none d-xl-table-cell"><i class="bi bi-calendar"></i> Loaded</th>
                            <th class="text-end"><i class="bi bi-gear"></i> Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${contexts.map(ctx => {
                            const label = ctx.label || 'unknown';
                            const filePath = ctx.file_path || '-';
                            const sizeKB = (ctx.content_size / 1024).toFixed(1);
                            const chunks = ctx.num_chunks || 1;
                            const timestamp = formatDateTime(ctx.timestamp);
                            const autoLoaded = ctx.auto_loaded ? '<span class="badge bg-info ms-2">Auto</span>' : '';

                            return `
                                <tr>
                                    <td>
                                        <strong>${escapeHtml(label)}</strong>
                                        ${autoLoaded}
                                        <div class="cli-hint mt-1">
                                            <i class="bi bi-terminal"></i> /clear eternal ${escapeHtml(label)}
                                        </div>
                                    </td>
                                    <td><small class="text-muted">${escapeHtml(filePath)}</small></td>
                                    <td><span class="badge bg-secondary">${sizeKB} KB</span></td>
                                    <td class="d-none d-lg-table-cell"><span class="badge badge-eternal">${chunks}</span></td>
                                    <td class="d-none d-xl-table-cell"><small class="text-muted">${timestamp}</small></td>
                                    <td class="text-end">
                                        <div class="btn-group btn-group-sm" role="group">
                                            <button class="btn btn-outline-info"
                                                    onclick="viewEternalContent('${escapeHtml(label)}')"
                                                    title="View Content">
                                                <i class="bi bi-eye"></i>
                                            </button>
                                            <button class="btn btn-outline-danger"
                                                    onclick="deleteEternal('${escapeHtml(label)}')"
                                                    title="Delete">
                                                <i class="bi bi-trash"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
            <div class="mt-3">
                <p class="text-muted small">
                    <i class="bi bi-info-circle"></i>
                    Eternal contexts persist across CLI sessions. Stored in <code>.vuhitra/eternal_contexts/</code>
                </p>
            </div>
        `;

        document.getElementById('eternalContainer').innerHTML = tableHTML;
    } catch (error) {
        console.error('Error loading eternals:', error);
        document.getElementById('eternalContainer').innerHTML = `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle-fill"></i>
                Unable to load eternal contexts. This feature requires the CLI to be running.
                <div class="mt-2">
                    <small>Start the CLI in normal mode to manage eternal contexts.</small>
                </div>
            </div>
        `;
    }
}

async function deleteEternal(label) {
    if (!confirm(`Are you sure you want to delete eternal context "${label}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/contexts/eternals/${label}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showMessage('success', `Eternal context "${label}" deleted successfully`);
            loadEternals();
        } else {
            throw new Error('Delete failed');
        }
    } catch (error) {
        showMessage('danger', `Failed to delete eternal context "${label}"`);
    }
}

async function viewEternalContent(label) {
    alert('Content viewing feature coming soon!');
}

function showMessage(type, text) {
    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${text}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    setTimeout(() => {
        messageDiv.innerHTML = '';
    }, 5000);
}

function formatDateTime(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Load eternals when page loads
document.addEventListener('DOMContentLoaded', loadEternals);
