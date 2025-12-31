#!/bin/bash
# Production Environment Setup Wizard for Chatwork-Lark Bridge

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo ""
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

prompt_input() {
    local prompt="$1"
    local var_name="$2"
    local default="$3"

    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        eval $var_name=\"${input:-$default}\"
    else
        read -p "$prompt: " input
        while [ -z "$input" ]; do
            print_warn "This field is required"
            read -p "$prompt: " input
        done
        eval $var_name=\"$input\"
    fi
}

prompt_secret() {
    local prompt="$1"
    local var_name="$2"

    read -sp "$prompt: " input
    echo ""
    while [ -z "$input" ]; do
        print_warn "This field is required"
        read -sp "$prompt: " input
        echo ""
    done
    eval $var_name=\"$input\"
}

# Main setup wizard
main() {
    clear
    print_header "Chatwork-Lark Bridge - Production Setup Wizard"

    echo "This wizard will help you configure the production environment."
    echo "Please have the following information ready:"
    echo "  - Chatwork API Token"
    echo "  - Chatwork Webhook Secret"
    echo "  - Lark App ID, App Secret, Verification Token"
    echo "  - Domain name for deployment"
    echo ""
    read -p "Press Enter to continue..."
    echo ""

    # Step 1: Basic Information
    print_header "Step 1: Basic Information"

    prompt_input "Your domain name (e.g., chatwork-lark.example.com)" DOMAIN
    prompt_input "Environment name" ENVIRONMENT "production"
    prompt_input "Kubernetes namespace" NAMESPACE "chatwork-lark"

    # Step 2: Chatwork Configuration
    print_header "Step 2: Chatwork Configuration"

    prompt_secret "Chatwork API Token" CHATWORK_API_TOKEN
    prompt_secret "Chatwork Webhook Secret (Base64 encoded)" CHATWORK_WEBHOOK_SECRET

    # Step 3: Lark Configuration
    print_header "Step 3: Lark Configuration"

    prompt_input "Lark App ID (cli_xxxxx)" LARK_APP_ID
    prompt_secret "Lark App Secret" LARK_APP_SECRET
    prompt_secret "Lark Verification Token" LARK_VERIFICATION_TOKEN

    # Step 4: Deployment Options
    print_header "Step 4: Deployment Options"

    prompt_input "Number of replicas" REPLICAS "2"
    prompt_input "Use Sealed Secrets? (yes/no)" USE_SEALED_SECRETS "yes"
    prompt_input "Enable TLS with Let's Encrypt? (yes/no)" ENABLE_TLS "yes"

    # Summary
    print_header "Configuration Summary"

    echo "Domain: $DOMAIN"
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Replicas: $REPLICAS"
    echo "Sealed Secrets: $USE_SEALED_SECRETS"
    echo "TLS: $ENABLE_TLS"
    echo ""
    echo "Chatwork API Token: ${CHATWORK_API_TOKEN:0:10}..."
    echo "Lark App ID: $LARK_APP_ID"
    echo ""

    read -p "Is this correct? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        print_error "Setup cancelled"
        exit 1
    fi

    # Generate configuration files
    print_header "Generating Configuration Files"

    # Create production directory
    mkdir -p k8s/production

    # Generate secret
    if [ "$USE_SEALED_SECRETS" == "yes" ]; then
        print_info "Generating Sealed Secret..."
        generate_sealed_secret
    else
        print_info "Generating Kubernetes Secret..."
        generate_k8s_secret
    fi

    # Generate ConfigMap
    print_info "Generating ConfigMap..."
    generate_configmap

    # Generate Ingress
    print_info "Generating Ingress..."
    generate_ingress

    # Generate deployment with custom replicas
    print_info "Generating Deployment..."
    generate_deployment

    # Create deployment script
    print_info "Creating deployment script..."
    create_deploy_script

    # Summary
    print_header "Setup Complete!"

    print_info "Configuration files created in k8s/production/"
    echo ""
    echo "Next steps:"
    echo "1. Review generated files in k8s/production/"
    echo "2. Update room_mappings.json and user_mappings.json in ConfigMap"
    echo "3. Run: ./k8s/production/deploy-production.sh"
    echo ""
    print_warn "IMPORTANT: Keep your secrets safe and never commit them to git!"
}

generate_sealed_secret() {
    cat > k8s/production/secret-unsealed.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: chatwork-lark-secrets
  namespace: $NAMESPACE
type: Opaque
stringData:
  chatwork-api-token: "$CHATWORK_API_TOKEN"
  chatwork-webhook-secret: "$CHATWORK_WEBHOOK_SECRET"
  lark-app-id: "$LARK_APP_ID"
  lark-app-secret: "$LARK_APP_SECRET"
  lark-verification-token: "$LARK_VERIFICATION_TOKEN"
EOF

    if command -v kubeseal &> /dev/null; then
        kubeseal -f k8s/production/secret-unsealed.yaml -w k8s/production/sealed-secret.yaml
        rm k8s/production/secret-unsealed.yaml
        print_info "Sealed Secret created: k8s/production/sealed-secret.yaml"
    else
        print_warn "kubeseal not found. Please install it and run:"
        print_warn "kubeseal -f k8s/production/secret-unsealed.yaml -w k8s/production/sealed-secret.yaml"
        print_warn "Then delete k8s/production/secret-unsealed.yaml"
    fi
}

