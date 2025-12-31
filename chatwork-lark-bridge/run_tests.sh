#!/bin/bash
# Test runner script for Chatwork-Lark Bridge

set -e

echo "🧪 Chatwork-Lark Bridge Test Runner"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default mode
MODE=${1:-all}

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Install dependencies if needed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -r requirements-test.txt
fi

echo ""

case $MODE in
    "unit")
        echo -e "${GREEN}Running unit tests...${NC}"
        pytest tests/unit -v -m unit --cov=src --cov-report=term-missing
        ;;

    "integration")
        echo -e "${GREEN}Running integration tests...${NC}"
        pytest tests/integration -v -m integration --cov=src --cov-report=term-missing
        ;;

    "e2e")
        echo -e "${GREEN}Running E2E tests...${NC}"
        pytest tests/e2e -v -m e2e --cov=src --cov-report=term-missing
        ;;

    "fast")
        echo -e "${GREEN}Running fast tests (excluding slow)...${NC}"
        pytest -v -m "not slow" --cov=src --cov-report=term-missing
        ;;

    "coverage")
        echo -e "${GREEN}Running all tests with detailed coverage...${NC}"
        pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80
        echo ""
        echo -e "${BLUE}Coverage report generated at: htmlcov/index.html${NC}"
        ;;

    "ci")
        echo -e "${GREEN}Running CI mode (strict)...${NC}"
        pytest --cov=src --cov-report=xml --cov-fail-under=80 -W error
        echo ""
        echo -e "${GREEN}✅ All tests passed with coverage ≥ 80%${NC}"
        ;;

    "watch")
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        if ! command -v ptw &> /dev/null; then
            pip install pytest-watch
        fi
        ptw -- -v
        ;;

    "all"|*)
        echo -e "${GREEN}Running all tests...${NC}"
        echo ""
        echo -e "${BLUE}1. Unit tests${NC}"
        pytest tests/unit -v -m unit

        echo ""
        echo -e "${BLUE}2. Integration tests${NC}"
        pytest tests/integration -v -m integration

        echo ""
        echo -e "${BLUE}3. E2E tests${NC}"
        pytest tests/e2e -v -m e2e

        echo ""
        echo -e "${BLUE}4. Coverage report${NC}"
        pytest --cov=src --cov-report=term-missing --cov-fail-under=80

        echo ""
        echo -e "${GREEN}✅ All test suites completed!${NC}"
        ;;
esac

echo ""
echo "===================================="
echo -e "${GREEN}Done!${NC}"
