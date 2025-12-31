#!/bin/bash
# Quick deployment script for Chatwork-Lark Bridge

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    if [ "$1" == "docker" ]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker is not installed"
            exit 1
        fi

        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose is not installed"
            exit 1
        fi

        print_info "Docker and Docker Compose are installed"
    elif [ "$1" == "k8s" ]; then
        if ! command -v kubectl &> /dev/null; then
            print_error "kubectl is not installed"
            exit 1
        fi

        print_info "kubectl is installed"
    fi
}

# Docker Compose deployment
deploy_docker() {
    print_info "Deploying with Docker Compose..."

    # Check .env file
    if [ ! -f .env ]; then
        print_warn ".env file not found. Copying from .env.example..."
        cp .env.example .env
        print_error "Please edit .env file with your actual credentials before running again"
        exit 1
    fi

    # Check config directory
    if [ ! -d config ]; then
        print_warn "config directory not found. Creating..."
        mkdir -p config
        print_error "Please add room_mappings.json and user_mappings.json to config/ directory"
        exit 1
    fi

    # Build and start
    print_info "Building Docker images..."
    docker-compose build

    print_info "Starting services..."
    docker-compose up -d

    # Wait for health check
    print_info "Waiting for services to be healthy..."
    sleep 10

    # Check health
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        print_info "✅ Deployment successful!"
        print_info "Application is running at http://localhost:8000"
        print_info "Health check: http://localhost:8000/health/"
        print_info ""
        print_info "To view logs: docker-compose logs -f app"
        print_info "To stop: docker-compose down"
    else
        print_error "❌ Health check failed"
        print_info "Check logs: docker-compose logs app"
        exit 1
    fi
}

# Kubernetes deployment
deploy_k8s() {
    print_info "Deploying to Kubernetes..."

    # Check if kubectl can connect
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Create namespace
    print_info "Creating namespace..."
    kubectl apply -f k8s/namespace.yaml

    # Check if secrets exist
    if ! kubectl get secret chatwork-lark-secrets -n chatwork-lark &> /dev/null; then
        print_warn "Secrets not found. Applying template..."
        print_error "⚠️  IMPORTANT: Edit k8s/secret.yaml with actual credentials before using in production!"
        kubectl apply -f k8s/secret.yaml
    fi

    # Apply configurations
    print_info "Applying configurations..."
    kubectl apply -f k8s/configmap.yaml

    # Deploy Redis
    print_info "Deploying Redis..."
    kubectl apply -f k8s/redis-deployment.yaml

    # Wait for Redis
    print_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis -n chatwork-lark --timeout=60s

    # Deploy application
    print_info "Deploying application..."
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml

    # Wait for deployment
    print_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available deployment/chatwork-lark-bridge -n chatwork-lark --timeout=120s

    # Apply ingress
    if [ -f k8s/ingress.yaml ]; then
        print_info "Applying Ingress..."
        kubectl apply -f k8s/ingress.yaml
    fi

    # Get status
    print_info "✅ Deployment successful!"
    print_info ""
    print_info "Pods:"
    kubectl get pods -n chatwork-lark
    print_info ""
    print_info "Services:"
    kubectl get svc -n chatwork-lark
    print_info ""
    print_info "To view logs: kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f"
    print_info "To delete: kubectl delete namespace chatwork-lark"
}

# Kustomize deployment
deploy_kustomize() {
    print_info "Deploying with Kustomize..."

    # Preview
    print_info "Preview of resources to be created:"
    kubectl kustomize k8s/

    read -p "Do you want to apply these resources? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl apply -k k8s/
        print_info "✅ Deployment successful!"
    else
        print_info "Deployment cancelled"
        exit 0
    fi
}

# Main
main() {
    echo "==================================="
    echo "Chatwork-Lark Bridge Deployment"
    echo "==================================="
    echo ""

    if [ -z "$1" ]; then
        echo "Usage: $0 <docker|k8s|kustomize>"
        echo ""
        echo "Options:"
        echo "  docker      - Deploy with Docker Compose"
        echo "  k8s         - Deploy to Kubernetes"
        echo "  kustomize   - Deploy with Kustomize"
        echo ""
        exit 1
    fi

    case "$1" in
        docker)
            check_prerequisites docker
            deploy_docker
            ;;
        k8s)
            check_prerequisites k8s
            deploy_k8s
            ;;
        kustomize)
            check_prerequisites k8s
            deploy_kustomize
            ;;
        *)
            print_error "Invalid option: $1"
            echo "Use: docker, k8s, or kustomize"
            exit 1
            ;;
    esac
}

main "$@"
