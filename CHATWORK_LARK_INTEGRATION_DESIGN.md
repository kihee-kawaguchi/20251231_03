# Chatwork ⇄ Lark メッセージ双方向連携 設計書
## Chatwork-Lark Bidirectional Messaging Integration Design

**作成日 / Date:** 2025年12月31日
**バージョン / Version:** 1.0
**ステータス / Status:** 設計フェーズ / Design Phase

---

## 目次 / Table of Contents

1. [概要 / Overview](#概要--overview)
2. [システムアーキテクチャ / System Architecture](#システムアーキテクチャ--system-architecture)
3. [API機能比較 / API Capabilities Comparison](#api機能比較--api-capabilities-comparison)
4. [メッセージ同期仕様 / Message Synchronization Specification](#メッセージ同期仕様--message-synchronization-specification)
5. [技術スタック / Technology Stack](#技術スタック--technology-stack)
6. [実装計画 / Implementation Plan](#実装計画--implementation-plan)
7. [セキュリティとパフォーマンス / Security and Performance](#セキュリティとパフォーマンス--security-and-performance)
8. [制限事項と課題 / Limitations and Challenges](#制限事項と課題--limitations-and-challenges)

---

## 概要 / Overview

### 目的 / Purpose

ChatworkとLarkの間でメッセージをリアルタイムに双方向同期し、両プラットフォームのユーザーがシームレスにコミュニケーションできる統合システムを構築する。

### 主要機能 / Key Features

✅ **リアルタイム同期**: Webhook/イベントサブスクリプションによる即時メッセージ転送
✅ **双方向通信**: Chatwork → Lark および Lark → Chatwork の両方向をサポート
✅ **ユーザー識別**: 送信者情報の保持と表示
✅ **ループ防止**: 同一メッセージの無限転送を防止
✅ **エラーハンドリング**: リトライロジックとフォールバック機構

### ユースケース / Use Cases

- **クロスプラットフォームチーム**: 一部がChatwork、一部がLarkを使用
- **企業間コラボレーション**: パートナー企業との連携
- **段階的移行**: ChatworkからLarkへの移行期間中の橋渡し
- **マルチチャネルサポート**: カスタマーサポートでの複数プラットフォーム対応

---

## システムアーキテクチャ / System Architecture

### アーキテクチャ図 / Architecture Diagram

```
┌─────────────────┐                    ┌─────────────────┐
│   Chatwork      │                    │      Lark       │
│   Platform      │                    │    Platform     │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │ Webhook                              │ Event
         │ (message_created)                    │ Subscription
         │                                      │
         ▼                                      ▼
┌────────────────────────────────────────────────────────┐
│                  Integration Server                     │
│                                                         │
│  ┌──────────────┐          ┌──────────────┐           │
│  │   Chatwork   │          │     Lark     │           │
│  │   Webhook    │◄────────►│   Webhook    │           │
│  │   Handler    │          │   Handler    │           │
│  └──────┬───────┘          └──────┬───────┘           │
│         │                         │                    │
│         ▼                         ▼                    │
│  ┌─────────────────────────────────────┐              │
│  │      Message Processing Engine       │              │
│  │  - Loop Detection                    │              │
│  │  - User Mapping                      │              │
│  │  - Format Conversion                 │              │
│  │  - Deduplication                     │              │
│  └─────────────────────────────────────┘              │
│         │                         │                    │
│         ▼                         ▼                    │
│  ┌──────────────┐          ┌──────────────┐           │
│  │   Lark API   │          │  Chatwork    │           │
│  │   Client     │          │  API Client  │           │
│  └──────────────┘          └──────────────┘           │
│         │                         │                    │
│         ▼                         ▼                    │
│  ┌─────────────────────────────────────┐              │
│  │         Data Store (Redis)           │              │
│  │  - Message ID Mapping                │              │
│  │  - User ID Mapping                   │              │
│  │  - Room ID Mapping                   │              │
│  │  - Deduplication Cache               │              │
│  └─────────────────────────────────────┘              │
└────────────────────────────────────────────────────────┘
         │                         │
         │ POST Message            │ POST Message
         ▼                         ▼
┌─────────────────┐          ┌─────────────────┐
│   Lark Room     │          │  Chatwork Room  │
└─────────────────┘          └─────────────────┘
```

### コンポーネント / Components

#### 1. Webhook Handlers
- **Chatwork Webhook Handler**: Chatworkからのイベントを受信・検証
- **Lark Webhook Handler**: Larkからのイベントを受信・検証

#### 2. Message Processing Engine
- ループ検出（無限転送防止）
- ユーザーマッピング
- フォーマット変換
- 重複排除

#### 3. API Clients
- **Lark API Client**: Larkへのメッセージ送信
- **Chatwork API Client**: Chatworkへのメッセージ送信

#### 4. Data Store (Redis)
- メッセージIDマッピング
- ユーザーIDマッピング
- ルームIDマッピング
- 重複排除キャッシュ

---

## API機能比較 / API Capabilities Comparison

### Chatwork API

| 項目 / Item | 詳細 / Details |
|------------|---------------|
| **認証方式** | API Token (x-chatworktoken header) |
| **Webhook** | ✅ サポート (message_created, message_updated, mention_to_me) |
| **メッセージ送信** | POST /v2/rooms/{room_id}/messages |
| **レート制限** | - 全体: 300リクエスト/5分<br>- メッセージ送信: 10リクエスト/10秒 |
| **Webhook制約** | - 最大5個のWebhook設定<br>- HTTPS必須<br>- 10秒以内にレスポンス<br>- リトライなし |
| **署名検証** | HMAC-SHA256 (Base64エンコード) |
| **最新更新** | 2025年4月3日 |

### Lark API

| 項目 / Item | 詳細 / Details |
|------------|---------------|
| **認証方式** | OAuth 2.0 (User/Tenant Access Token) |
| **イベント購読** | ✅ サポート (im.message.receive_v1 等) |
| **メッセージ送信** | POST /im/v1/messages |
| **レート制限** | エンドポイントとプランにより異なる |
| **SDK** | Python, Node.js, Java (公式), Go (コミュニティ) |
| **署名検証** | AES暗号化、トークン検証 |
| **MCP対応** | ✅ 2025年Beta版リリース |

### 比較サマリー / Comparison Summary

| 機能 / Feature | Chatwork | Lark |
|---------------|----------|------|
| Webhook/イベント | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| SDK充実度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| レート制限 | 厳しい | 標準的 |
| 認証方式 | シンプル | OAuth 2.0 (セキュア) |
| ドキュメント | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## メッセージ同期仕様 / Message Synchronization Specification

### メッセージフロー / Message Flow

#### Chatwork → Lark

```
1. Chatworkでメッセージ送信
2. Chatwork Webhook (message_created) が発火
3. Integration Server が受信・検証
4. ループチェック（このメッセージはLarkから来たものか？）
5. ユーザー名・メッセージ本文を整形
6. Lark API経由でメッセージ送信
7. メッセージIDマッピングをRedisに保存
```

#### Lark → Chatwork

```
1. Larkでメッセージ送信
2. Lark Event (im.message.receive_v1) が発火
3. Integration Server が受信・検証
4. ループチェック（このメッセージはChatworkから来たものか？）
5. ユーザー名・メッセージ本文を整形
6. Chatwork API経由でメッセージ送信
7. メッセージIDマッピングをRedisに保存
```

### メッセージフォーマット / Message Format

#### 基本フォーマット

**Chatwork → Lark:**
```
[From Chatwork] {ユーザー名}:
{メッセージ本文}
```

**Lark → Chatwork:**
```
[From Lark] {ユーザー名}:
{メッセージ本文}
```

#### プレフィックスの役割

- ループ検出の識別子
- ユーザーへの視覚的な情報提供
- デバッグ・トレーシング

### ループ防止メカニズム / Loop Prevention Mechanism

#### 1. プレフィックス検出

```python
def is_from_integration(message_body):
    """統合システムから送信されたメッセージか判定"""
    prefixes = ["[From Chatwork]", "[From Lark]"]
    return any(message_body.startswith(prefix) for prefix in prefixes)
```

#### 2. メッセージIDトラッキング

```python
# Redis key schema
processed_messages:{platform}:{message_id} = {
    "source_platform": "chatwork",
    "source_message_id": "123456",
    "target_platform": "lark",
    "target_message_id": "om_abc123",
    "timestamp": 1735642800,
    "ttl": 86400  # 24 hours
}
```

#### 3. タイムスタンプベースの重複排除

- 同一メッセージ（同一送信者、同一本文、5秒以内）の転送を防止

### ルームマッピング / Room Mapping

```python
# Configuration example
room_mappings = {
    "chatwork_room_12345": "lark_chat_oc_abc123",
    "chatwork_room_67890": "lark_chat_oc_def456"
}
```

- 設定ファイルまたはデータベースで管理
- 1:1 マッピング
- 動的追加・削除可能なUI（管理画面）

### ユーザーマッピング / User Mapping

#### オプション1: 名前ベース（シンプル）

```python
def format_message(sender_name, message_body):
    return f"[From Chatwork] {sender_name}:\n{message_body}"
```

**メリット:**
- 実装が簡単
- メンテナンス不要

**デメリット:**
- 同姓同名の場合に混乱
- ユーザーIDが保持されない

#### オプション2: IDマッピング（推奨）

```python
user_mappings = {
    "chatwork_user_123": {
        "name": "山田太郎",
        "lark_user_id": "ou_abc123"
    },
    "lark_user_ou_abc123": {
        "name": "山田太郎",
        "chatwork_user_id": "123"
    }
}
```

**メリット:**
- ユーザー識別が正確
- メンション機能の実装が可能

**デメリット:**
- 初期設定が必要
- メンテナンスコスト

---

## 技術スタック / Technology Stack

### 推奨構成 / Recommended Stack

#### バックエンド / Backend

**言語・フレームワーク:**
- **Python 3.11+** + **FastAPI** (推奨)
  - 理由: 非同期処理、高パフォーマンス、優れたドキュメント生成
  - 代替: Node.js + Express (JavaScript環境の場合)

**APIクライアント:**
- `lark-oapi` (Python SDK for Lark)
- `requests` または `httpx` (Chatwork API用)

**Webフレームワーク:**
```python
# FastAPI example
from fastapi import FastAPI, Request, Header
import hmac
import hashlib
import base64

app = FastAPI()

@app.post("/webhook/chatwork")
async def chatwork_webhook(request: Request, x_chatworkwebhooksignature: str = Header()):
    body = await request.body()
    # Verify signature
    # Process message
    # Send to Lark
    pass

@app.post("/webhook/lark")
async def lark_webhook(request: Request):
    body = await request.json()
    # Verify signature
    # Process message
    # Send to Chatwork
    pass
```

#### データストア / Data Store

**Redis**
- メッセージIDマッピング
- ユーザー・ルームマッピング
- レート制限カウンター
- 重複排除キャッシュ

```python
# Redis schema
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Message tracking
redis_client.setex(
    f"msg:chatwork:{message_id}",
    86400,  # 24 hours TTL
    json.dumps({"lark_message_id": "om_xxx", "timestamp": time.time()})
)
```

#### インフラ / Infrastructure

**オプション1: クラウドホスティング**
- AWS Lambda + API Gateway (サーバーレス)
- Google Cloud Run (コンテナ)
- Heroku (PaaS、開発・小規模向け)

**オプション2: オンプレミス/VPS**
- Docker + Docker Compose
- Nginx (リバースプロキシ)
- Let's Encrypt (SSL証明書)

#### 監視・ロギング / Monitoring & Logging

- **ログ**: Structlog (構造化ログ)
- **監視**: Prometheus + Grafana
- **エラートラッキング**: Sentry
- **アラート**: Slack/Discord webhook

---

## 実装計画 / Implementation Plan

### フェーズ1: 基盤構築 (1-2週間)

#### タスク / Tasks

- [ ] プロジェクト環境セットアップ
  - Python仮想環境
  - 依存関係インストール（FastAPI, lark-oapi, redis, etc.）
  - Docker環境構築

- [ ] API認証設定
  - Chatwork APIトークン取得・設定
  - Lark App作成、OAuth設定
  - 環境変数管理（.env）

- [ ] Webhook受信エンドポイント作成
  - Chatwork webhook受信
  - Lark event受信
  - 署名検証実装

- [ ] Redis接続・データモデル設計
  - Redis接続確立
  - キースキーマ定義
  - TTL設定

#### 成果物 / Deliverables

✓ 動作するWebhookサーバー（署名検証付き）
✓ Redis接続とデータストア設計
✓ 基本的なログ出力

### フェーズ2: 単方向同期実装 (2週間)

#### タスク / Tasks

- [ ] Chatwork → Lark 単方向同期
  - メッセージ受信処理
  - フォーマット変換
  - Lark API経由でメッセージ送信
  - エラーハンドリング

- [ ] ループ防止メカニズム実装
  - プレフィックス検出
  - メッセージIDトラッキング

- [ ] レート制限対応
  - リトライロジック
  - 指数バックオフ

#### 成果物 / Deliverables

✓ Chatwork → Lark の安定した単方向同期
✓ ループ防止機能
✓ レート制限エラーの適切な処理

### フェーズ3: 双方向同期実装 (2週間)

#### タスク / Tasks

- [ ] Lark → Chatwork 逆方向同期
  - Larkイベント処理
  - フォーマット変換
  - Chatwork API経由でメッセージ送信

- [ ] 双方向ループ防止テスト
  - 相互送信テスト
  - エッジケース検証

- [ ] ルームマッピング設定UI（オプション）
  - 管理画面作成
  - マッピング追加・削除機能

#### 成果物 / Deliverables

✓ 完全な双方向同期
✓ ループフリーな動作確認
✓ (オプション) 管理UI

### フェーズ4: 高度な機能・本番化 (2-3週間)

#### タスク / Tasks

- [ ] ユーザーマッピング実装
  - ユーザーID管理
  - メンション変換（オプション）

- [ ] 監視・ログ強化
  - Prometheus メトリクス
  - Grafana ダッシュボード
  - Sentry エラートラッキング

- [ ] パフォーマンス最適化
  - 非同期処理の最適化
  - Redis接続プール
  - キャッシング戦略

- [ ] ドキュメント作成
  - セットアップガイド
  - 運用マニュアル
  - API仕様書

#### 成果物 / Deliverables

✓ 本番環境へのデプロイ準備完了
✓ 監視・アラートシステム
✓ 完全なドキュメント

### 総所要期間 / Total Duration

**約 7-9週間** （チーム規模: 1-2名）

---

## セキュリティとパフォーマンス / Security and Performance

### セキュリティ対策 / Security Measures

#### 1. Webhook署名検証

**Chatwork:**
```python
def verify_chatwork_signature(body: bytes, signature: str, token: str) -> bool:
    secret = base64.b64decode(token)
    digest = hmac.new(secret, body, hashlib.sha256).digest()
    expected_signature = base64.b64encode(digest).decode()
    return hmac.compare_digest(signature, expected_signature)
```

**Lark:**
```python
from lark_oapi.api.event import EventVerify

def verify_lark_event(request_body: dict, verification_token: str) -> bool:
    # Lark SDK provides built-in verification
    return EventVerify.verify(request_body, verification_token)
```

#### 2. 環境変数管理

```bash
# .env (DO NOT commit to git)
CHATWORK_API_TOKEN=your_chatwork_api_token
CHATWORK_WEBHOOK_SECRET=your_webhook_secret
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=your_lark_app_secret
REDIS_URL=redis://localhost:6379
```

#### 3. HTTPS強制

- すべてのWebhookエンドポイントはHTTPSを使用
- Let's Encrypt等で無料SSL証明書を取得

#### 4. レート制限保護

```python
from fastapi import HTTPException
import time

def check_rate_limit(user_id: str, limit: int = 10, window: int = 10):
    key = f"rate_limit:{user_id}"
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    if current > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

#### 5. 入力サニタイゼーション

- すべての外部入力を検証
- SQLインジェクション対策（該当する場合）
- XSS対策（メッセージ本文のエスケープ）

### パフォーマンス最適化 / Performance Optimization

#### 1. 非同期処理

```python
import asyncio
from httpx import AsyncClient

async def send_to_lark(message: str):
    async with AsyncClient() as client:
        response = await client.post(
            "https://open.larksuite.com/open-apis/im/v1/messages",
            json={"content": message},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response
```

#### 2. Redis接続プール

```python
from redis.asyncio import ConnectionPool, Redis

pool = ConnectionPool.from_url("redis://localhost:6379")
redis_client = Redis(connection_pool=pool)
```

#### 3. バッチ処理（必要に応じて）

- 短時間に複数メッセージを受信した場合、まとめて処理

#### 4. キャッシング

- ユーザーマッピング、ルームマッピングをメモリキャッシュ
- Redis + ローカルキャッシュの2層構造

#### 5. 監視指標 / Metrics

- **レイテンシ**: Webhook受信からメッセージ送信までの時間
- **成功率**: 送信成功 / 総送信試行
- **エラー率**: エラー発生頻度
- **レート制限ヒット**: 429エラーの発生回数

---

## 制限事項と課題 / Limitations and Challenges

### 技術的制限 / Technical Limitations

#### Chatwork側

⚠️ **レート制限が厳しい**
- メッセージ送信: 10リクエスト/10秒
- 全体: 300リクエスト/5分
- **対策**: キューイング、バッチ処理

⚠️ **Webhookリトライなし**
- 失敗時の再送信なし
- **対策**: 自前のリトライロジック、監視アラート

⚠️ **Webhook設定上限**
- 最大5個
- **影響**: 大規模展開時の制約

#### Lark側

⚠️ **ファイル添付未サポート（MCP制限）**
- テキストメッセージのみ同期可能
- **対策**: ファイルはリンクとして共有

⚠️ **Beta版機能（MCP）**
- API変更の可能性
- **対策**: バージョン固定、定期的な更新チェック

### 機能的制約 / Functional Constraints

#### メッセージタイプ

**サポート:**
- ✅ テキストメッセージ
- ✅ メンション（名前ベース）

**未サポート（初期バージョン）:**
- ❌ ファイル添付
- ❌ 画像・動画
- ❌ リアクション（絵文字）
- ❌ スレッド返信
- ❌ メッセージ編集の同期
- ❌ メッセージ削除の同期

#### スケーラビリティ

- 同時接続数の上限
- 大量メッセージ処理時のパフォーマンス低下
- **対策**: 水平スケーリング、ロードバランサー

### ビジネス上の考慮事項 / Business Considerations

#### コスト

- **インフラコスト**: サーバー、Redis、帯域幅
- **API利用料**: Lark/Chatworkの有料プランが必要な可能性
- **開発・メンテナンスコスト**

#### 法的・コンプライアンス

- **データ保管**: メッセージログの保管期間、場所
- **プライバシー**: ユーザー同意、GDPR/個人情報保護法対応
- **利用規約**: ChatworkとLarkの規約に違反しないか確認

---

## 次のステップ / Next Steps

### 即時対応 / Immediate Actions

1. **要件確認**
   - [ ] 対象ルーム（チャットルーム）の特定
   - [ ] ユーザー数、メッセージ量の見積もり
   - [ ] 優先機能の決定

2. **API アクセス準備**
   - [ ] Chatwork APIトークン取得
   - [ ] Lark App作成、認証設定
   - [ ] Webhook URLの準備（HTTPS必須）

3. **プロトタイプ開発**
   - [ ] 開発環境セットアップ
   - [ ] 単方向同期のPoC実装
   - [ ] 動作確認

### 中期計画 / Mid-term Plan

- フェーズ1-2の完了（約4週間）
- テスト環境でのパイロット運用
- フィードバック収集と改善

### 長期計画 / Long-term Plan

- 本番環境への展開
- 監視体制の確立
- 継続的な機能追加とメンテナンス

---

## 参考資料 / References

### Chatwork API
- [Chatwork API Webhook Documentation](https://developer.chatwork.com/docs/webhook)
- [Chatwork API Documentation PDF](https://download.chatwork.com/ChatWork_API_Documentation.pdf) (Updated: April 3, 2025)
- [Chatwork API Endpoints](https://developer.chatwork.com/docs/endpoints)

### Lark API
- [Lark Developer Platform](https://open.larksuite.com/)
- [Official Lark OpenAPI MCP](https://github.com/larksuite/lark-openapi-mcp)
- [Python SDK (lark-oapi)](https://pypi.org/project/lark-oapi/)
- [Lark MCP Server Deep Dive](https://skywork.ai/skypage/en/A-Deep-Dive-into-the-Lark-MCP-Server:-The-Ultimate-Guide-for-AI-Engineers/1971403697816989696)

### 技術参考
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/docs/)
- [HMAC Authentication](https://en.wikipedia.org/wiki/HMAC)

---

**作成者:** Claude (Anthropic)
**最終更新:** 2025年12月31日
