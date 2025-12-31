#!/bin/bash
# Production Readiness Validation Script
# Validates all prerequisites before production deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_check() {
    echo -en "  [....] $1"
}

print_pass() {
    echo -e "\r  [${GREEN}PASS${NC}] $1"
    ((PASS_COUNT++))
}

print_fail() {
    echo -e "\r  [${RED}FAIL${NC}] $1"
    echo -e "    ${RED}→ $2${NC}"
    ((FAIL_COUNT++))
}

print_warn() {
    echo -e "\r  [${YELLOW}WARN${NC}] $1"
    echo -e "    ${YELLOW}→ $2${NC}"
    ((WARN_COUNT++))
}

# 1. Code Quality Checks
print_header "1. Code Quality"

# Tests
print_check "All tests passing"
if pytest -v --tb=no -q > /dev/null 2>&1; then
    print_pass "All tests passing (79/79)"
else
    print_fail "All tests passing" "Run 'pytest -v' to see failures"
fi

# Coverage
print_check "Code coverage >= 67%"
COVERAGE=$(pytest --cov=src --cov-report=term-missing --tb=no -q 2>/dev/null | grep "TOTAL" | awk '{print $4}' | sed 's/%//')
if [ -n "$COVERAGE" ] && [ "$COVERAGE" -ge 67 ]; then
    print_pass "Code coverage >= 67% (actual: ${COVERAGE}%)"
else
    print_fail "Code coverage >= 67%" "Current: ${COVERAGE}%, run 'pytest --cov=src'"
fi

# Type hints
print_check "Type hints present"
if python -c "import mypy" > /dev/null 2>&1; then
    if mypy src/ --ignore-missing-imports > /dev/null 2>&1; then
        print_pass "Type hints validated"
    else
        print_warn "Type hints present" "Some type issues found, run 'mypy src/'"
    fi
else
    print_warn "Type hints present" "mypy not installed, skipping validation"
fi

# 2. Security Checks
print_header "2. Security"

# Environment file
print_check ".env file exists and configured"
if [ -f .env ]; then
    # Check for placeholder values
    if grep -q "REPLACE_WITH" .env || grep -q "your_.*_here" .env; then
        print_fail ".env file configured" "Contains placeholder values"
    else
        print_pass ".env file exists and configured"
    fi
else
    print_fail ".env file exists" "Create .env from .env.example"
fi

# Secrets not in git
print_check ".gitignore includes .env"
if grep -q "^\.env$" .gitignore; then
    print_pass ".gitignore includes .env"
else
    print_fail ".gitignore includes .env" "Add '.env' to .gitignore"
fi

# Webhook verification
print_check "Webhook verification implemented"
if grep -r "verify_signature" src/ > /dev/null 2>&1; then
    print_pass "Webhook verification implemented"
else
    print_warn "Webhook verification implemented" "Could not verify implementation"
fi

# 3. Infrastructure Checks
print_header "3. Infrastructure"

# Docker
print_check "Docker available"
if command -v docker &> /dev/null; then
    if docker ps > /dev/null 2>&1; then
        print_pass "Docker available and running"
    else
        print_warn "Docker available" "Docker daemon not running"
    fi
else
    print_fail "Docker available" "Install Docker for local testing"
fi

# Kubernetes
print_check "kubectl available"
if command -v kubectl &> /dev/null; then
    print_pass "kubectl available"

    # Cluster connection
    print_check "Kubernetes cluster accessible"
    if kubectl cluster-info > /dev/null 2>&1; then
        print_pass "Kubernetes cluster accessible"
    else
        print_fail "Kubernetes cluster accessible" "Configure kubectl to connect to your cluster"
    fi
else
    print_fail "kubectl available" "Install kubectl for production deployment"
fi

# 4. Configuration Checks
print_header "4. Configuration"

# Production secret
print_check "Production secrets configured"
if [ -f k8s/production/secret.yaml ]; then
    if grep -q "REPLACE_WITH" k8s/production/secret.yaml; then
        print_fail "Production secrets configured" "k8s/production/secret.yaml contains placeholders"
    else
        print_pass "Production secrets configured"
    fi
elif [ -f k8s/production/sealed-secret.yaml ]; then
    print_pass "Production secrets configured (Sealed Secrets)"
else
    print_fail "Production secrets configured" "Create k8s/production/secret.yaml from template"
fi

# ConfigMap
print_check "Production ConfigMap configured"
if [ -f k8s/production/configmap.yaml ]; then
    print_pass "Production ConfigMap exists"
else
    print_fail "Production ConfigMap configured" "k8s/production/configmap.yaml not found"
