# 本番環境デプロイ設定
# Production Deployment Configuration

このディレクトリには本番環境用の Kubernetes マニフェストが含まれています。

---

## 📁 ファイル構成

```
k8s/production/
├── README.md                  # このファイル
├── configmap.yaml            # アプリケーション設定とマッピング
├── secret-template.yaml      # Secret テンプレート（要編集）
├── deployment.yaml           # Deployment 設定（レプリカ2）
├── ingress.yaml             # Ingress + TLS 設定（要編集）
└── deploy-production.sh     # 自動デプロイスクリプト
```

---

## 🚀 クイックスタート

### 1. 設定ファイルの編集

#### Secret の作成

```bash
# 1. テンプレートをコピー
cp secret-template.yaml secret.yaml

# 2. 実際の認証情報を入力
nano secret.yaml

# 3. Sealed Secret に変換（推奨）
kubeseal -f secret.yaml -w sealed-secret.yaml

# 4. 元のファイルを削除
rm secret.yaml
```

**必須: 以下を実際の値に置き換えてください:**
- `REPLACE_WITH_YOUR_CHATWORK_API_TOKEN`
- `REPLACE_WITH_BASE64_ENCODED_WEBHOOK_SECRET`
- `cli_REPLACE_WITH_YOUR_APP_ID`
- `REPLACE_WITH_YOUR_APP_SECRET`
- `REPLACE_WITH_YOUR_VERIFICATION_TOKEN`

#### ConfigMap の編集

```bash
nano configmap.yaml
```

**必須: マッピング情報を実際の値に置き換えてください:**
- `REPLACE_WITH_ACTUAL_CHATWORK_ROOM_ID` → 実際のChatwork Room ID
- `REPLACE_WITH_ACTUAL_LARK_CHAT_ID` → 実際のLark Chat ID
- `REPLACE_WITH_ACTUAL_USER_ID` → 実際のChatwork User ID
- `REPLACE_WITH_ACTUAL_OPEN_ID` → 実際のLark Open ID

#### Ingress の編集

```bash
nano ingress.yaml
```

**必須: ドメイン名を置き換えてください:**
- `REPLACE_WITH_YOUR_DOMAIN.com` → 実際のドメイン名（例: chatwork-lark.example.com）

### 2. デプロイ実行

```bash
# 自動デプロイスクリプトを実行
./deploy-production.sh
```

または手動で:

```bash
# Namespace 作成
kubectl apply -f ../../k8s/namespace.yaml

# Secrets 適用
kubectl apply -f sealed-secret.yaml  # または secret.yaml

# ConfigMap 適用
kubectl apply -f configmap.yaml

# Redis デプロイ
kubectl apply -f ../../k8s/redis-deployment.yaml
kubectl wait --for=condition=ready pod -l app=redis -n chatwork-lark --timeout=60s

# アプリケーション デプロイ
kubectl apply -f deployment.yaml
kubectl apply -f ../../k8s/service.yaml
kubectl wait --for=condition=available deployment/chatwork-lark-bridge -n chatwork-lark --timeout=120s

# Ingress 適用
kubectl apply -f ingress.yaml
```

---

## ✅ デプロイ後の確認

### 1. Pod 状態確認

```bash
kubectl get pods -n chatwork-lark

# 期待される出力:
# NAME                                    READY   STATUS    RESTARTS   AGE
# chatwork-lark-bridge-xxxxxxxxxx-xxxxx   1/1     Running   0          2m
# chatwork-lark-bridge-xxxxxxxxxx-yyyyy   1/1     Running   0          2m
# redis-xxxxxxxxxx-xxxxx                  1/1     Running   0          3m
```

### 2. Service 確認

```bash
kubectl get svc -n chatwork-lark
```

### 3. Ingress 確認

```bash
kubectl get ingress -n chatwork-lark

# ADDRESS フィールドにIPアドレスが表示されることを確認
```

### 4. TLS 証明書確認

```bash
# 証明書の状態確認
kubectl get certificate -n chatwork-lark

# 詳細確認
kubectl describe certificate chatwork-lark-tls -n chatwork-lark

# READY が True になることを確認（数分かかる場合があります）
```

### 5. ヘルスチェック

```bash
# DNSが正しく設定されていることを確認
nslookup your-domain.com

# アプリケーションの動作確認
curl https://your-domain.com/health/

# 期待される出力:
# {"status":"healthy","redis":true,"details":{"redis":"connected"}}
```

### 6. ログ確認

```bash
# リアルタイムログ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge -f

# エラーログのみ
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge | grep ERROR
```

---

