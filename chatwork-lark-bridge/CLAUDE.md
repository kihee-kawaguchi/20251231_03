# Chatwork-Lark Bridge - Claude Code Context

## プロジェクト概要

**Chatwork-Lark Bridge** - Chatwork と Lark (Feishu) の双方向メッセージ同期サービス

本番環境対応の FastAPI マイクロサービスで、リアルタイムメッセージ同期を実現します。

## 🎯 主要機能

- ✅ Chatwork ↔ Lark 双方向メッセージ同期
- ✅ ループ検出（プレフィックスベース）
- ✅ 重複メッセージ防止（Redis）
- ✅ Webhook 署名検証
- ✅ 高可用性構成（Kubernetes）
- ✅ 包括的なテストスイート（79テスト、67%カバレッジ）

## 📁 プロジェクト構造

```
chatwork-lark-bridge/
├── src/                      # アプリケーションコード (765行)
│   ├── api/                 # FastAPI endpoints
│   │   ├── chatwork.py     # Chatwork webhook handler
│   │   ├── lark.py         # Lark webhook handler
│   │   └── health.py       # Health check endpoints
│   ├── core/                # Core functionality
│   │   ├── config.py       # Settings & environment vars
│   │   ├── exceptions.py   # Custom exceptions
│   │   ├── logging.py      # Structured logging
│   │   └── retry.py        # Retry logic with backoff
│   ├── services/            # Business logic
│   │   ├── chatwork_client.py    # Chatwork API client
│   │   ├── lark_client.py        # Lark API client
│   │   ├── message_processor.py  # Message sync logic
│   │   ├── redis_client.py       # Redis operations
│   │   └── mapping_loader.py     # Config loader
│   └── utils/
│       └── webhook_verification.py  # Signature validation
├── tests/                    # Test suite (79 tests)
│   ├── unit/                # Unit tests (54)
│   ├── integration/         # Integration tests (20)
│   └── e2e/                 # End-to-end tests (5)
├── k8s/                      # Kubernetes manifests
│   ├── production/          # Production configs
│   │   ├── deployment.yaml       # 2 replicas, HA
│   │   ├── ingress.yaml          # TLS + rate limiting
│   │   ├── configmap.yaml        # App configuration
│   │   ├── secret-template.yaml  # Secrets template
│   │   └── deploy-production.sh  # Deploy script
│   ├── namespace.yaml
│   ├── service.yaml
│   └── redis-deployment.yaml
├── config/                   # Configuration files
│   ├── room_mappings.json   # Chatwork ↔ Lark room mapping
│   └── user_mappings.json   # User mapping
└── docs/                     # Documentation (13 files)
```

## 🚀 クイックスタート

### ローカル開発

```bash
# 依存関係インストール
pip install -r requirements.txt
pip install -r requirements-test.txt

# 環境変数設定
cp .env.example .env
nano .env  # 認証情報を入力

# テスト実行
pytest -v

# アプリ起動
uvicorn src.main:app --reload
```

### Docker Compose

```bash
# 起動
docker-compose up -d

# ログ確認
docker-compose logs -f app

# 停止
docker-compose down
```

### 本番デプロイ

```bash
cd k8s/production

# 設定ファイル編集
cp secret-template.yaml secret.yaml
nano secret.yaml      # 認証情報入力
nano configmap.yaml   # マッピング設定
nano ingress.yaml     # ドメイン設定

# デプロイ実行
./deploy-production.sh
```

## 🧪 テスト

### テスト実行

```bash
# 全テスト実行
pytest -v

# カバレッジ付き
pytest --cov=src --cov-report=html

# 特定カテゴリ
pytest tests/unit/           # ユニットテストのみ
pytest tests/integration/    # 統合テストのみ
pytest tests/e2e/            # E2Eテストのみ

# マーカー指定
pytest -m "not slow"         # 遅いテストをスキップ
pytest -m e2e                # E2Eテストのみ
```

### テスト統計

- **合計**: 79テスト
- **合格率**: 100%
- **カバレッジ**: 67.38%
- **実行時間**: 約100秒

## 🔧 開発ガイドライン

### コーディング規約

```python
# Type hints 必須
async def send_message(
    room_id: str,
    message: str,
    user_id: Optional[str] = None
) -> str:
    """Send message to Chatwork room.
    
    Args:
        room_id: Chatwork room ID
        message: Message content
        user_id: Optional user ID for mention
    
    Returns:
        Message ID
    """
    pass

# Docstring 形式: Google style
# 非同期処理: async/await
# エラーハンドリング: カスタム例外使用
# ログ: 構造化ログ (JSON)
```

