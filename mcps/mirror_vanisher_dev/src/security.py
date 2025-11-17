"""
Security Tools - Step 8 of the Pillars Methodology

Tools for scanning secrets and checking for vulnerabilities.
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class SecurityTools:
    """Tools for security scanning."""

    def __init__(self, manager):
        """Initialize security tools."""
        self.manager = manager

        # Common secret patterns
        self.secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'API Key'),
            (r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'Password'),
            (r'(?i)(secret|token)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'Secret/Token'),
            (r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'AWS Access Key'),
            (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'AWS Secret Key'),
            (r'(?i)(private[_-]?key)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'Private Key'),
            (r'(?i)(db[_-]?password|database[_-]?password)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 'Database Password'),
            (r'[\'"][0-9a-zA-Z]{32,}[\'"]', 'Potential Secret (32+ chars)'),
        ]

        # Files to skip
        self.skip_files = {
            '.git', 'node_modules', '__pycache__', 'venv', '.venv',
            'dist', 'build', '.pyc', '.min.js', '.bundle.js'
        }

    def scan_secrets(self, path: str) -> Dict[str, Any]:
        """Scan for hardcoded secrets and credentials.

        Args:
            path: Path to scan

        Returns:
            Dictionary with scan results
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                resolved_path = Path(path)
                if not resolved_path.exists():
                    return {'success': False, 'error': f'Path not found: {path}'}

            findings = []

            # Scan all text files
            for root, dirs, files in os.walk(resolved_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.skip_files]

                for file in files:
                    # Skip binary and compiled files
                    if any(file.endswith(ext) for ext in ['.pyc', '.so', '.dll', '.exe', '.bin']):
                        continue

                    file_path = Path(root) / file
                    relative_path = str(file_path.relative_to(resolved_path))

                    try:
                        content = file_path.read_text()

                        # Check each pattern
                        for pattern, secret_type in self.secret_patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                line_num = content[:match.start()].count('\n') + 1
                                findings.append({
                                    'file': relative_path,
                                    'line': line_num,
                                    'type': secret_type,
                                    'severity': 'high',
                                    'context': self._get_line_context(content, line_num)
                                })

                    except (UnicodeDecodeError, PermissionError):
                        continue

            return {
                'success': True,
                'path': str(resolved_path),
                'findings': findings,
                'total_findings': len(findings),
                'severity_breakdown': self._calculate_severity_breakdown(findings),
                'message': f'Found {len(findings)} potential secrets' if findings else 'No secrets found'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'scan_secrets', 'path': path})
            return {'success': False, 'error': str(e)}

    def _get_line_context(self, content: str, line_num: int, context_lines: int = 2) -> List[str]:
        """Get context around a line."""
        lines = content.splitlines()
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        return lines[start:end]

    def _calculate_severity_breakdown(self, findings: List[Dict]) -> Dict[str, int]:
        """Calculate severity breakdown."""
        breakdown = {'high': 0, 'medium': 0, 'low': 0}
        for finding in findings:
            severity = finding.get('severity', 'medium')
            breakdown[severity] = breakdown.get(severity, 0) + 1
        return breakdown

    def check_vulnerabilities(self, path: str) -> Dict[str, Any]:
        """Check dependencies for known vulnerabilities.

        Args:
            path: Path to check

        Returns:
            Dictionary with vulnerability scan results
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                resolved_path = Path(path)
                if not resolved_path.exists():
                    return {'success': False, 'error': f'Path not found: {path}'}

            results = []

            # Check for Python requirements
            requirements_file = resolved_path / 'requirements.txt'
            if requirements_file.exists():
                if self._command_exists('safety'):
                    result = self._run_safety_check(requirements_file)
                    results.append(result)
                else:
                    results.append({
                        'tool': 'safety',
                        'available': False,
                        'message': 'safety not installed (pip install safety)'
                    })

            # Check for package.json
            package_json = resolved_path / 'package.json'
            if package_json.exists():
                if self._command_exists('npm'):
                    result = self._run_npm_audit(resolved_path)
                    results.append(result)
                else:
                    results.append({
                        'tool': 'npm audit',
                        'available': False,
                        'message': 'npm not installed'
                    })

            if not results:
                return {
                    'success': True,
                    'message': 'No dependency files found to scan',
                    'scanned': False
                }

            vulnerabilities_found = any(r.get('vulnerabilities', 0) > 0 for r in results)

            return {
                'success': True,
                'path': str(resolved_path),
                'results': results,
                'vulnerabilities_found': vulnerabilities_found,
                'message': 'Vulnerabilities found' if vulnerabilities_found else 'No vulnerabilities found'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'check_vulnerabilities', 'path': path})
            return {'success': False, 'error': str(e)}

    def _run_safety_check(self, requirements_file: Path) -> Dict[str, Any]:
        """Run safety check on requirements."""
        try:
            process = subprocess.run(
                ['safety', 'check', '--file', str(requirements_file), '--json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                'tool': 'safety',
                'available': True,
                'exit_code': process.returncode,
                'vulnerabilities': process.returncode,  # Non-zero means vulnerabilities found
                'output': process.stdout
            }

        except Exception as e:
            return {
                'tool': 'safety',
                'available': True,
                'error': str(e)
            }

    def _run_npm_audit(self, path: Path) -> Dict[str, Any]:
        """Run npm audit."""
        try:
            process = subprocess.run(
                ['npm', 'audit', '--json'],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                'tool': 'npm audit',
                'available': True,
                'exit_code': process.returncode,
                'vulnerabilities': process.returncode,  # Non-zero means vulnerabilities found
                'output': process.stdout
            }

        except Exception as e:
            return {
                'tool': 'npm audit',
                'available': True,
                'error': str(e)
            }

    def security_audit(self, path: str) -> Dict[str, Any]:
        """Run comprehensive security audit.

        Args:
            path: Path to audit

        Returns:
            Dictionary with complete security audit results
        """
        try:
            secrets_scan = self.scan_secrets(path)
            vulnerabilities_check = self.check_vulnerabilities(path)

            has_issues = (
                secrets_scan.get('total_findings', 0) > 0 or
                vulnerabilities_check.get('vulnerabilities_found', False)
            )

            return {
                'success': True,
                'path': path,
                'secrets_scan': secrets_scan,
                'vulnerabilities_check': vulnerabilities_check,
                'has_security_issues': has_issues,
                'message': 'Security issues found' if has_issues else 'No security issues found'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'security_audit', 'path': path})
            return {'success': False, 'error': str(e)}

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run([command, '--version'], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