## 🔧 Webhook 設定

### Chatwork

1. Chatwork のグループチャットを開く
2. 右上の歯車アイコン → 「Webhook」
3. 「Webhook を追加」
4. **URL:** `https://your-domain.com/webhook/chatwork/`
5. 保存

### Lark

1. [Lark Open Platform](https://open.larksuite.com/) にアクセス
2. アプリを開く
3. 「イベントとコールバック」タブ
4. **Request URL:** `https://your-domain.com/webhook/lark/`
5. 検証ボタンをクリック（緑のチェックマークが表示されることを確認）

---

## 📊 監視設定（オプション）

### Prometheus メトリクス確認

```bash
# Port Forward でアクセス
kubectl port-forward -n chatwork-lark svc/chatwork-lark-service 8000:80

# メトリクスエンドポイント
curl http://localhost:8000/metrics
```

### Grafana ダッシュボード

```bash
# Grafana にアクセス（Prometheus Operator がインストール済みの場合）
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# http://localhost:3000
# ログイン: admin / prom-operator
```

---

## 🔄 アップデート手順

### イメージの更新

```bash
# 新しいイメージをビルド
docker build -t chatwork-lark-bridge:v1.1.0 .

# レジストリにプッシュ
docker tag chatwork-lark-bridge:v1.1.0 yourregistry/chatwork-lark-bridge:v1.1.0
docker push yourregistry/chatwork-lark-bridge:v1.1.0

# deployment.yaml のイメージタグを更新
sed -i 's/chatwork-lark-bridge:latest/chatwork-lark-bridge:v1.1.0/' deployment.yaml

# デプロイ
kubectl apply -f deployment.yaml

# ローリングアップデートの進行状況確認
kubectl rollout status deployment/chatwork-lark-bridge -n chatwork-lark
```

### ConfigMap の更新

```bash
# ConfigMap を編集
nano configmap.yaml

# 適用
kubectl apply -f configmap.yaml

# Pod を再起動（ConfigMap の変更を反映）
kubectl rollout restart deployment/chatwork-lark-bridge -n chatwork-lark
```

---

## ↩️ ロールバック

### 直前のバージョンに戻す

```bash
kubectl rollout undo deployment/chatwork-lark-bridge -n chatwork-lark
```

### 特定のリビジョンに戻す

```bash
# リビジョン履歴を確認
kubectl rollout history deployment/chatwork-lark-bridge -n chatwork-lark

# 特定のリビジョンに戻す
kubectl rollout undo deployment/chatwork-lark-bridge -n chatwork-lark --to-revision=3
```

---

## 🗑️ アンインストール

```bash
# すべてのリソースを削除
kubectl delete namespace chatwork-lark

# または個別に削除
kubectl delete -f ingress.yaml
kubectl delete -f deployment.yaml
kubectl delete -f ../../k8s/service.yaml
kubectl delete -f ../../k8s/redis-deployment.yaml
kubectl delete -f configmap.yaml
kubectl delete -f sealed-secret.yaml
```

---

## 🐛 トラブルシューティング

### Pod が起動しない

```bash
# Pod の詳細を確認
kubectl describe pod -n chatwork-lark chatwork-lark-bridge-xxx

# ログを確認
kubectl logs -n chatwork-lark chatwork-lark-bridge-xxx

# イベントを確認
kubectl get events -n chatwork-lark --sort-by='.lastTimestamp'
```

### Webhook が受信されない

```bash
# Ingress の設定確認
kubectl describe ingress chatwork-lark-ingress -n chatwork-lark

# Service のエンドポイント確認
kubectl get endpoints -n chatwork-lark

# ログでWebhook受信を確認
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge | grep webhook
```

### TLS 証明書が取得できない

```bash
# Certificate の状態確認
kubectl describe certificate chatwork-lark-tls -n chatwork-lark

# cert-manager のログ確認
kubectl logs -n cert-manager deployment/cert-manager

# Challenge の確認
kubectl get challenge -n chatwork-lark
```

---

## 📚 参考ドキュメント

- [PRODUCTION_SETUP.md](../../PRODUCTION_SETUP.md) - 詳細セットアップガイド
- [PRODUCTION_CHECKLIST.md](../../PRODUCTION_CHECKLIST.md) - デプロイチェックリスト
- [DEPLOYMENT.md](../../DEPLOYMENT.md) - デプロイメントガイド
- [Kubernetes 公式ドキュメント](https://kubernetes.io/ja/docs/)

---

**本番環境へのデプロイ準備が完了しました！** 🚀

設定ファイルを編集して `./deploy-production.sh` を実行してください。