### Git Workflow

```bash
# ブランチ作成
git checkout -b feature/xxx

# コミット (Conventional Commits)
git commit -m "feat: add user mention support"
git commit -m "fix: handle webhook timeout"
git commit -m "docs: update API documentation"

# プッシュ
git push origin feature/xxx

# PR 作成
gh pr create --title "feat: Add user mention support"
```

## 📊 アーキテクチャ

### システム構成

```
┌─────────────┐         ┌─────────────┐
│  Chatwork   │         │    Lark     │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │ Webhook               │ Webhook
       ▼                       ▼
┌─────────────────────────────────────┐
│     nginx-ingress (TLS/SSL)         │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│  FastAPI Application (2 replicas)   │
│  ┌─────────────┐  ┌───────────────┐ │
│  │  Chatwork   │  │     Lark      │ │
│  │   Handler   │  │    Handler    │ │
│  └──────┬──────┘  └───────┬───────┘ │
│         │                 │         │
│         └────────┬────────┘         │
│                  ▼                  │
│        ┌──────────────────┐         │
│        │ Message Processor│         │
│        └──────────────────┘         │
└───────────────┬─────────────────────┘
                ▼
        ┌───────────────┐
        │     Redis     │
        │ (Message      │
        │  Tracking)    │
        └───────────────┘
```

### データフロー

```
1. Chatwork Webhook受信
   ↓
2. 署名検証
   ↓
3. 重複チェック (Redis)
   ↓
4. ループ検出 (プレフィックス)
   ↓
5. Larkへメッセージ送信
   ↓
6. マッピング保存 (Redis)

(Lark → Chatwork も同様)
```

## 🔐 セキュリティ

### Webhook 検証

```python
# Chatwork: HMAC-SHA256
signature = base64.b64encode(
    hmac.new(secret, body, hashlib.sha256).digest()
)

# Lark: Verification Token
if event.header.token != settings.lark_verification_token:
    raise SignatureVerificationError()
```

### 環境変数管理

```bash
# 必須環境変数
CHATWORK_API_TOKEN=xxx
CHATWORK_WEBHOOK_SECRET=xxx (base64)
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_VERIFICATION_TOKEN=xxx
REDIS_URL=redis://localhost:6379/0

# オプション
LOG_LEVEL=INFO
ENABLE_LOOP_DETECTION=true
MESSAGE_PREFIX_CHATWORK=[From Lark]
MESSAGE_PREFIX_LARK=[From Chatwork]
```

### Kubernetes Secrets

```bash
# Sealed Secrets 使用推奨
kubectl create secret generic chatwork-lark-secrets \
  --from-literal=chatwork-api-token=xxx \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml
```

## 📈 監視とログ

### ヘルスチェック

```bash
# Basic health
curl https://your-domain.com/health/

# Liveness probe
curl https://your-domain.com/health/live

# Readiness probe
curl https://your-domain.com/health/ready
```

### Prometheus メトリクス

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

### ログ

```json
{
  "event": "message_received",
  "platform": "chatwork",
  "room_id": "12345678",
  "message_id": "999",
  "level": "info",
  "timestamp": "2025-12-31T12:00:00Z"
}
```

## 🐛 トラブルシューティング

### よくある問題

```bash
# Redis接続エラー
kubectl logs -n chatwork-lark -l app=chatwork-lark-bridge | grep redis

# Webhook受信されない
kubectl describe ingress chatwork-lark-ingress -n chatwork-lark

# Pod起動しない
kubectl describe pod -n chatwork-lark chatwork-lark-bridge-xxx
```

## 📚 参考ドキュメント

- [README.md](./README.md) - プロジェクト概要
- [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md) - 本番セットアップ
- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
- [TESTING.md](./TESTING.md) - テストガイド
- [PROJECT_COMPLETION_REPORT.md](./PROJECT_COMPLETION_REPORT.md) - 完了報告

## 🛠️ 開発ツール

```bash
# コードフォーマット
black src/ tests/
isort src/ tests/

# Linting
flake8 src/ tests/
pylint src/

# 型チェック
mypy src/

# セキュリティスキャン
bandit -r src/
safety check
```

## 📞 サポート

- **Issues**: GitHub Issues で問題報告
- **PRs**: Pull Request歓迎
- **Documentation**: [docs/](./docs/) 参照

---

🤖 **このプロジェクトは Claude Code で開発されました**

*Claude Code が自動的にこのファイルを参照します。*
