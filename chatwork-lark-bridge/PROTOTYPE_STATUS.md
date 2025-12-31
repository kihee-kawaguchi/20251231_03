# Chatwork-Lark Bridge - プロトタイプ実装状況
## Prototype Implementation Status

**作成日 / Date:** 2025年12月31日
**バージョン / Version:** 0.1.0-alpha
**ステータス / Status:** プロトタイプ基盤完成 / Prototype Foundation Complete

---

## ✅ 実装完了 / Completed

### 1. プロジェクト構造 / Project Structure

```
chatwork-lark-bridge/
├── src/
│   ├── api/
│   │   ├── chatwork.py      ✅ Webhook受信エンドポイント
│   │   ├── lark.py           ✅ Webhook受信エンドポイント
│   │   └── health.py         ✅ ヘルスチェック
│   ├── core/
│   │   ├── config.py         ✅ 環境変数管理
│   │   ├── logging.py        ✅ 構造化ログ
│   │   ├── exceptions.py     ✅ カスタム例外
│   │   └── retry.py          ✅ リトライロジック
│   ├── services/
│   │   └── redis_client.py   ✅ Redis接続・データモデル
│   ├── utils/
│   │   └── webhook_verification.py  ✅ 署名検証
│   └── main.py               ✅ FastAPIアプリケーション
├── requirements.txt          ✅ 依存関係定義
├── .env.example              ✅ 環境変数テンプレート
└── README.md                 ✅ セットアップガイド
```

### 2. コア機能 / Core Features

#### ✅ 環境設定管理
- Pydantic Settingsによる型安全な設定
- 環境変数からの自動読み込み
- 本番/開発環境の切り替え

#### ✅ エラーハンドリング
- カスタム例外階層（RetryableError / NonRetryableError）
- API エラー分類（429, 401, 500等）
- Webhook エラー
- メッセージ処理エラー
- Redis接続エラー

#### ✅ リトライメカニズム
- Tenacityを使用した指数バックオフ
- レート制限エラー専用ハンドリング
- 最大試行回数の設定可能化
- retry_after ヘッダー対応

#### ✅ Redis統合
- 非同期接続プール
- メッセージIDマッピング（ループ防止用）
- ルーム・ユーザーマッピングキャッシュ
- Dead Letter Queue (失敗メッセージ保存)
- レート制限カウンター
- ヘルスチェック

#### ✅ Webhook署名検証
- **Chatwork**: HMAC-SHA256 + Base64
- **Lark**: SHA256 + 検証トークン
- 定数時間比較（タイミング攻撃対策）

#### ✅ 構造化ロギング
- Structlogによる JSON/テキスト出力
- ログレベル設定可能
- コンテキスト情報の自動付与

#### ✅ ヘルスチェック
- `/health` - 全体の健全性
- `/health/ready` - Readiness Probe (K8s対応)
- `/health/live` - Liveness Probe (K8s対応)

---

## 🚧 次のステップ / Next Steps

### フェーズ2: メッセージ同期実装（2週間）

#### 優先度: 🔴 Critical

1. **Chatwork → Lark 単方向同期**
   - [ ] Chatwork Webhookイベント処理
     - message_created イベントのパース
     - ルームIDマッピング取得
     - メッセージ本文の抽出

   - [ ] ループ検出
     - メッセージプレフィックスチェック
     - Redis によるメッセージID追跡

   - [ ] Lark API統合
     - lark-oapi SDK初期化
     - アクセストークン取得・管理
     - メッセージ送信 (POST /im/v1/messages)

   - [ ] エラーハンドリング
     - レート制限対応（10秒待機）
     - リトライロジック適用
     - DLQへの失敗メッセージ保存

2. **ルーム・ユーザーマッピング管理**
   - [ ] PostgreSQL スキーマ作成
     - room_mappings テーブル
     - user_mappings テーブル
     - sync_config テーブル

   - [ ] SQLAlchemy モデル定義
   - [ ] CRUD API実装
   - [ ] Redis キャッシング統合

3. **テスト実装**
   - [ ] ユニットテスト
     - 署名検証ロジック
     - ループ検出アルゴリズム
     - メッセージフォーマット変換

   - [ ] 統合テスト
     - Chatwork Webhook → Lark送信
     - Redisデータ保存・取得

   - [ ] モックサーバー
     - Chatwork API モック
     - Lark API モック

---

## 📋 実装詳細 / Implementation Details

### エラーハンドリング戦略

```python
# 実装済み例
from src.core.exceptions import RateLimitError, RetryableError
from src.core.retry import retry_with_rate_limit_handling

async def send_message_to_lark(message):
    try:
        response = await lark_api.send_message(message)
        return response
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limit
            retry_after = int(e.response.headers.get('Retry-After', 60))
            raise RateLimitError(platform="lark", retry_after=retry_after)
        elif e.response.status_code >= 500:
            # Server error - retryable
            raise ServerError(f"Lark API error: {e}")
        else:
            # Client error - non-retryable
            raise BadRequestError(f"Invalid request: {e}")
```

