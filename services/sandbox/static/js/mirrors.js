async function loadMirrors() {
    try {
        const response = await fetch('/mirror-list');
        const data = await response.json();
        const mirrors = data.mirrors || [];

        if (mirrors.length === 0) {
            document.getElementById('mirrorContainer').innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <h4>No Mirrors Found</h4>
                    <p>Create your first mirror using the CLI:</p>
                    <div class="cli-hint">
                        <code>/mirror do @data</code>
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
                            <th><i class="bi bi-folder"></i> Name</th>
                            <th><i class="bi bi-diagram-3"></i> Type</th>
                            <th><i class="bi bi-files"></i> Files</th>
                            <th class="d-none d-lg-table-cell"><i class="bi bi-calendar"></i> Created</th>
                            <th><i class="bi bi-check-circle"></i> Status</th>
                            <th class="d-none d-xl-table-cell"><i class="bi bi-clock-history"></i> Last Checked</th>
                            <th class="text-end"><i class="bi bi-gear"></i> Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${mirrors.map(mirror => {
                            const name = mirror.name || 'unknown';
                            const type = mirror.type || 'unknown';
                            const fileCount = mirror.file_count || '0';
                            const created = formatDateTime(mirror.created_at);
                            const lastChecked = formatDateTime(mirror.last_checked);
                            const syncStatus = mirror.sync_status || 'unknown';
                            const isSynced = syncStatus === 'synced';
                            
                            const typeBadge = type === 'file' ? 
                                '<span class="badge badge-file"><i class="bi bi-file-earmark"></i> File</span>' :
                                '<span class="badge badge-directory"><i class="bi bi-folder-fill"></i> Directory</span>';
                            
                            const statusBadge = isSynced ?
                                '<span class="badge bg-success sync-badge"><i class="bi bi-check-circle-fill"></i> Synced</span>' :
                                '<span class="badge bg-warning text-dark sync-badge"><i class="bi bi-exclamation-circle-fill"></i> Not Synced</span>';

                            return `
                                <tr>
                                    <td>
                                        <strong>${escapeHtml(name)}</strong>
                                        <div class="cli-hint mt-1">
                                            <i class="bi bi-terminal"></i> /mirror revert+sync @${escapeHtml(name)}
                                        </div>
                                    </td>
                                    <td>${typeBadge}</td>
                                    <td><span class="badge bg-secondary">${fileCount}</span></td>
                                    <td class="d-none d-lg-table-cell"><small class="text-muted">${created}</small></td>
                                    <td>${statusBadge}</td>
                                    <td class="d-none d-xl-table-cell"><small class="text-muted">${lastChecked}</small></td>
                                    <td class="text-end">
                                        <div class="btn-group btn-group-sm" role="group">
                                            <button class="btn btn-outline-primary" 
                                                    onclick="syncMirror('${escapeHtml(name)}')"
                                                    title="Sync from Host">
                                                <i class="bi bi-arrow-repeat"></i>
                                            </button>
                                            <button class="btn btn-outline-purple" 
                                                    onclick="downloadMirror('${escapeHtml(name)}')"
                                                    title="Download from Sandbox">
                                                <i class="bi bi-download"></i>
                                            </button>
                                            <button class="btn btn-outline-danger" 
                                                    onclick="deleteMirror('${escapeHtml(name)}')"
                                                    title="Delete Mirror">
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
        `;

        document.getElementById('mirrorContainer').innerHTML = tableHTML;
    } catch (error) {
        console.error('Error loading mirrors:', error);
        document.getElementById('mirrorContainer').innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle-fill"></i>
                Failed to load mirrors. Please refresh the page.
            </div>
        `;
    }
}

function formatDateTime(dateString) {
    if (!dateString || dateString === 'unknown' || dateString === 'never') {
        return 'N/A';
    }
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch {
        return dateString;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyAndClose(alertId, text) {
    // Extract command from message (look for /mirror ... @... pattern)
    const textToCopy = text.replace(/<[^>]*>/g, ''); // Strip HTML tags first
    const commandMatch = textToCopy.match(/\/mirror\s+\S+\s+@\S+/);
    const finalText = commandMatch ? commandMatch[0] : textToCopy;
    
    navigator.clipboard.writeText(finalText).then(() => {
        console.log('Copied to clipboard:', finalText);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
    
    // Close the alert
    const alert = document.getElementById(alertId);
    if (alert) {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }
}

function showMessage(message, type = 'success') {
    const alertClass = type === 'error' ? 'alert-danger' : 'alert-success';
    const icon = type === 'error' ? 'bi-x-circle-fill' : 'bi-check-circle-fill';
    
    const alertId = 'alert-' + Date.now();
    document.getElementById('message').innerHTML = `
        <div id="${alertId}" class="alert ${alertClass} alert-dismissible fade show d-flex justify-content-between align-items-center" role="alert">
            <span><i class="bi ${icon}"></i> ${message}</span>
            <button type="button" class="btn btn-sm btn-link text-decoration-none p-0 ms-3" 
                    onclick="copyAndClose('${alertId}', \`${message.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)"
                    title="Copy to clipboard and close">
                <i class="bi bi-clipboard"></i>
            </button>
        </div>
    `;
    
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }
    }, 5000);
}

async function syncMirror(name) {
    showMessage(`Sync operation requires running the CLI command: /mirror sync @${name}`, 'info');
}

async function downloadMirror(name) {
    try {
        showMessage(`Downloading mirror '${name}'...`, 'info');
        window.location.href = `/download-mirror/${name}`;
        setTimeout(() => showMessage(`Mirror '${name}' download started`, 'success'), 1000);
    } catch (error) {
        showMessage(`Failed to download: ${error.message}`, 'error');
    }
}

async function deleteMirror(name) {
    if (!confirm(`Are you sure you want to delete mirror '${name}'? This will remove it from the sandbox.`)) {
        return;
    }

    try {
        const response = await fetch(`/mirrors/remove/${name}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showMessage(`Mirror '${name}' deleted successfully`, 'success');
            setTimeout(() => loadMirrors(), 1000);
        } else {
            const data = await response.json();
            showMessage(`Failed to delete: ${data.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Failed to delete: ${error.message}`, 'error');
    }
}

// Load mirrors on page load
loadMirrors();

// Auto-refresh every 10 seconds
setInterval(loadMirrors, 10000);
