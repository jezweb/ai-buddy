#!/bin/bash
# AI Buddy Test Runner

set -e

echo "🧪 AI Buddy Test Suite"
echo "===================="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  No virtual environment found. Creating one...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate || source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
else
    # Activate virtual environment
    source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null || true
fi

# Install/upgrade test dependencies
echo "📦 Ensuring test dependencies are installed..."
pip install -q -r requirements-dev.txt

# Run linting
echo
echo "🔍 Running code quality checks..."
echo "================================"

# Black formatting check
echo -n "  Black formatter: "
if black --check . --exclude="venv|.venv|tests/fixtures" 2>/dev/null; then
    echo -e "${GREEN}✓ Passed${NC}"
else
    echo -e "${YELLOW}⚠ Would reformat files${NC}"
    echo "    Run 'black .' to fix formatting"
fi

# Flake8 linting
echo -n "  Flake8 linter: "
if flake8 . --exclude=venv,.venv,tests/fixtures --max-line-length=100 2>/dev/null; then
    echo -e "${GREEN}✓ Passed${NC}"
else
    echo -e "${YELLOW}⚠ Found issues${NC}"
fi

# Run tests
echo
echo "🧪 Running tests..."
echo "=================="

# Run pytest with coverage
if pytest -v --cov=. --cov-report=term-missing --cov-report=html; then
    echo
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo
    echo "📊 Coverage report generated in htmlcov/index.html"
else
    echo
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

# Test summary
echo
echo "📈 Test Summary"
echo "=============="
echo "  - Unit tests: $(pytest --collect-only -q -m unit 2>/dev/null | grep -c '<Module' || echo 0)"
echo "  - Integration tests: $(pytest --collect-only -q -m integration 2>/dev/null | grep -c '<Module' || echo 0)"
echo "  - Total test files: $(find tests -name 'test_*.py' | wc -l)"

# Optional: Run specific test categories
if [ "$1" == "unit" ]; then
    echo
    echo "🧪 Running only unit tests..."
    pytest -v -m unit
elif [ "$1" == "integration" ]; then
    echo
    echo "🧪 Running only integration tests..."
    pytest -v -m integration
elif [ "$1" == "slow" ]; then
    echo
    echo "🧪 Running slow tests..."
    pytest -v -m slow
fi

echo
echo "✨ Test run complete!"