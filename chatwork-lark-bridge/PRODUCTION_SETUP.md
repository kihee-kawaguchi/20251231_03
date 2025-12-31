# 本番環境セットアップガイド
# Production Environment Setup Guide

本番環境へのデプロイ前に必要な設定と手順を説明します。

---

## 📋 事前準備チェックリスト

### 必須項目

- [ ] **Chatwork アカウント準備**
  - [ ] API トークン取得済み
  - [ ] Webhook 設定完了
  - [ ] Webhook シークレット取得済み

- [ ] **Lark (Feishu) アプリ準備**
  - [ ] アプリ作成済み（企業自建応用）
  - [ ] App ID / App Secret 取得済み
  - [ ] Verification Token 取得済み
  - [ ] Event Subscription 設定済み
  - [ ] 必要な権限付与済み

- [ ] **インフラストラクチャ**
  - [ ] Kubernetes クラスタ準備完了
  - [ ] Redis インスタンス準備完了（または k8s 内）
  - [ ] ドメイン取得済み
  - [ ] DNS 設定可能
  - [ ] SSL/TLS 証明書取得可能

- [ ] **セキュリティ**
  - [ ] Secret 管理ツール選定（Sealed Secrets/Vault）
  - [ ] Network Policy 設計完了
  - [ ] RBAC 設計完了

---

## 🔐 Step 1: 認証情報の取得

### 1.1 Chatwork API トークン

1. Chatwork にログイン
2. 右上のアイコン → 「サービス連携」
3. 「API トークン」タブ
4. 「新しいトークンを発行」
5. トークンをコピーして安全に保存

**保存先:** `.env.production` または Secret 管理ツール

```bash
CHATWORK_API_TOKEN=your_actual_chatwork_api_token_here
```

### 1.2 Chatwork Webhook シークレット

1. Chatwork にログイン
2. 対象のグループチャットを開く
3. 右上の歯車アイコン → 「Webhook」
4. 「Webhook を追加」
5. Webhook URL: `https://your-domain.com/webhook/chatwork/`
6. シークレットキーをコピー（Base64エンコード済み）

**保存先:**

```bash
CHATWORK_WEBHOOK_SECRET=abcd1234efgh5678...  # Base64エンコード済み
```

### 1.3 Lark App 認証情報

#### App 作成