### Redisデータスキーマ

```python
# メッセージマッピング (24時間 TTL)
msg:chatwork:{message_id} = {
    "source_platform": "chatwork",
    "source_message_id": "123456",
    "target_platform": "lark",
    "target_message_id": "om_abc123",
    "timestamp": "2025-12-31T20:00:00Z"
}

# ルームマッピング (1時間キャッシュ)
room:chatwork:{room_id} = "lark_chat_id"

# ユーザーマッピング (1時間キャッシュ)
user:chatwork:{user_id} = {
    "name": "山田太郎",
    "lark_user_id": "ou_abc123"
}

# 失敗メッセージ (7日間保存)
failed:{timestamp}:{platform}:{message_id} = {
    "source_platform": "chatwork",
    "target_platform": "lark",
    "message": {...},
    "error": "Rate limit exceeded",
    "retry_count": 5,
    "failed_at": "2025-12-31T20:00:00Z"
}
```

---

## 🛠️ セットアップ手順 / Setup Instructions

### 1. 環境構築

```bash
# リポジトリ内のディレクトリに移動
cd 20251231_03/chatwork-lark-bridge

# 仮想環境作成
python -m venv venv

# 仮想環境アクティベート
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### 2. 環境変数設定

```bash
# .envファイル作成
cp .env.example .env

# .envを編集（必須項目を設定）
# - CHATWORK_API_TOKEN
# - CHATWORK_WEBHOOK_SECRET
# - LARK_APP_ID
# - LARK_APP_SECRET
# - LARK_VERIFICATION_TOKEN
```

### 3. Redis起動

```bash
# Dockerを使用
docker run -d --name redis -p 6379:6379 redis:7-alpine

# またはローカルインストール
redis-server
```

### 4. アプリケーション起動

```bash
# 開発モード
python -m src.main

# または
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/health

# 期待される出力:
# {
#   "status": "healthy",
#   "redis": true,
#   "details": {"redis": "connected"}
# }
```

---

## 🧪 テスト方法 / Testing

### 現時点での手動テスト

#### 1. Webhook受信テスト（Chatwork）

```bash
# 署名生成（Python）
import base64, hmac, hashlib, json

secret = "YOUR_WEBHOOK_SECRET_BASE64"
body = json.dumps({"webhook_event_type": "message_created", "webhook_setting_id": "123"})

decoded_secret = base64.b64decode(secret)
digest = hmac.new(decoded_secret, body.encode(), hashlib.sha256).digest()
signature = base64.b64encode(digest).decode()

print(f"Signature: {signature}")
```

```bash
# curlでWebhook送信
curl -X POST http://localhost:8000/webhook/chatwork \
  -H "Content-Type: application/json" \
  -H "X-ChatWorkWebhookSignature: <SIGNATURE>" \
  -d '{"webhook_event_type":"message_created","webhook_setting_id":"123"}'
```

#### 2. Webhook受信テスト（Lark）

```bash
# URL検証チャレンジ
curl -X POST http://localhost:8000/webhook/lark \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url_verification",
    "token": "YOUR_VERIFICATION_TOKEN",
    "challenge": "test_challenge_string"
  }'

# 期待される出力:
# {"challenge": "test_challenge_string"}
```

---

## 📊 現在の制限事項 / Current Limitations

1. **メッセージ同期未実装**
   - Webhookは受信できるが、実際の転送処理は未実装
   - プレースホルダーのみ（`TODO`コメント）

2. **データベース未統合**
   - ルーム・ユーザーマッピングはハードコーディング必要
   - PostgreSQL スキーマ未作成

3. **テストスイート不足**
   - ユニットテスト未作成
   - 統合テスト未作成

4. **監視・メトリクス**
   - Prometheusメトリクス未実装
   - アラート未設定

5. **CI/CD**
   - パイプライン未構築
   - Dockerイメージ未作成

---

## 🎯 推奨: 次の開発フォーカス / Recommended Next Focus

### 最優先（今週中）

1. **Chatwork → Lark 単方向同期の完成**
   - Lark SDK統合
   - メッセージ送信処理
   - ループ検出の実装

2. **基本的なテストケース作成**
   - 署名検証テスト
   - Redis操作テスト
   - ループ検出テスト

3. **ルームマッピング設定**
   - 簡易的な設定ファイル（JSON/YAML）
   - 最低1ペアのマッピング

### 来週以降

4. **Lark → Chatwork 逆方向同期**
5. **PostgreSQL統合**
6. **Docker化**
7. **CI/CD構築**

---

## 📞 サポート / Support

**質問・問題がある場合:**
- 設計書: `CHATWORK_LARK_INTEGRATION_DESIGN.md`
- ギャップ分析: `DESIGN_REVIEW_GAPS.md`
- README: `README.md`

**次回レビュー:** 単方向同期実装完了後

---

**作成者:** Claude (Anthropic)
**最終更新:** 2025年12月31日 21:00 JST
