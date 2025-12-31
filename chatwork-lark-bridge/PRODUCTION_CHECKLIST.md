# 本番環境デプロイチェックリスト
# Production Deployment Checklist

デプロイ前に必ず確認してください。

---

## 📋 デプロイ前チェックリスト

### 1. 認証情報の準備 ✅

- [ ] **Chatwork**
  - [ ] API トークンを取得済み
  - [ ] Webhook シークレットを取得済み（Base64エンコード）
  - [ ] 対象ルームでWebhook設定を作成済み

- [ ] **Lark**
  - [ ] アプリを作成済み（企業自建応用）
  - [ ] App ID を取得済み
  - [ ] App Secret を取得済み
  - [ ] Verification Token を取得済み
  - [ ] 必要な権限を付与済み (`im:message`, `im:message:send_as_bot`, `im:chat`)
  - [ ] Event Subscription を有効化済み

### 2. インフラストラクチャ ✅

- [ ] **Kubernetes クラスタ**
  - [ ] クラスタが準備済み（最小: 2ノード、推奨: 3+ノード）
  - [ ] kubectl でクラスタに接続可能
  - [ ] 十分なリソースがある（CPU: 4cores+, Memory: 8GB+）

- [ ] **Ingress Controller**
  - [ ] nginx-ingress がインストール済み
  - [ ] LoadBalancer が作成され、EXTERNAL-IP が割り当て済み

- [ ] **DNS**
  - [ ] ドメインを取得済み
  - [ ] DNS Aレコードを設定済み（Ingress IPを指定）
  - [ ] DNS伝播を確認済み（`nslookup`で確認）

- [ ] **TLS証明書**
  - [ ] cert-manager がインストール済み（Let's Encrypt使用の場合）
  - [ ] ClusterIssuer が作成済み
  - [ ] メールアドレスを設定済み

### 3. Secret 管理 ✅

- [ ] **Secret 暗号化**
  - [ ] Sealed Secrets または Vault をインストール済み
  - [ ] Secret を暗号化済み
  - [ ] 平文のSecretファイルを削除済み

- [ ] **セキュリティ**
  - [ ] `.env` ファイルが `.gitignore` に含まれている
  - [ ] Secret ファイルが Git にコミットされていない
  - [ ] Secret のローテーション計画がある

### 4. 設定ファイル ✅

- [ ] **Room Mappings**
  - [ ] `config/room_mappings.prod.json` を作成済み
  - [ ] すべての同期対象ルームを設定済み
  - [ ] Chatwork Room ID が正しい
  - [ ] Lark Chat ID が正しい
  - [ ] `sync_direction` が適切に設定されている

- [ ] **User Mappings**
  - [ ] `config/user_mappings.prod.json` を作成済み
  - [ ] すべてのユーザーマッピングを設定済み
  - [ ] ユーザーIDが正しい

- [ ] **ConfigMap**
  - [ ] `k8s/production/configmap.yaml` を確認済み
  - [ ] Room/User mappings を ConfigMap に反映済み
  - [ ] ログレベルを `INFO` に設定済み

### 5. デプロイ設定 ✅

- [ ] **Deployment**
  - [ ] レプリカ数を設定済み（推奨: 2以上）
  - [ ] リソース制限を確認済み
  - [ ] イメージタグが正しい

- [ ] **Ingress**
  - [ ] ドメイン名が正しく設定されている
  - [ ] TLS設定が有効
  - [ ] Rate Limit が設定されている

- [ ] **Service**
  - [ ] Service タイプが ClusterIP
  - [ ] ポート設定が正しい

---

## 🚀 デプロイ手順

### 方法1: セットアップウィザード（推奨）

```bash
./setup-production.sh
```

対話形式で設定を入力し、自動で設定ファイルを生成します。

### 方法2: 手動デプロイ

```bash
# 1. Namespace 作成
kubectl apply -f k8s/namespace.yaml

# 2. Secrets 適用
kubectl apply -f k8s/production/sealed-secret.yaml

# 3. ConfigMap 適用
kubectl apply -f k8s/production/configmap.yaml

# 4. Redis デプロイ
kubectl apply -f k8s/redis-deployment.yaml
kubectl wait --for=condition=ready pod -l app=redis -n chatwork-lark --timeout=60s

# 5. アプリケーション デプロイ
kubectl apply -f k8s/production/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl wait --for=condition=available deployment/chatwork-lark-bridge -n chatwork-lark --timeout=120s

# 6. Ingress 適用
kubectl apply -f k8s/production/ingress.yaml
```

### 方法3: 自動デプロイスクリプト

```bash
cd k8s/production
./deploy-production.sh
```

---

## ✅ デプロイ後確認

### 1. Pod の状態確認

```bash
kubectl get pods -n chatwork-lark

# すべてのPodが Running かつ READY 1/1 であることを確認
# 例:
# NAME                                    READY   STATUS    RESTARTS   AGE
# chatwork-lark-bridge-xxxxxxxxxx-xxxxx   1/1     Running   0          2m
# chatwork-lark-bridge-xxxxxxxxxx-yyyyy   1/1     Running   0          2m
# redis-xxxxxxxxxx-xxxxx                  1/1     Running   0          3m
```

### 2. Service の確認

```bash
kubectl get svc -n chatwork-lark

# CLUSTER-IP が割り当てられていることを確認
```

### 3. Ingress の確認

```bash
kubectl get ingress -n chatwork-lark

# ADDRESS にIPアドレスが割り当てられていることを確認
# HOSTS にドメイン名が正しく表示されることを確認
```

### 4. ヘルスチェック

