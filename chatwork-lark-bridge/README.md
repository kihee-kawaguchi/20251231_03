# 🌉 Chatwork-Lark Bridge

[![Tests](https://img.shields.io/badge/tests-79%20passed-success)](https://github.com/kihee-kawaguchi/20251231_03)
[![Coverage](https://img.shields.io/badge/coverage-67.38%25-green)](https://github.com/kihee-kawaguchi/20251231_03)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**本番環境対応**の Chatwork ↔ Lark (Feishu) 双方向メッセージ同期サービス

リアルタイムでメッセージを同期し、チーム間のコミュニケーションをシームレスに統合します。

## ✨ 主要機能

- 🔄 **双方向メッセージ同期** - Chatwork と Lark 間でリアルタイム同期
- 🔒 **セキュアな通信** - Webhook 署名検証、TLS/SSL 対応
- 🛡️ **ループ検出** - メッセージプレフィックスによる無限ループ防止
- 🎯 **重複防止** - Redis を使用した重複メッセージ検出
- 📊 **高可用性** - Kubernetes 2レプリカ構成、自動フェイルオーバー
- 🧪 **包括的テスト** - 79テスト (100%合格)、67%カバレッジ
- 📈 **監視対応** - Prometheus メトリクス、構造化ログ
- 🚀 **本番対応** - Docker、Kubernetes、CI/CD完備

## 🚀 クイックスタート

### Docker Compose (推奨)

```bash
# リポジトリクローン
git clone https://github.com/kihee-kawaguchi/20251231_03.git
cd 20251231_03/chatwork-lark-bridge

# 環境変数設定
cp .env.example .env
nano .env  # 認証情報を入力

# 起動
docker-compose up -d

# ヘルスチェック
curl http://localhost:8000/health/
```

### ローカル開発

```bash
# Python 3.12+ 必須
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
export CHATWORK_API_TOKEN=your_token
export LARK_APP_ID=cli_xxx
# ... その他の環境変数

# アプリ起動
uvicorn src.main:app --reload

# 別ターミナルでテスト実行
pytest -v
```

## 📋 必須環境変数

```bash
# Chatwork
CHATWORK_API_TOKEN=xxx          # APIトークン
CHATWORK_WEBHOOK_SECRET=xxx     # Webhook Secret (base64)

# Lark
LARK_APP_ID=cli_xxx            # App ID
LARK_APP_SECRET=xxx            # App Secret
LARK_VERIFICATION_TOKEN=xxx     # Verification Token

# Redis
REDIS_URL=redis://localhost:6379/0

# オプション
LOG_LEVEL=INFO
ENABLE_LOOP_DETECTION=true
MESSAGE_PREFIX_CHATWORK=[From Lark]
MESSAGE_PREFIX_LARK=[From Chatwork]
```

詳細は [.env.example](.env.example) を参照してください。

## 🏗️ アーキテクチャ

```
┌─────────────┐              ┌─────────────┐
│  Chatwork   │◄────────────►│    Lark     │
└──────┬──────┘              └──────┬──────┘
       │                            │
       │ Webhook                    │ Webhook
       ▼                            ▼
┌──────────────────────────────────────────┐
│         nginx-ingress (TLS/SSL)          │
└─────────────────┬────────────────────────┘
                  ▼
┌──────────────────────────────────────────┐
│    FastAPI (2 replicas, HA)              │
│  ┌────────────┐      ┌─────────────┐    │
│  │ Chatwork   │      │    Lark     │    │
│  │  Handler   │      │   Handler   │    │
│  └─────┬──────┘      └──────┬──────┘    │
│        └────────┬────────────┘           │
│                 ▼                        │
│       ┌──────────────────┐               │
│       │Message Processor │               │
│       │- Loop Detection  │               │
│       │- Duplicate Check │               │
│       └─────────┬────────┘               │
└─────────────────┼──────────────────────┘
                  ▼
          ┌───────────────┐
          │     Redis     │
          │  (Tracking)   │
          └───────────────┘
```

## 📊 API エンドポイント

| Method | Path | 説明 |
|--------|------|------|
| `POST` | `/webhook/chatwork/` | Chatwork Webhook受信 |
| `POST` | `/webhook/lark/` | Lark Webhook受信 |
| `GET` | `/health/` | ヘルスチェック (詳細) |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus メトリクス |
| `GET` | `/docs` | Swagger UI |

## 🧪 テスト

### テスト実行

```bash
# 全テスト実行
pytest -v

# カバレッジ付き
pytest --cov=src --cov-report=html
open htmlcov/index.html

# 特定カテゴリのみ
pytest tests/unit/         # ユニットテスト
pytest tests/integration/  # 統合テスト
pytest tests/e2e/          # E2Eテスト

# 高速実行 (遅いテストをスキップ)
pytest -m "not slow"
```

### テスト統計

```
✅ 79/79 テスト合格 (100%)
├── ユニットテスト: 54個
├── 統合テスト: 20個
└── E2Eテスト: 5個

📈 カバレッジ: 67.38%
├── src/api/: 88-94%
├── src/core/: 65-92%
├── src/services/: 16-83%
└── src/utils/: 68%
```

## 🚢 本番デプロイ

### Kubernetes デプロイ

```bash
cd k8s/production

# 1. Secret 作成
cp secret-template.yaml secret.yaml
nano secret.yaml  # 実際の認証情報を入力

# 2. ConfigMap 編集
nano configmap.yaml  # Room/User マッピング設定

# 3. Ingress 編集
nano ingress.yaml  # ドメイン名設定

# 4. デプロイ実行
./deploy-production.sh

# 5. 確認
kubectl get pods -n chatwork-lark
kubectl get ingress -n chatwork-lark
curl https://your-domain.com/health/
```

詳細は [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) を参照してください。

### 本番環境構成

- **高可用性**: 2レプリカ + Pod Anti-Affinity
- **ゼロダウンタイム**: RollingUpdate戦略
- **自動回復**: Liveness/Readiness Probes
- **セキュリティ**: 
  - 非rootユーザー実行
  - Read-only filesystem
  - TLS/SSL (Let's Encrypt)
  - Rate limiting
  - Security headers
- **監視**: Prometheus annotations, 構造化ログ

## 📁 プロジェクト構造

```
chatwork-lark-bridge/
├── src/                    # アプリケーションコード (765行)
│   ├── api/               # FastAPI endpoints
│   ├── core/              # Config, exceptions, logging
│   ├── services/          # Business logic
│   └── utils/             # Utilities
├── tests/                  # テストスイート (79テスト)
│   ├── unit/              # ユニットテスト (54)
│   ├── integration/       # 統合テスト (20)
│   └── e2e/               # E2Eテスト (5)
├── k8s/                    # Kubernetes manifests
│   └── production/        # 本番環境設定
├── config/                 # マッピング設定
├── .github/workflows/      # CI/CD
└── docs/                   # ドキュメント
```

## 🔧 設定

### Room マッピング

`config/room_mappings.json`:

```json
{
  "mappings": [
    {
      "chatwork_room_id": "12345678",
      "lark_chat_id": "oc_a1b2c3d4e5f6",
      "sync_direction": "both"
    }
  ]
}
```

### User マッピング

`config/user_mappings.json`:

```json
{
  "mappings": [
    {
      "chatwork_user_id": "111",
      "lark_open_id": "ou_a1b2c3d4e5f6"
    }
  ]
}
```

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) | 本番環境セットアップ完全ガイド |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | デプロイ前チェックリスト |
| [DEPLOYMENT.md](DEPLOYMENT.md) | デプロイメント手順 |
| [TESTING.md](TESTING.md) | テスト実行ガイド |
| [PROJECT_COMPLETION_REPORT.md](PROJECT_COMPLETION_REPORT.md) | プロジェクト完了報告 |
| [CLAUDE.md](CLAUDE.md) | Claude Code 開発ガイド |

## 🛠️ 技術スタック

### バックエンド
- **Python** 3.12
- **FastAPI** 0.115.6 - 高性能非同期Webフレームワーク
- **Pydantic** 2.10.5 - データバリデーション
- **aiohttp** 3.11.11 - 非同期HTTPクライアント
- **Redis** 5.2.1 - メッセージトラッキング

### インフラ
- **Docker** - コンテナ化
- **Kubernetes** - オーケストレーション
- **nginx-ingress** - リバースプロキシ
- **cert-manager** - TLS証明書管理
- **Prometheus** - メトリクス収集

### 開発ツール
- **pytest** - テストフレームワーク
- **black** - コードフォーマッター
- **flake8** - Linter
- **mypy** - 型チェッカー

## 🤝 コントリビューション

コントリビューション歓迎！以下の手順でPRを送ってください:

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/20251231_03.git

# 2. ブランチ作成
git checkout -b feature/amazing-feature

# 3. 変更をコミット
git commit -m "feat: add amazing feature"

# 4. プッシュ
git push origin feature/amazing-feature

# 5. PR作成
gh pr create --title "feat: Add amazing feature"
```

### 開発ガイドライン
- Conventional Commits を使用
- テストを追加（カバレッジ維持）
- Black + isort でフォーマット
- 型ヒント必須
- Docstring を記述

## 📝 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照

## 🙏 謝辞

- [FastAPI](https://fastapi.tiangolo.com/) - 素晴らしいWebフレームワーク
- [Chatwork API](https://developer.chatwork.com/) - Chatwork API
- [Lark Open Platform](https://open.larksuite.com/) - Lark API

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/kihee-kawaguchi/20251231_03/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kihee-kawaguchi/20251231_03/discussions)

---

<div align="center">

🤖 **Generated with [Claude Code](https://claude.com/claude-code)**

Made with ❤️ by Claude Sonnet 4.5

</div>
