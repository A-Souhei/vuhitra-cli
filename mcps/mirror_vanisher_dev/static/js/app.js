// Mirror+Vanisher Development MCP - JavaScript

let selectedPath = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadMirrorVanishers();
    setupTabs();
    setupRefreshButton();
});

// Load mirror+vanisher list
async function loadMirrorVanishers() {
    const listEl = document.getElementById('mirrorList');
    listEl.innerHTML = '<p class="loading"><span class="spinner"></span>Loading...</p>';

    try {
        const response = await fetch('/api/mirror-vanishers');
        const data = await response.json();

        if (data.success && data.mirror_vanishers.length > 0) {
            let html = '';
            data.mirror_vanishers.forEach(mv => {
                html += `
                    <div class="mirror-item" onclick="selectMirrorVanisher('${mv.name}', '${mv.path}')">
                        <h4>📁 ${mv.name}</h4>
                        <p><strong>Path:</strong> ${mv.path}</p>
                        <p><strong>Files:</strong> ${mv.file_count} | <strong>Status:</strong> ${mv.sync_status}</p>
                    </div>
                `;
            });
            listEl.innerHTML = html;
        } else {
            listEl.innerHTML = '<p class="loading">No mirror+vanisher directories found. Create one first!</p>';
        }
    } catch (error) {
        listEl.innerHTML = `<p class="loading error">Error loading: ${error.message}</p>`;
    }
}

// Select mirror+vanisher
function selectMirrorVanisher(name, path) {
    selectedPath = path;

    // Update UI
    document.querySelectorAll('.mirror-item').forEach(item => {
        item.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');
}

// Setup tabs
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        });
    });
}

// Setup refresh button
function setupRefreshButton() {
    document.getElementById('refreshBtn').addEventListener('click', loadMirrorVanishers);
}

// Utility function to check if path is selected
function checkPathSelected() {
    if (!selectedPath) {
        alert('Please select a mirror+vanisher directory first!');
        return false;
    }
    return true;
}

// Utility function to show result
function showResult(elementId, data, isSuccess) {
    const resultEl = document.getElementById(elementId);
    resultEl.className = 'result show ' + (isSuccess ? 'success' : 'error');
    resultEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// Exploration
async function runExploration() {
    if (!checkPathSelected()) return;

    const resultEl = document.getElementById('explorationResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Running exploration...';

    try {
        const response = await fetch('/api/explore', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath, max_depth: 3})
        });
        const data = await response.json();
        showResult('explorationResult', data, data.success);
    } catch (error) {
        showResult('explorationResult', {error: error.message}, false);
    }
}

// Architecture Analysis
async function runArchitectureAnalysis() {
    if (!checkPathSelected()) return;

    const resultEl = document.getElementById('architectureResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Analyzing architecture...';

    try {
        const response = await fetch('/api/architecture', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath})
        });
        const data = await response.json();
        showResult('architectureResult', data, data.success);
    } catch (error) {
        showResult('architectureResult', {error: error.message}, false);
    }
}

// Planning
async function createPlan() {
    if (!checkPathSelected()) return;

    const task = document.getElementById('taskInput').value.trim();
    if (!task) {
        alert('Please enter a task description!');
        return;
    }

    const resultEl = document.getElementById('planningResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Creating plan...';

    try {
        const response = await fetch('/api/plan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath, task: task})
        });
        const data = await response.json();
        showResult('planningResult', data, data.success);
    } catch (error) {
        showResult('planningResult', {error: error.message}, false);
    }
}

// Testing
async function runTests() {
    if (!checkPathSelected()) return;

    const resultEl = document.getElementById('testingResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Running tests...';

    try {
        const response = await fetch('/api/test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath})
        });
        const data = await response.json();
        showResult('testingResult', data, data.success);
    } catch (error) {
        showResult('testingResult', {error: error.message}, false);
    }
}

// Quality Check
async function runQualityCheck() {
    if (!checkPathSelected()) return;

    const fix = document.getElementById('autoFixCheck').checked;
    const resultEl = document.getElementById('qualityResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Running quality checks...';

    try {
        const response = await fetch('/api/quality-check', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath, fix: fix})
        });
        const data = await response.json();
        showResult('qualityResult', data, data.success);
    } catch (error) {
        showResult('qualityResult', {error: error.message}, false);
    }
}

// Security Audit
async function runSecurityAudit() {
    if (!checkPathSelected()) return;

    const resultEl = document.getElementById('securityResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Running security audit...';

    try {
        const response = await fetch('/api/security-audit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath})
        });
        const data = await response.json();
        showResult('securityResult', data, data.success);
    } catch (error) {
        showResult('securityResult', {error: error.message}, false);
    }
}

// Feature Workflow
async function runFeatureWorkflow() {
    if (!checkPathSelected()) return;

    const feature = document.getElementById('featureInput').value.trim();
    if (!feature) {
        alert('Please enter a feature description!');
        return;
    }

    const resultEl = document.getElementById('workflowResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Starting feature workflow...';

    try {
        const response = await fetch('/api/workflow/feature', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath, feature_description: feature})
        });
        const data = await response.json();
        showResult('workflowResult', data, data.success);
    } catch (error) {
        showResult('workflowResult', {error: error.message}, false);
    }
}

// Bugfix Workflow
async function runBugfixWorkflow() {
    if (!checkPathSelected()) return;

    const bug = document.getElementById('bugInput').value.trim();
    if (!bug) {
        alert('Please enter a bug description!');
        return;
    }

    const resultEl = document.getElementById('workflowResult');
    resultEl.className = 'result show';
    resultEl.innerHTML = '<span class="spinner"></span> Starting bugfix workflow...';

    try {
        const response = await fetch('/api/workflow/bugfix', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: selectedPath, bug_description: bug})
        });
        const data = await response.json();
        showResult('workflowResult', data, data.success);
    } catch (error) {
        showResult('workflowResult', {error: error.message}, false);
    }
}