```bash
# DNS解決確認
nslookup chatwork-lark.your-domain.com

# HTTPS接続確認
curl https://chatwork-lark.your-domain.com/health/

# 期待されるレスポンス:
# {"status":"healthy","redis":true,"details":{"redis":"connected"}}
```

### 5. TLS証明書の確認

```bash
# 証明書の取得状況確認
kubectl get certificate -n chatwork-lark

# 詳細確認
kubectl describe certificate chatwork-lark-tls -n chatwork-lark

# STATUS が True になるまで待つ（最大5分程度）
```

### 6. ログの確認

```bash
# アプリケーションログ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# エラーがないことを確認
# 起動ログに以下が含まれることを確認:
# - "application_starting"
# - "redis_connected"
# - "mappings_loaded_successfully"
```

---

## 🧪 動作テスト

### 1. Webhook URL の設定

#### Chatwork

1. Chatwork のグループチャットを開く
2. 右上の歯車アイコン → 「Webhook」
3. 「Webhook を追加」
4. URL: `https://chatwork-lark.your-domain.com/webhook/chatwork/`
5. 保存

#### Lark

1. [Lark Open Platform](https://open.larksuite.com/) にアクセス
2. アプリを開く
3. 「イベントとコールバック」タブ
4. Request URL: `https://chatwork-lark.your-domain.com/webhook/lark/`
5. 検証ボタンをクリック（緑のチェックマークが表示されることを確認）

### 2. メッセージ同期テスト

#### Chatwork → Lark

1. Chatwork のマッピング済みルームでメッセージを送信
2. Lark の対応するチャットでメッセージが受信されることを確認
3. フォーマットが正しいことを確認:
   ```
   [From Chatwork] ユーザー名: メッセージ内容
   ```

#### Lark → Chatwork

1. Lark のマッピング済みチャットでメッセージを送信
2. Chatwork の対応するルームでメッセージが受信されることを確認
3. フォーマットが正しいことを確認:
   ```
   [From Lark] ユーザー名: メッセージ内容
   ```

### 3. ループ検出テスト

1. 同期されたメッセージ（`[From Lark]` または `[From Chatwork]` で始まる）に返信
2. 無限ループにならず、一度だけ同期されることを確認
3. ログで `loop_detected_skipping` が記録されることを確認

### 4. エラー処理テスト

1. 存在しないルームIDを設定して ConfigMap を更新
2. メッセージを送信
3. エラーログが記録されることを確認
4. DLQ（Dead Letter Queue）にメッセージが保存されることを確認:
   ```bash
   kubectl exec -n chatwork-lark redis-xxx -- redis-cli KEYS "failed:*"
   ```

---

## 📊 モニタリング設定確認

### Prometheus メトリクス

```bash
# Prometheusでメトリクスが収集されているか確認
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# ブラウザで http://localhost:9090 を開く
# Targets で chatwork-lark-bridge が表示され、状態が UP であることを確認
```

### Grafana ダッシュボード

```bash
# Grafana にアクセス
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# ブラウザで http://localhost:3000 を開く
# ログイン（デフォルト: admin / prom-operator）
# ダッシュボードで Pod のメトリクスが表示されることを確認
```

### アラート設定

```bash
# PrometheusRule が適用されているか確認
kubectl get prometheusrule -n chatwork-lark

# アラートが正しく設定されているか確認
# Prometheus UI の Alerts タブで確認
```

---

## 🔒 セキュリティ確認

### Pod Security

```bash
# Pod が非rootユーザーで実行されているか確認
kubectl get pod -n chatwork-lark chatwork-lark-bridge-xxx -o jsonpath='{.spec.securityContext}'

# 出力例:
# {"fsGroup":1000,"runAsNonRoot":true,"runAsUser":1000}
```

### Network Policy

```bash
# Network Policy が適用されているか確認（設定している場合）
kubectl get networkpolicy -n chatwork-lark
```

### Image Scan

```bash
# Trivy でイメージをスキャン
trivy image chatwork-lark-bridge:latest

# HIGH/CRITICAL の脆弱性がないことを確認
```

---

## 📝 ドキュメント整備確認

- [ ] **運用手順書**
  - [ ] デプロイ手順
  - [ ] ロールバック手順
  - [ ] スケーリング手順
  - [ ] バックアップ・リストア手順

- [ ] **インシデント対応**
  - [ ] インシデント対応フロー
  - [ ] エスカレーションパス
  - [ ] 連絡先リスト
  - [ ] 既知の問題とその対処法

- [ ] **監視・アラート**
  - [ ] 監視項目リスト
  - [ ] アラート通知先
  - [ ] SLA/SLO定義
  - [ ] オンコール体制

---

## 🎯 本番運用開始

すべてのチェック項目が完了したら、本番運用を開始できます。

### 運用開始後の定期確認

**毎日:**
- [ ] ヘルスチェックエンドポイントの確認
- [ ] エラーログの確認
- [ ] メッセージ同期が正常に動作しているか確認

**毎週:**
- [ ] リソース使用状況の確認
- [ ] DLQ（失敗メッセージキュー）の確認
- [ ] パフォーマンスメトリクスの確認

**毎月:**
- [ ] Secret のローテーション検討
- [ ] ログの分析とトレンド確認
- [ ] バックアップの動作確認

---

## 🆘 トラブル時の連絡先

**緊急連絡先:**
- システム管理者: [担当者名] - [連絡先]
- Chatwork 管理者: [担当者名] - [連絡先]
- Lark 管理者: [担当者名] - [連絡先]

**エスカレーション:**
1. レベル1: 現場担当者（初動対応）
2. レベル2: システム管理者（技術的問題）
3. レベル3: マネージャー（ビジネス影響判断）

---

**最終確認日:** ___________
**確認者:** ___________
**承認者:** ___________
