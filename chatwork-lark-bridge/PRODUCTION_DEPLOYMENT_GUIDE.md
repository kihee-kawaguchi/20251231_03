# Production Deployment Guide

**Status**: Ready for Production Deployment
**Last Updated**: 2026-01-01

---

## Quick Start (3 Options)

### Option 1: Automated GitHub Actions Deployment (Recommended)

```bash
# 1. Configure GitHub Secrets
# Go to: Settings → Secrets and variables → Actions → New repository secret

# Required secrets:
KUBECONFIG=<base64 encoded kubeconfig file>
CHATWORK_API_TOKEN=<your token>
CHATWORK_WEBHOOK_SECRET=<base64 encoded secret>
LARK_APP_ID=cli_xxxxx
LARK_APP_SECRET=<your secret>
LARK_VERIFICATION_TOKEN=<your token>
PRODUCTION_DOMAIN=your-domain.com

# 2. Trigger deployment
# Go to: Actions → Deploy to Production → Run workflow
# Select: environment=production
# Type: "deploy" to confirm
```

### Option 2: Manual Kubernetes Deployment

```bash
# 1. Validate readiness
./validate-production-readiness.sh

# 2. Configure production files
cd k8s/production
cp secret-template.yaml secret.yaml
nano secret.yaml  # Add real credentials
nano configmap.yaml  # Update mappings
nano ingress.yaml  # Update domain

# 3. Deploy
./deploy-production.sh
```

### Option 3: Docker Compose (Development/Staging)

```bash
# 1. Update .env file
cp .env.example .env
nano .env  # Add real credentials

# 2. Start services
docker-compose up -d

# 3. Verify
docker-compose logs -f app
curl http://localhost:8000/health/
```

---

## Prerequisites Checklist

### Infrastructure Requirements

- [ ] Kubernetes cluster (v1.28+) with kubectl access
- [ ] nginx-ingress-controller installed
- [ ] cert-manager installed (for TLS certificates)
- [ ] Container registry access (Docker Hub or GitHub Container Registry)
- [ ] Domain name with DNS access

### Required Credentials

- [ ] Chatwork API Token
- [ ] Chatwork Webhook Secret (base64 encoded)
- [ ] Lark App ID
- [ ] Lark App Secret
- [ ] Lark Verification Token

### Configuration Files

- [ ] `k8s/production/secret.yaml` (from template)
- [ ] `k8s/production/configmap.yaml` (room/user mappings)
- [ ] `k8s/production/ingress.yaml` (domain configured)

---

## Deployment Steps (Detailed)

### Step 1: Prepare Kubernetes Cluster

```bash
# Verify cluster access
kubectl cluster-info
kubectl get nodes

# Install nginx-ingress (if not installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager (if not installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# Verify installations
kubectl get pods -n ingress-nginx
kubectl get pods -n cert-manager
```

### Step 2: Configure Secrets

```bash
cd k8s/production

# Option A: Plain Secret (Quick setup, NOT recommended for production)
cp secret-template.yaml secret.yaml
nano secret.yaml  # Replace all REPLACE_WITH_* values

# Option B: Sealed Secrets (Recommended for production)
cp secret-template.yaml secret.yaml
nano secret.yaml  # Replace all values
kubeseal -f secret.yaml -w sealed-secret.yaml
rm secret.yaml  # Remove unencrypted file
```

**Required values:**
- `chatwork-api-token`: Get from Chatwork → Settings → API Token
- `chatwork-webhook-secret`: Base64 encoded webhook secret
- `lark-app-id`: From Lark Open Platform → Your App → Credentials
- `lark-app-secret`: From Lark Open Platform → Your App → Credentials
- `lark-verification-token`: From Lark Open Platform → Your App → Event Subscriptions

### Step 3: Configure Room/User Mappings

```bash
nano configmap.yaml
```

Update the `room_mappings.json` section:

```json
{
  "12345678": "oc_lark_chat_id_1",
  "87654321": "oc_lark_chat_id_2"
}
```

Update the `user_mappings.json` section:

```json
{
  "111222": "ou_lark_user_id_1",
  "333444": "ou_lark_user_id_2"
}
```

### Step 4: Configure Domain

```bash
nano ingress.yaml
```

Replace `REPLACE_WITH_YOUR_DOMAIN.com` with your actual domain (e.g., `chatwork-bridge.example.com`).

