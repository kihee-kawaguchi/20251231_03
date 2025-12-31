# デプロイメントガイド
# Deployment Guide

Chatwork-Lark Bridge のデプロイ方法を説明します。

---

## 📋 目次

- [前提条件](#前提条件)
- [Docker Compose でのデプロイ](#docker-compose-でのデプロイ)
- [Kubernetes でのデプロイ](#kubernetes-でのデプロイ)
- [設定ファイル](#設定ファイル)
- [監視とログ](#監視とログ)
- [トラブルシューティング](#トラブルシューティング)

---

## 🔧 前提条件

### Docker Compose の場合

- Docker Engine 20.10+
- Docker Compose 2.0+
- 空きポート: 8000, 6379

### Kubernetes の場合

- Kubernetes クラスタ 1.24+
- kubectl CLI
- Helm 3.0+ (オプション)
- Ingress Controller (nginx-ingress推奨)
- Cert-Manager (TLS証明書用、オプション)

---

## 🐳 Docker Compose でのデプロイ

### 1. 環境変数の設定

```bash
# .env.example をコピー
cp .env.example .env

# エディタで .env を編集
nano .env
```

**必須の環境変数:**

```bash
CHATWORK_API_TOKEN=your_actual_token
CHATWORK_WEBHOOK_SECRET=your_base64_secret
LARK_APP_ID=cli_your_app_id
LARK_APP_SECRET=your_app_secret
LARK_VERIFICATION_TOKEN=your_verification_token
```

### 2. 設定ファイルの準備

```bash
# config ディレクトリを作成
mkdir -p config

# ルーム・ユーザーマッピングファイルを配置
# 例: config/room_mappings.json
# 例: config/user_mappings.json
```

### 3. ビルドと起動

```bash
# イメージをビルド
docker-compose build

# バックグラウンドで起動
docker-compose up -d

# ログを確認
docker-compose logs -f app
```

### 4. 動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/health/

# レスポンス例:
# {"status":"healthy","redis":true,"details":{"redis":"connected"}}
```

### 5. 停止と削除

```bash
# 停止
docker-compose down

# データも含めて削除
docker-compose down -v
```

---

## ☸️ Kubernetes でのデプロイ

### 1. Namespace の作成

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Secrets の設定

**重要:** `k8s/secret.yaml` の値を実際の認証情報に置き換えてください。

```bash
# テンプレートをコピー
cp k8s/secret.yaml k8s/secret-prod.yaml

# 実際の値に編集
nano k8s/secret-prod.yaml

# 適用（本番環境では SealedSecrets などを使用）
kubectl apply -f k8s/secret-prod.yaml
```

**推奨:** 本番環境では以下のシークレット管理ツールを使用:

- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [External Secrets Operator](https://external-secrets.io/)
- [HashiCorp Vault](https://www.vaultproject.io/)

### 3. ConfigMap の設定

ルーム・ユーザーマッピングを `k8s/configmap.yaml` に設定:

```bash
# ConfigMap を編集
nano k8s/configmap.yaml

# 適用
kubectl apply -f k8s/configmap.yaml
```

### 4. Redis のデプロイ

```bash
kubectl apply -f k8s/redis-deployment.yaml
```

### 5. アプリケーションのデプロイ

```bash
# Docker イメージをビルド
docker build -t chatwork-lark-bridge:latest .

# イメージをレジストリにプッシュ（例: Docker Hub）
docker tag chatwork-lark-bridge:latest yourregistry/chatwork-lark-bridge:v1.0.0
docker push yourregistry/chatwork-lark-bridge:v1.0.0

# Deployment を適用
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 6. Ingress の設定

**ドメイン設定:**

`k8s/ingress.yaml` でドメインを変更:

```yaml
spec:
  tls:
    - hosts:
        - your-domain.com  # ← ここを変更
```

**適用:**

```bash
kubectl apply -f k8s/ingress.yaml
```

### 7. Kustomize を使用したデプロイ（推奨）

```bash
# プレビュー
kubectl kustomize k8s/

# 適用
kubectl apply -k k8s/
```

### 8. デプロイの確認

```bash
# Pod の状態確認
kubectl get pods -n chatwork-lark

# ログ確認
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# Service 確認
kubectl get svc -n chatwork-lark

# Ingress 確認
kubectl get ingress -n chatwork-lark
```

---

## 📝 設定ファイル

### Room Mappings (config/room_mappings.json)

```json
{
  "mappings": [
    {
      "chatwork_room_id": "12345678",
      "lark_chat_id": "oc_a1b2c3d4e5f6",
      "name": "General Discussion",
      "is_active": true,
      "sync_direction": "both"
    },
    {
      "chatwork_room_id": "87654321",
      "lark_chat_id": "oc_g7h8i9j0k1l2",
      "name": "Engineering Team",
      "is_active": true,
      "sync_direction": "chatwork_to_lark"
    }
  ]
}
```

**sync_direction の値:**
- `both`: 双方向同期
- `chatwork_to_lark`: Chatwork → Lark のみ
- `lark_to_chatwork`: Lark → Chatwork のみ

### User Mappings (config/user_mappings.json)

```json
{
  "mappings": [
    {
      "chatwork_user_id": "111",
      "lark_user_id": "ou_test123",
      "display_name": "Taro Yamada",
      "is_active": true
    },
    {
      "chatwork_user_id": "222",
      "lark_user_id": "ou_test456",
      "display_name": "Hanako Tanaka",
      "is_active": true
    }
  ]
}
```

---

## 📊 監視とログ

### Docker Compose

**ログ確認:**

```bash
# リアルタイムログ
docker-compose logs -f app

# エラーログのみ
docker-compose logs app | grep ERROR

# Redis のログ
docker-compose logs redis
```

**メトリクス:**

```bash
# コンテナの状態
docker-compose ps

# リソース使用状況
docker stats chatwork-lark-bridge
```

### Kubernetes

**ログ確認:**

```bash
# Pod のログ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# 特定の Pod
kubectl logs -n chatwork-lark chatwork-lark-bridge-xxx-yyy

# 過去1時間のログ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge --since=1h
```

**メトリクス:**

```bash
# Pod のリソース使用状況
kubectl top pods -n chatwork-lark

# Node のリソース
kubectl top nodes
```

**Prometheus + Grafana（推奨）:**

1. Prometheus Operator をインストール
2. ServiceMonitor を作成
3. Grafana ダッシュボードをインポート

---

## 🔍 トラブルシューティング

### 問題: アプリケーションが起動しない

**確認ポイント:**

```bash
# Docker Compose
docker-compose logs app

# Kubernetes
kubectl describe pod -n chatwork-lark chatwork-lark-bridge-xxx
kubectl logs -n chatwork-lark chatwork-lark-bridge-xxx
```

**よくある原因:**

1. 環境変数の設定ミス → `.env` または Secret を確認
2. Redis に接続できない → Redis の起動状態を確認
3. ポートが使用中 → `docker-compose down` で停止

### 問題: Webhook が受信されない

**確認:**

1. Ingress の設定を確認
   ```bash
   kubectl get ingress -n chatwork-lark
   kubectl describe ingress chatwork-lark-ingress -n chatwork-lark
   ```

2. Service のエンドポイント確認
   ```bash
   kubectl get endpoints -n chatwork-lark
   ```

3. Webhook URL の設定を確認
   - Chatwork: `https://your-domain.com/webhook/chatwork/`
   - Lark: `https://your-domain.com/webhook/lark/`

### 問題: メッセージが同期されない

**デバッグ手順:**

1. ログで処理を確認
   ```bash
   kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge | grep "processing"
   ```

2. ルームマッピングを確認
   ```bash
   kubectl get configmap chatwork-lark-mappings -n chatwork-lark -o yaml
   ```

3. Redis のデータを確認
   ```bash
   # Docker Compose
   docker-compose exec redis redis-cli

   # Kubernetes
   kubectl exec -n chatwork-lark redis-xxx -- redis-cli

   # コマンド例
   KEYS room:*
   GET room:chatwork:12345678
   ```

### 問題: 高負荷時のパフォーマンス

**対策:**

1. **Kubernetes のレプリカ数を増やす**
   ```bash
   kubectl scale deployment chatwork-lark-bridge -n chatwork-lark --replicas=5
   ```

2. **リソース制限を調整**
   ```yaml
   resources:
     requests:
       cpu: 500m
       memory: 512Mi
     limits:
       cpu: 1000m
       memory: 1Gi
   ```

3. **Horizontal Pod Autoscaler (HPA) を設定**
   ```bash
   kubectl autoscale deployment chatwork-lark-bridge \
     -n chatwork-lark \
     --cpu-percent=70 \
     --min=2 \
     --max=10
   ```

---

## 🔐 セキュリティ

### 推奨事項

1. **Secrets の管理**
   - Git にコミットしない
   - SealedSecrets または Vault を使用

2. **Network Policy**
   ```bash
   kubectl apply -f k8s/network-policy.yaml
   ```

3. **TLS 証明書**
   - Let's Encrypt + Cert-Manager を使用
   - 自動更新を有効化

4. **RBAC**
   - 最小権限の原則
   - ServiceAccount の適切な設定

5. **イメージスキャン**
   ```bash
   # Trivy でスキャン
   trivy image chatwork-lark-bridge:latest
   ```

---

## 🚀 本番環境チェックリスト

- [ ] 環境変数・Secrets が正しく設定されている
- [ ] ルーム・ユーザーマッピングが最新
- [ ] TLS 証明書が有効
- [ ] Ingress の DNS 設定が完了
- [ ] ログ収集が設定されている
- [ ] メトリクス監視が設定されている
- [ ] アラート設定が完了
- [ ] バックアップ戦略が確立
- [ ] ディザスタリカバリ計画が策定
- [ ] セキュリティスキャンが実施済み

---

**作成者:** Claude Sonnet 4.5
**最終更新:** 2025-12-31
