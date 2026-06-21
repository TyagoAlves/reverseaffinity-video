#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Running coverage ==="
python3 -m pytest tests/ \
    --cov=editor \
    --cov-report=term \
    --cov-report=html \
    --cov-report=xml \
    -v --tb=short \
    -m 'not slow and not stress and not perf and not gui' \
    -x \
    2>&1 | tee coverage_report.txt

echo ""
echo "=== Coverage HTML report: htmlcov/index.html ==="
echo "=== Coverage XML report:  coverage.xml ==="
