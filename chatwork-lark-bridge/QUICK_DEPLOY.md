# Quick Production Deployment Guide

**Time Required**: 30-60 minutes
**Difficulty**: Intermediate
**Prerequisites**: Kubernetes cluster, kubectl, domain name

---

## 3-Step Production Deployment

### Step 1: Configure Secrets (5 minutes)

```bash
cd k8s/production

# Copy template
cp secret-template.yaml secret.yaml

# Edit and replace all REPLACE_WITH_* values
nano secret.yaml

# Values needed:
# - CHATWORK_API_TOKEN (from Chatwork settings)
# - CHATWORK_WEBHOOK_SECRET (base64, from Chatwork webhook)
# - LARK_APP_ID (cli_xxxxx, from Lark Open Platform)
# - LARK_APP_SECRET (from Lark Open Platform)
# - LARK_VERIFICATION_TOKEN (from Lark Open Platform)
```

### Step 2: Configure Domain & Mappings (5 minutes)

```bash
# Update domain
nano ingress.yaml
# Replace: REPLACE_WITH_YOUR_DOMAIN.com → your-actual-domain.com

# Update room mappings
nano configmap.yaml
# Add your Chatwork room ID → Lark chat ID mappings
# Add your Chatwork user ID → Lark open ID mappings
```

### Step 3: Deploy (5-10 minutes)

```bash
# Deploy everything
./deploy-production.sh

# Follow on-screen prompts
# Script will:
# ✓ Create namespace
# ✓ Apply secrets
# ✓ Deploy Redis
# ✓ Deploy application (2 replicas)
# ✓ Create service
# ✓ Configure ingress with TLS
```

---

## Verification (5 minutes)

```bash
# 1. Check pods are running
kubectl get pods -n chatwork-lark
# Expected: 2 pods in Running state

# 2. Check health endpoint
curl https://your-domain.com/health/
# Expected: {"status":"healthy","redis":true}

# 3. View logs
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f
```

---

## Configure Webhooks (10 minutes)

### Chatwork
1. Open group chat → Settings → Webhook
2. Add webhook URL: `https://your-domain.com/webhook/chatwork/`
3. Select events: "Message created"
4. Save

### Lark
1. [Lark Open Platform](https://open.larksuite.com/) → Your App
2. Event Subscriptions → Request URL
3. Enter: `https://your-domain.com/webhook/lark/`
4. Click Verify (should show ✓)
5. Subscribe to: `im.message.receive_v1`
6. Save

---

## Test (5 minutes)

```bash
# Test 1: Send message in Chatwork
# → Should appear in Lark with prefix "[From Chatwork]"

# Test 2: Send message in Lark
# → Should appear in Chatwork with prefix "[From Lark]"

# Test 3: Monitor logs
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f
# Should see message processing logs
```

---

## Alternative: GitHub Actions Deployment

```bash
# 1. Configure GitHub Secrets (in repository settings):
KUBECONFIG=<base64 encoded kubeconfig>
CHATWORK_API_TOKEN=<token>
CHATWORK_WEBHOOK_SECRET=<secret>
LARK_APP_ID=<id>
LARK_APP_SECRET=<secret>
LARK_VERIFICATION_TOKEN=<token>
PRODUCTION_DOMAIN=your-domain.com

# 2. Go to Actions → "Deploy to Production" → Run workflow

# 3. Select: environment=production, type "deploy"

# Done! GitHub Actions will:
# - Run tests
# - Build Docker image
# - Deploy to Kubernetes
# - Verify deployment
```

---

## Alternative: Docker Compose (Local/Staging)

```bash
# 1. Configure .env
cp .env.example .env
nano .env  # Add credentials

# 2. Start
docker-compose up -d

# 3. Verify
curl http://localhost:8000/health/
open http://localhost:8000/docs

# 4. Stop
docker-compose down
```

---

## Troubleshooting

### Issue: Pods not starting
```bash
kubectl describe pod chatwork-lark-bridge-xxx -n chatwork-lark
kubectl logs chatwork-lark-bridge-xxx -n chatwork-lark
```

### Issue: Webhook not working
```bash
# Check ingress
kubectl get ingress -n chatwork-lark

# Test endpoint
curl -X POST https://your-domain.com/webhook/chatwork/ \
  -H "Content-Type: application/json" \
  -d '{"test":"data"}'
# Should return 403 or 422, NOT 404
```

### Issue: TLS certificate pending
```bash
# Wait 1-2 minutes, then check
kubectl get certificate -n chatwork-lark

# If still pending, check DNS
nslookup your-domain.com
# Should point to ingress IP
```

---

## What You Get

- **High Availability**: 2 replicas with zero-downtime updates
- **Security**: TLS/SSL, webhook verification, non-root containers
- **Monitoring**: Prometheus metrics, health checks
- **Scalability**: Horizontal Pod Autoscaler ready
- **Reliability**: Automatic restarts, rolling updates

---

## Support

- Full Guide: `PRODUCTION_DEPLOYMENT_GUIDE.md`
- Validation: `./validate-production-readiness.sh`
- API Docs: `https://your-domain.com/docs`
- Health: `https://your-domain.com/health/`

---

**Status**: Production Ready ✓

Generated with Claude Code
