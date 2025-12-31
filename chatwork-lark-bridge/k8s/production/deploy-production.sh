#!/bin/bash
# Production Deployment Script for Chatwork-Lark Bridge

set -e

NAMESPACE="chatwork-lark"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=====================================${NC}"
}

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

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    print_info "Prerequisites OK"
}

# Main deployment
main() {
    clear
    print_header "Chatwork-Lark Bridge - Production Deployment"

    check_prerequisites

    echo ""
    echo "This will deploy Chatwork-Lark Bridge to production."
    echo "Namespace: $NAMESPACE"
    echo ""
    read -p "Continue? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        print_error "Deployment cancelled"
        exit 1
    fi

    # Step 1: Create namespace
    print_header "[1/8] Creating Namespace"
    kubectl apply -f ../../k8s/namespace.yaml

    # Step 2: Apply secrets
    print_header "[2/8] Applying Secrets"
    if [ -f sealed-secret.yaml ]; then
        print_info "Applying Sealed Secret..."
        kubectl apply -f sealed-secret.yaml
    elif [ -f secret.yaml ]; then
        print_warn "Applying plain Secret (not recommended for production!)"
        kubectl apply -f secret.yaml
    else
        print_error "No secret file found! Please create sealed-secret.yaml or secret.yaml"
        exit 1
    fi

    # Step 3: Apply ConfigMap
    print_header "[3/8] Applying ConfigMap"
    kubectl apply -f configmap.yaml

    # Step 4: Deploy Redis
    print_header "[4/8] Deploying Redis"
    kubectl apply -f ../../k8s/redis-deployment.yaml

    print_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=60s

    # Step 5: Deploy application
    print_header "[5/8] Deploying Application"
    kubectl apply -f deployment.yaml
    kubectl apply -f ../../k8s/service.yaml

    # Step 6: Wait for deployment
    print_header "[6/8] Waiting for Deployment"
    kubectl wait --for=condition=available deployment/chatwork-lark-bridge -n $NAMESPACE --timeout=120s

    # Step 7: Apply Ingress
    print_header "[7/8] Applying Ingress"
    kubectl apply -f ingress.yaml

    # Step 8: Verify deployment
    print_header "[8/8] Verifying Deployment"

    echo ""
    echo "Pods:"
    kubectl get pods -n $NAMESPACE
    echo ""
    echo "Services:"
    kubectl get svc -n $NAMESPACE
    echo ""
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE
    echo ""

    # Get domain from Ingress
    DOMAIN=$(kubectl get ingress chatwork-lark-ingress -n $NAMESPACE -o jsonpath='{.spec.rules[0].host}')

    print_header "Deployment Complete!"

    print_info "Application deployed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Wait for TLS certificate to be issued (may take a few minutes)"
    echo "   kubectl get certificate -n $NAMESPACE"
    echo ""
    echo "2. Check application logs:"
    echo "   kubectl logs -n $NAMESPACE -l app=chatwork-lark-bridge -f"
    echo ""
    echo "3. Test health endpoint:"
    echo "   curl https://$DOMAIN/health/"
    echo ""
    echo "4. Configure Webhooks:"
    echo "   Chatwork: https://$DOMAIN/webhook/chatwork/"
    echo "   Lark: https://$DOMAIN/webhook/lark/"
    echo ""

    print_warn "Don't forget to set up monitoring and alerts!"
}

# Run main
main