generate_k8s_secret() {
    cat > k8s/production/secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: chatwork-lark-secrets
  namespace: $NAMESPACE
type: Opaque
stringData:
  chatwork-api-token: "$CHATWORK_API_TOKEN"
  chatwork-webhook-secret: "$CHATWORK_WEBHOOK_SECRET"
  lark-app-id: "$LARK_APP_ID"
  lark-app-secret: "$LARK_APP_SECRET"
  lark-verification-token: "$LARK_VERIFICATION_TOKEN"
EOF

    print_warn "Secret file created. Do NOT commit to git!"
}

generate_configmap() {
    cat > k8s/production/configmap.yaml <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: chatwork-lark-config
  namespace: $NAMESPACE
data:
  log_level: "INFO"
  redis_url: "redis://redis-service:6379/0"
  enable_loop_detection: "true"
  message_prefix_chatwork: "[From Chatwork]"
  message_prefix_lark: "[From Lark]"
  max_retry_attempts: "3"
  max_message_length: "4000"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: chatwork-lark-mappings
  namespace: $NAMESPACE
data:
  room_mappings.json: |
    {
      "mappings": [
        {
          "chatwork_room_id": "REPLACE_WITH_ACTUAL_ROOM_ID",
          "lark_chat_id": "REPLACE_WITH_ACTUAL_CHAT_ID",
          "name": "General Discussion",
          "is_active": true,
          "sync_direction": "both"
        }
      ]
    }

  user_mappings.json: |
    {
      "mappings": [
        {
          "chatwork_user_id": "REPLACE_WITH_ACTUAL_USER_ID",
          "lark_user_id": "REPLACE_WITH_ACTUAL_OPEN_ID",
          "display_name": "User Name",
          "is_active": true
        }
      ]
    }
EOF

    print_warn "Please update room_mappings.json and user_mappings.json with actual values"
}

generate_ingress() {
    cat > k8s/production/ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: chatwork-lark-ingress
  namespace: $NAMESPACE
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
EOF

    if [ "$ENABLE_TLS" == "yes" ]; then
        cat >> k8s/production/ingress.yaml <<EOF
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
EOF
    fi

    cat >> k8s/production/ingress.yaml <<EOF
spec:
  ingressClassName: nginx
EOF

    if [ "$ENABLE_TLS" == "yes" ]; then
        cat >> k8s/production/ingress.yaml <<EOF
  tls:
    - hosts:
        - $DOMAIN
      secretName: chatwork-lark-tls
EOF
    fi

    cat >> k8s/production/ingress.yaml <<EOF
  rules:
    - host: $DOMAIN
      http:
        paths:
          - path: /webhook
            pathType: Prefix
            backend:
              service:
                name: chatwork-lark-service
                port:
                  number: 80
          - path: /health
            pathType: Prefix
            backend:
              service:
                name: chatwork-lark-service
                port:
                  number: 80
EOF
}

generate_deployment() {
    cp k8s/deployment.yaml k8s/production/deployment.yaml

    # Update replicas
    sed -i.bak "s/replicas: 2/replicas: $REPLICAS/" k8s/production/deployment.yaml
    rm k8s/production/deployment.yaml.bak 2>/dev/null || true
}

create_deploy_script() {
    cat > k8s/production/deploy-production.sh <<'EOF'
#!/bin/bash
set -e

NAMESPACE="$NAMESPACE"

echo "==================================="
echo "Chatwork-Lark Bridge - Production Deployment"
echo "==================================="
echo ""

# Create namespace
echo "[1/7] Creating namespace..."
kubectl apply -f ../../k8s/namespace.yaml

# Apply secrets
echo "[2/7] Applying secrets..."
if [ -f sealed-secret.yaml ]; then
    kubectl apply -f sealed-secret.yaml
elif [ -f secret.yaml ]; then
    kubectl apply -f secret.yaml
else
    echo "ERROR: No secret file found!"
    exit 1
fi

# Apply ConfigMap
echo "[3/7] Applying ConfigMap..."
kubectl apply -f configmap.yaml

# Deploy Redis
echo "[4/7] Deploying Redis..."
kubectl apply -f ../../k8s/redis-deployment.yaml
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=60s

# Deploy application
echo "[5/7] Deploying application..."
kubectl apply -f deployment.yaml
kubectl apply -f ../../k8s/service.yaml

# Wait for deployment
echo "[6/7] Waiting for deployment..."
kubectl wait --for=condition=available deployment/chatwork-lark-bridge -n $NAMESPACE --timeout=120s

# Apply Ingress
echo "[7/7] Applying Ingress..."
kubectl apply -f ingress.yaml

echo ""
echo "==================================="
echo "Deployment Complete!"
echo "==================================="
echo ""

# Show status
echo "Pods:"
kubectl get pods -n $NAMESPACE
echo ""
echo "Services:"
kubectl get svc -n $NAMESPACE
echo ""
echo "Ingress:"
kubectl get ingress -n $NAMESPACE
echo ""
echo "Check logs:"
echo "  kubectl logs -n $NAMESPACE -l app=chatwork-lark-bridge -f"
EOF

    chmod +x k8s/production/deploy-production.sh

    # Replace $NAMESPACE in the script
    sed -i.bak "s/\$NAMESPACE/$NAMESPACE/" k8s/production/deploy-production.sh
    rm k8s/production/deploy-production.sh.bak 2>/dev/null || true
}

# Run main
main