**Important**: Ensure DNS A record points to your ingress controller's external IP:

```bash
# Get ingress controller external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Create DNS A record
# your-domain.com → <EXTERNAL-IP>
```

### Step 5: Build and Push Docker Image

```bash
# Option A: Using Docker Hub
docker build -t your-dockerhub-username/chatwork-lark-bridge:latest .
docker push your-dockerhub-username/chatwork-lark-bridge:latest

# Option B: Using GitHub Container Registry
docker build -t ghcr.io/your-github-username/chatwork-lark-bridge:latest .
echo $GITHUB_TOKEN | docker login ghcr.io -u your-github-username --password-stdin
docker push ghcr.io/your-github-username/chatwork-lark-bridge:latest

# Option C: Using GitHub Actions (automatic)
# Push to main branch → .github/workflows/deploy-production.yml builds and pushes
```

Update image in `deployment.yaml`:

```bash
nano deployment.yaml
# Change: image: chatwork-lark-bridge:latest
# To: image: your-registry/chatwork-lark-bridge:latest
```

### Step 6: Deploy to Kubernetes

```bash
# Run automated deployment script
./deploy-production.sh

# Or manually apply manifests
kubectl apply -f ../../k8s/namespace.yaml
kubectl apply -f secret.yaml  # or sealed-secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f ../../k8s/redis-deployment.yaml
kubectl wait --for=condition=ready pod -l app=redis -n chatwork-lark --timeout=120s
kubectl apply -f deployment.yaml
kubectl apply -f ../../k8s/service.yaml
kubectl apply -f ingress.yaml
```

### Step 7: Verify Deployment

```bash
# Check all resources
kubectl get all -n chatwork-lark

# Check pods (should see 2 replicas running)
kubectl get pods -n chatwork-lark
# Expected: chatwork-lark-bridge-xxx-xxx   1/1   Running

# Check deployment
kubectl describe deployment chatwork-lark-bridge -n chatwork-lark

# Check logs
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# Check ingress
kubectl get ingress -n chatwork-lark
# Expected: ADDRESS column shows external IP

# Check TLS certificate (may take 1-2 minutes)
kubectl get certificate -n chatwork-lark
# Expected: READY = True
```

### Step 8: Test Endpoints

```bash
# Health check
curl https://your-domain.com/health/
# Expected: {"status":"healthy","redis":true,...}

# Liveness probe
curl https://your-domain.com/health/live
# Expected: {"status":"ok"}

# Readiness probe
curl https://your-domain.com/health/ready
# Expected: {"status":"ready","redis":true}

# API documentation
open https://your-domain.com/docs
# Should show Swagger UI
```

### Step 9: Configure Webhooks

#### Chatwork Webhook Setup

1. Open your Chatwork group chat
2. Click settings (gear icon) → "Webhook"
3. Click "Add Webhook"
4. Enter:
   - **Webhook URL**: `https://your-domain.com/webhook/chatwork/`
   - **Events**: Select "Message created"
5. Save webhook
6. Copy the **Webhook Token** (if you need to update secret)

#### Lark Event Subscription Setup