1. [Lark Open Platform](https://open.larksuite.com/) にアクセス
2. 「開発者バックエンド」→「アプリを作成」
3. 「企業自建応用」を選択
4. アプリ名・説明を入力

#### 認証情報取得

1. 作成したアプリを開く
2. 「認証情報」タブ
3. 以下をコピー:
   - App ID: `cli_xxxxxxxxxx`
   - App Secret: `xxxxxxxxxxxxxxxx`
   - Verification Token: `xxxxxxxxxxxxxxxx`

**保存先:**

```bash
LARK_APP_ID=cli_your_actual_app_id
LARK_APP_SECRET=your_actual_app_secret
LARK_VERIFICATION_TOKEN=your_actual_verification_token
```

#### 権限設定

「権限管理」タブで以下を有効化:

- [x] `im:message` - メッセージ送受信
- [x] `im:message:send_as_bot` - Bot としてメッセージ送信
- [x] `im:chat` - グループチャット情報取得

#### Event Subscription 設定

1. 「イベントとコールバック」タブ
2. 「イベント購読を有効化」
3. Request URL: `https://your-domain.com/webhook/lark/`
4. 購読するイベント:
   - `im.message.receive_v1` - メッセージ受信

---

## 🌐 Step 2: インフラストラクチャ準備

### 2.1 Kubernetes クラスタ

#### 推奨スペック

| リソース | 最小 | 推奨 | 備考 |
|---------|------|------|------|
| Nodes | 2 | 3+ | 高可用性のため |
| CPU/Node | 2 cores | 4 cores | - |
| Memory/Node | 4 GB | 8 GB | - |
| Storage | 20 GB | 50 GB | PVC用 |

#### クラスタ作成例（GKE）

```bash
gcloud container clusters create chatwork-lark-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-2 \
  --region=asia-northeast1 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=5
```

#### クラスタ作成例（EKS）

```bash
eksctl create cluster \
  --name=chatwork-lark-cluster \
  --region=ap-northeast-1 \
  --nodegroup-name=standard-workers \
  --node-type=t3.medium \
  --nodes=3 \
  --nodes-min=2 \
  --nodes-max=5
```

### 2.2 Ingress Controller

#### Nginx Ingress Controller のインストール

```bash
# Helm で nginx-ingress をインストール
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.service.type=LoadBalancer
```

#### Ingress IP の取得

```bash
kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller

# EXTERNAL-IP をメモ
# 例: 35.200.1.100
```

### 2.3 DNS 設定

取得した EXTERNAL-IP を使用してDNS Aレコードを設定:

```
A レコード:
chatwork-lark.your-domain.com → 35.200.1.100
```

**確認:**

```bash
nslookup chatwork-lark.your-domain.com
# 設定したIPが返ることを確認
```

### 2.4 TLS 証明書（Let's Encrypt）

#### Cert-Manager のインストール

```bash
# Cert-Manager をインストール
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# ClusterIssuer を作成
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

---

## 🔒 Step 3: Secret 管理

### Option A: Sealed Secrets（推奨）

#### Sealed Secrets のインストール

```bash
# Controller をインストール
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# CLI (kubeseal) をインストール
# macOS
brew install kubeseal

# Linux
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar xfz kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

#### Sealed Secret の作成

```bash
# 1. 通常の Secret YAML を作成
cat > secret-temp.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: chatwork-lark-secrets
  namespace: chatwork-lark
type: Opaque
stringData:
  chatwork-api-token: "YOUR_ACTUAL_TOKEN"
  chatwork-webhook-secret: "YOUR_BASE64_SECRET"
  lark-app-id: "cli_YOUR_APP_ID"
  lark-app-secret: "YOUR_APP_SECRET"
  lark-verification-token: "YOUR_VERIFICATION_TOKEN"
EOF

# 2. Sealed Secret に変換
kubeseal -f secret-temp.yaml -w k8s/sealed-secret.yaml

# 3. 元のファイルを削除
rm secret-temp.yaml

# 4. Sealed Secret を適用
kubectl apply -f k8s/sealed-secret.yaml
```

### Option B: HashiCorp Vault

#### Vault Agent Injector のインストール

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --namespace vault \
  --create-namespace \
  --set "injector.enabled=true"
```

#### Secret の保存

```bash
# Vault にログイン
kubectl exec -n vault vault-0 -- vault login

# Secret を保存
kubectl exec -n vault vault-0 -- vault kv put secret/chatwork-lark \
  chatwork-api-token="YOUR_TOKEN" \
  chatwork-webhook-secret="YOUR_SECRET" \
  lark-app-id="cli_YOUR_APP_ID" \
  lark-app-secret="YOUR_SECRET" \
  lark-verification-token="YOUR_TOKEN"
```

---

## 📝 Step 4: 設定ファイルの作成

### 4.1 Room Mappings (本番環境)

`config/room_mappings.prod.json` を作成:

```json
{
  "mappings": [
    {
      "chatwork_room_id": "実際のChatworkルームID",
      "lark_chat_id": "実際のLarkチャットID",
      "name": "General Discussion",
      "is_active": true,
      "sync_direction": "both",
      "description": "全社共通チャット"
    },
    {
      "chatwork_room_id": "別のルームID",
      "lark_chat_id": "別のチャットID",
      "name": "Engineering Team",
      "is_active": true,
      "sync_direction": "chatwork_to_lark",
      "description": "エンジニアリングチーム専用"
    }
  ]
}
```

#### Room ID の取得方法

**Chatwork:**
1. 対象のルームを開く
2. URL を確認: `https://www.chatwork.com/#!rid12345678`
3. `rid` の後の数字が Room ID

**Lark:**
1. グループチャットを開く
2. 右上の「...」→「グループ設定」
3. グループIDをコピー（`oc_xxxxxxxxxx` 形式）

### 4.2 User Mappings (本番環境)

`config/user_mappings.prod.json` を作成:

```json
{
  "mappings": [
    {
      "chatwork_user_id": "実際のChatwork User ID",
      "lark_user_id": "実際のLark Open ID",
      "display_name": "山田太郎",
      "email": "taro.yamada@example.com",
      "is_active": true
    }
  ]
}
```

#### User ID の取得方法

**Chatwork:**
1. ユーザーのプロフィールを開く
2. URL を確認: `https://www.chatwork.com/#!uid123456`
3. `uid` の後の数字が User ID

**Lark:**
```bash
# Lark API でユーザー情報を取得
curl -X GET "https://open.larksuite.com/open-apis/contact/v3/users?user_id_type=open_id" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🚀 Step 5: デプロイ実行

### 5.1 Production ConfigMap の作成

`k8s/configmap.prod.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chatwork-lark-config
  namespace: chatwork-lark
data:
  log_level: "INFO"  # 本番は INFO
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
  namespace: chatwork-lark
data:
  room_mappings.json: |
    # ここに config/room_mappings.prod.json の内容をコピー

  user_mappings.json: |
    # ここに config/user_mappings.prod.json の内容をコピー
```

### 5.2 Production Ingress の作成

`k8s/ingress.prod.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: chatwork-lark-ingress
  namespace: chatwork-lark
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - chatwork-lark.your-actual-domain.com  # 実際のドメインに変更
      secretName: chatwork-lark-tls
  rules:
    - host: chatwork-lark.your-actual-domain.com  # 実際のドメインに変更
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
```

### 5.3 デプロイコマンド

```bash
# 1. Namespace 作成
kubectl apply -f k8s/namespace.yaml

# 2. Secrets 適用（Sealed Secrets の場合）
kubectl apply -f k8s/sealed-secret.yaml

# 3. ConfigMap 適用
kubectl apply -f k8s/configmap.prod.yaml

# 4. Redis デプロイ
kubectl apply -f k8s/redis-deployment.yaml

# Redis の起動を待つ
kubectl wait --for=condition=ready pod -l app=redis -n chatwork-lark --timeout=60s

# 5. アプリケーション デプロイ
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 6. Ingress 適用
kubectl apply -f k8s/ingress.prod.yaml

# 7. デプロイ状態確認
kubectl get pods -n chatwork-lark
kubectl get svc -n chatwork-lark
kubectl get ingress -n chatwork-lark
```

---

## ✅ Step 6: 動作確認

### 6.1 ヘルスチェック

```bash
# DNS解決確認
nslookup chatwork-lark.your-domain.com

# HTTPS接続確認
curl https://chatwork-lark.your-domain.com/health/

# 期待されるレスポンス:
# {"status":"healthy","redis":true,"details":{"redis":"connected"}}
```

### 6.2 Webhook 設定確認

#### Chatwork

1. Chatworkのグループチャットで「Webhook」設定を開く
2. Webhook URLが正しいか確認:
   ```
   https://chatwork-lark.your-domain.com/webhook/chatwork/
   ```
3. テストメッセージを送信
4. Larkで受信されることを確認

#### Lark

1. Lark Open Platform でアプリを開く
2. 「イベントとコールバック」設定を確認:
   ```
   https://chatwork-lark.your-domain.com/webhook/lark/
   ```
3. テストメッセージを送信
4. Chatworkで受信されることを確認

### 6.3 ログ確認

```bash
# アプリケーションログ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# 特定のPod
kubectl logs -n chatwork-lark chatwork-lark-bridge-xxx-yyy

# エラーログのみ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge | grep ERROR
```

---

## 📊 Step 7: モニタリング設定

### 7.1 Prometheus + Grafana

```bash
# Prometheus Operator インストール
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Grafana ダッシュボードにアクセス
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# http://localhost:3000
# デフォルト: admin / prom-operator
```

### 7.2 アラート設定例

`k8s/prometheus-rule.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: chatwork-lark-alerts
  namespace: chatwork-lark
spec:
  groups:
    - name: chatwork-lark
      interval: 30s
      rules:
        - alert: PodDown
          expr: up{job="chatwork-lark-bridge"} == 0
          for: 5m
          annotations:
            summary: "Pod is down"

        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
          for: 10m
          annotations:
            summary: "High error rate detected"
```

---

## 🔒 セキュリティチェックリスト

- [ ] **認証情報**
  - [ ] Secret は暗号化して保存（Sealed Secrets/Vault）
  - [ ] .env ファイルは .gitignore に含まれている
  - [ ] 定期的なローテーション計画がある

- [ ] **ネットワーク**
  - [ ] Network Policy 適用済み
  - [ ] Ingress でレート制限設定済み
  - [ ] TLS 1.2+ のみ許可

- [ ] **Pod Security**
  - [ ] 非rootユーザーで実行
  - [ ] Read-only filesystem
  - [ ] SecurityContext 設定済み

- [ ] **監視**
  - [ ] ログ集約設定済み
  - [ ] メトリクス収集設定済み
  - [ ] アラート設定済み

---

## 📋 本番環境チェックリスト

### デプロイ前

- [ ] すべての認証情報を取得済み
- [ ] DNS設定完了
- [ ] TLS証明書取得設定完了
- [ ] ConfigMap に本番マッピング設定済み
- [ ] Sealed Secrets 作成済み
- [ ] Ingress のドメイン名を本番用に変更済み

### デプロイ後

- [ ] すべての Pod が Running
- [ ] ヘルスチェックが正常
- [ ] Webhook URLが正しく設定されている
- [ ] テストメッセージが正常に同期される
- [ ] ログが正常に出力されている
- [ ] メトリクスが収集されている

### 運用開始後

- [ ] 監視ダッシュボード確認
- [ ] アラート通知先設定済み
- [ ] バックアップ設定済み
- [ ] インシデント対応手順文書化済み
- [ ] エスカレーションパス確立済み

---

**次のステップ:**
1. このガイドに従って本番環境を構築
2. ステージング環境で事前テスト
3. 本番デプロイ実施
4. 運用監視開始

**問い合わせ:**
問題が発生した場合は DEPLOYMENT.md のトラブルシューティングセクションを参照してください。