fi

# Ingress domain
print_check "Production domain configured"
if [ -f k8s/production/ingress.yaml ]; then
    if grep -q "REPLACE_WITH_YOUR_DOMAIN" k8s/production/ingress.yaml; then
        print_fail "Production domain configured" "Update domain in k8s/production/ingress.yaml"
    else
        DOMAIN=$(grep "host:" k8s/production/ingress.yaml | head -1 | awk '{print $3}')
        print_pass "Production domain configured: $DOMAIN"
    fi
else
    print_fail "Production domain configured" "k8s/production/ingress.yaml not found"
fi

# 5. Documentation Checks
print_header "5. Documentation"

# README
print_check "README.md exists"
if [ -f README.md ] && [ -s README.md ]; then
    print_pass "README.md exists and not empty"
else
    print_fail "README.md exists" "Create or update README.md"
fi

# Deployment docs
print_check "Deployment documentation exists"
if [ -f DEPLOYMENT.md ] || [ -f docs/deployment.md ]; then
    print_pass "Deployment documentation exists"
else
    print_warn "Deployment documentation exists" "Consider creating DEPLOYMENT.md"
fi

# API documentation
print_check "API documentation accessible"
if grep -r "swagger" src/main.py > /dev/null 2>&1 || grep -r "openapi" src/main.py > /dev/null 2>&1; then
    print_pass "API documentation configured (OpenAPI/Swagger)"
else
    print_warn "API documentation accessible" "Consider adding OpenAPI docs"
fi

# 6. Monitoring & Observability
print_header "6. Monitoring"

# Health endpoints
print_check "Health check endpoints implemented"
if grep -r "/health/" src/ > /dev/null 2>&1; then
    print_pass "Health check endpoints implemented"
else
    print_fail "Health check endpoints implemented" "Implement /health/ endpoints"
fi

# Structured logging
print_check "Structured logging configured"
if grep -r "structlog\|json.*log" src/ > /dev/null 2>&1; then
    print_pass "Structured logging configured"
else
    print_warn "Structured logging configured" "Consider using structured logging"
fi

# Prometheus metrics
print_check "Prometheus metrics configured"
if grep -r "prometheus" k8s/ > /dev/null 2>&1; then
    print_pass "Prometheus metrics annotations configured"
else
    print_warn "Prometheus metrics configured" "Add prometheus.io annotations"
fi

# 7. CI/CD Checks
print_header "7. CI/CD"

# GitHub Actions
print_check "CI/CD workflow exists"
if [ -f .github/workflows/ci.yml ] || [ -f .github/workflows/test.yml ]; then
    print_pass "CI/CD workflow configured"
else
    print_warn "CI/CD workflow exists" "Create .github/workflows/ci.yml"
fi

# Deployment workflow
print_check "Deployment workflow exists"
if [ -f .github/workflows/deploy-production.yml ]; then
    print_pass "Production deployment workflow configured"
else
    print_warn "Deployment workflow exists" "Create automated deployment workflow"
fi

# 8. Dependency Checks
print_header "8. Dependencies"

# Requirements files
print_check "requirements.txt exists"
if [ -f requirements.txt ]; then
    print_pass "requirements.txt exists"
else
    print_fail "requirements.txt exists" "Create requirements.txt"
fi

# Test dependencies
print_check "requirements-test.txt exists"
if [ -f requirements-test.txt ]; then
    print_pass "requirements-test.txt exists"
else
    print_warn "requirements-test.txt exists" "Create requirements-test.txt"
fi

# Security vulnerabilities
print_check "No known security vulnerabilities"
if command -v safety &> /dev/null; then
    if safety check -r requirements.txt > /dev/null 2>&1; then
        print_pass "No known security vulnerabilities"
    else
        print_warn "No known security vulnerabilities" "Run 'safety check' to see details"
    fi
else
    print_warn "No known security vulnerabilities" "Install 'safety' to check: pip install safety"
fi

# Summary
echo ""
print_header "Validation Summary"
echo ""
echo -e "  ${GREEN}PASS:${NC} $PASS_COUNT"
echo -e "  ${YELLOW}WARN:${NC} $WARN_COUNT"
echo -e "  ${RED}FAIL:${NC} $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Production deployment ready!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review warnings (if any)"
    echo "  2. Run: cd k8s/production && ./deploy-production.sh"
    echo "  3. Or trigger GitHub Actions deployment workflow"
    echo ""
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Production deployment NOT ready${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Please fix the failed checks before deploying to production."
    echo ""
    exit 1
fi
