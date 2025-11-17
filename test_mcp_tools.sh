#!/bin/bash
# MCP Tools Testing Script

set -e
BASE_URL="http://localhost:5100"
PROJECT="test-project"

echo "===================================="
echo "MCP TOOLS TESTING"
echo "===================================="
echo ""

echo "=== Test 1: list_mirror_vanishers ==="
curl -s ${BASE_URL}/api/mirror-vanishers | jq -c '{success, count}'
echo ""

echo "=== Test 2: verify_mirror_vanisher ==="
curl -s -X POST ${BASE_URL}/api/verify -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\"}" | jq -c '{success, is_valid: .is_valid_mirror_vanisher}'
echo ""

echo "=== Test 3: full_exploration ==="
curl -s -X POST ${BASE_URL}/api/explore -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\", \"max_depth\": 3}" | \
  jq -c '{success, files: .structure.statistics.total_files, lang: .tech_stack.primary_language}'
echo ""

echo "=== Test 4: analyze_architecture ==="
curl -s -X POST ${BASE_URL}/api/architecture -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\"}" | jq -c '{success, structure_type}'
echo ""

echo "=== Test 5: create_plan ==="
curl -s -X POST ${BASE_URL}/api/plan -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\", \"task\": \"Add input validation\", \"context\": {}}" | \
  jq -c '{success, plan_type: .plan.type, steps: (.plan.steps | length)}'
echo ""

echo "=== Test 6: run_tests ==="
curl -s -X POST ${BASE_URL}/api/test -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\"}" | jq -c '{success, framework: .framework}'
echo ""

echo "=== Test 7: full_quality_check ==="
curl -s -X POST ${BASE_URL}/api/quality-check -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\", \"fix\": false}" | jq -c '{success, all_checks_passed}'
echo ""

echo "=== Test 8: security_audit ==="
curl -s -X POST ${BASE_URL}/api/security-audit -H "Content-Type: application/json" \
  -d "{\"path\": \"${PROJECT}\"}" | jq -c '{success, has_issues: .has_security_issues}'
echo ""

echo "===================================="
echo "Testing Complete"
echo "===================================="