1. Go to [Lark Open Platform](https://open.larksuite.com/)
2. Open your app
3. Navigate to "Event Subscriptions" or "Events & Callbacks"
4. Enter:
   - **Request URL**: `https://your-domain.com/webhook/lark/`
5. Click "Verify"
   - Should show green checkmark if successful
   - If failed, check pod logs: `kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge`
6. Subscribe to events:
   - `im.message.receive_v1` (Message received)
7. Save configuration

### Step 10: End-to-End Testing

```bash
# Test 1: Chatwork → Lark
# 1. Send a message in Chatwork chat
# 2. Verify it appears in Lark chat with prefix "[From Chatwork]"

# Test 2: Lark → Chatwork
# 1. Send a message in Lark chat
# 2. Verify it appears in Chatwork chat with prefix "[From Lark]"

# Test 3: Loop Detection
# 1. Message from Chatwork should sync to Lark
# 2. That synced message (with prefix) should NOT sync back to Chatwork

# Monitor logs during testing
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f
```

---

## Monitoring & Maintenance

### View Logs

```bash
# Real-time logs from all pods
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# Logs from specific pod
kubectl logs -n chatwork-lark chatwork-lark-bridge-xxx-xxx

# Error logs only
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge | grep ERROR

# Last 100 lines
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge --tail=100
```

### Check Resource Usage

```bash
# CPU and memory usage
kubectl top pods -n chatwork-lark

# Node resource usage
kubectl top nodes

# Detailed resource info
kubectl describe deployment chatwork-lark-bridge -n chatwork-lark
```

### Check Events

```bash
# Recent events in namespace
kubectl get events -n chatwork-lark --sort-by='.lastTimestamp'

# Events for specific pod
kubectl describe pod chatwork-lark-bridge-xxx-xxx -n chatwork-lark
```

### Prometheus Metrics

```bash
# Port forward to access metrics endpoint
kubectl port-forward -n chatwork-lark svc/chatwork-lark-service 8000:80

# In another terminal, fetch metrics
curl http://localhost:8000/metrics
```

### Update Deployment

```bash
# Update image version
kubectl set image deployment/chatwork-lark-bridge \
  app=your-registry/chatwork-lark-bridge:v1.1.0 \
  -n chatwork-lark

# Watch rollout
kubectl rollout status deployment/chatwork-lark-bridge -n chatwork-lark

# Verify new version
kubectl get pods -n chatwork-lark
```

### Update ConfigMap (Room Mappings)

```bash
# Edit ConfigMap
nano k8s/production/configmap.yaml

# Apply changes
kubectl apply -f k8s/production/configmap.yaml

# Restart pods to pick up changes
kubectl rollout restart deployment/chatwork-lark-bridge -n chatwork-lark
```

### Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/chatwork-lark-bridge -n chatwork-lark

# Check rollout history
kubectl rollout history deployment/chatwork-lark-bridge -n chatwork-lark

# Rollback to specific revision
kubectl rollout undo deployment/chatwork-lark-bridge -n chatwork-lark --to-revision=2
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n chatwork-lark

# Describe pod for events
kubectl describe pod chatwork-lark-bridge-xxx-xxx -n chatwork-lark

# Common issues:
# - ImagePullBackOff: Image not found or no pull access
# - CrashLoopBackOff: Application crashing on startup
# - Pending: Insufficient resources or node selector issues

# Check logs
kubectl logs -n chatwork-lark chatwork-lark-bridge-xxx-xxx
```

### Webhook Not Receiving Requests

```bash
# Check ingress
kubectl describe ingress chatwork-lark-ingress -n chatwork-lark

# Verify ingress controller
kubectl get svc -n ingress-nginx

# Check DNS resolution
nslookup your-domain.com

# Test webhook endpoint
curl -X POST https://your-domain.com/webhook/chatwork/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Should return 403 (signature verification) or 422 (invalid payload)
# NOT 404 or connection refused
```

### TLS Certificate Issues

```bash
# Check certificate status
kubectl get certificate -n chatwork-lark

# Describe certificate for details
kubectl describe certificate chatwork-lark-tls -n chatwork-lark

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check challenges
kubectl get challenge -n chatwork-lark

# Common issues:
# - DNS not configured
# - Domain not pointing to ingress IP
# - Rate limit from Let's Encrypt (5 certs/week/domain)
```

### Redis Connection Issues

```bash
# Check Redis pod
kubectl get pods -n chatwork-lark -l app=redis

# Test Redis connection
kubectl exec -it -n chatwork-lark deployment/chatwork-lark-bridge -- \
  python -c "import redis; r=redis.from_url('redis://redis-service:6379/0'); print(r.ping())"

# Check Redis logs
kubectl logs -n chatwork-lark -l app=redis
```

### High Memory/CPU Usage

```bash
# Check resource usage
kubectl top pods -n chatwork-lark

# Increase resource limits
nano k8s/production/deployment.yaml
# Update resources.limits.memory and resources.limits.cpu

# Apply changes
kubectl apply -f k8s/production/deployment.yaml

# Or scale up replicas
kubectl scale deployment chatwork-lark-bridge --replicas=3 -n chatwork-lark
```

---

## Security Best Practices

### 1. Secrets Management

- ✓ Use Sealed Secrets for production
- ✓ Never commit plain secrets to Git
- ✓ Rotate secrets regularly (every 90 days)
- ✓ Use separate secrets for staging/production

### 2. Network Security

- ✓ Enable TLS/SSL (Let's Encrypt via cert-manager)
- ✓ Use network policies to restrict pod communication
- ✓ Configure ingress rate limiting
- ✓ Enable CORS appropriately

### 3. Pod Security

- ✓ Run as non-root user (UID 1000)
- ✓ Read-only root filesystem
- ✓ Drop all capabilities
- ✓ Use security context

### 4. Monitoring & Alerts

- ✓ Set up Prometheus/Grafana
- ✓ Configure alerts for pod failures
- ✓ Monitor error rates
- ✓ Track webhook processing times

---

## Scaling

### Horizontal Scaling (More Replicas)

```bash
# Scale to 3 replicas
kubectl scale deployment chatwork-lark-bridge --replicas=3 -n chatwork-lark

# Or update deployment.yaml
nano k8s/production/deployment.yaml
# Change: replicas: 2 → replicas: 3

kubectl apply -f k8s/production/deployment.yaml
```

### Vertical Scaling (More Resources)

```bash
# Update resource limits
nano k8s/production/deployment.yaml

# Change:
resources:
  requests:
    cpu: 500m  # was 250m
    memory: 512Mi  # was 256Mi
  limits:
    cpu: 2000m  # was 1000m
    memory: 1Gi  # was 512Mi

kubectl apply -f k8s/production/deployment.yaml
```

### Autoscaling (HPA)

```bash
# Create Horizontal Pod Autoscaler
kubectl autoscale deployment chatwork-lark-bridge \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n chatwork-lark

# Check HPA status
kubectl get hpa -n chatwork-lark
```

---

## Backup & Disaster Recovery

### Backup ConfigMap and Secrets

```bash
# Backup all resources
kubectl get all,configmap,secret -n chatwork-lark -o yaml > backup-$(date +%Y%m%d).yaml

# Backup specific resources
kubectl get configmap chatwork-lark-config -n chatwork-lark -o yaml > configmap-backup.yaml
kubectl get secret chatwork-lark-secrets -n chatwork-lark -o yaml > secret-backup.yaml
```

### Redis Data Backup

```bash
# Backup Redis data
kubectl exec -n chatwork-lark deployment/redis -- redis-cli SAVE
kubectl cp chatwork-lark/redis-deployment-xxx:/data/dump.rdb ./redis-backup.rdb
```

### Restore from Backup

```bash
# Restore resources
kubectl apply -f backup-20260101.yaml

# Restore Redis data
kubectl cp ./redis-backup.rdb chatwork-lark/redis-deployment-xxx:/data/dump.rdb
kubectl exec -n chatwork-lark deployment/redis -- redis-cli SHUTDOWN
# Redis will restart with backed up data
```

---

## Performance Tuning

### Redis Optimization

```yaml
# In k8s/redis-deployment.yaml
command:
  - redis-server
  - --appendonly yes
  - --maxmemory 512mb
  - --maxmemory-policy allkeys-lru
```

### Application Tuning

```yaml
# In k8s/production/configmap.yaml
data:
  max_retry_attempts: "5"
  initial_retry_delay: "1.0"
  max_retry_delay: "60.0"
  message_ttl_seconds: "86400"  # 24 hours
```

---

## Cost Optimization

### Resource Requests vs Limits

- Set requests to average usage
- Set limits to peak usage (150-200% of requests)
- Monitor actual usage with `kubectl top pods`

### Replica Count

- Start with 2 replicas (high availability)
- Scale based on traffic patterns
- Use HPA for automatic scaling

### Storage

- Use appropriate storage classes
- Set retention policies for logs
- Clean up old Redis keys automatically

---

## Next Steps After Deployment

1. **Monitor for 24 hours**
   - Check logs for errors
   - Verify message synchronization working
   - Monitor resource usage

2. **Set up alerts**
   - Pod failures
   - High error rates
   - Resource exhaustion
   - Certificate expiration

3. **Document runbook**
   - On-call procedures
   - Escalation paths
   - Common issues and fixes

4. **Performance baseline**
   - Message latency
   - API response times
   - Resource utilization

5. **Regular maintenance**
   - Update dependencies monthly
   - Rotate secrets quarterly
   - Review and update documentation

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Logs**: `kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge`
- **Health**: `https://your-domain.com/health/`
- **API Docs**: `https://your-domain.com/docs`

---

**Status**: Production Ready ✓
**Deployment Time**: ~30-60 minutes
**Difficulty**: Intermediate

Generated with Claude Code
