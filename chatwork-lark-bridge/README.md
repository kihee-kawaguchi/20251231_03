# Chatwork-Lark Bridge

Bidirectional message synchronization between Chatwork and Lark platforms.

## Features

- ✅ Real-time bidirectional message sync
- ✅ Loop detection and prevention
- ✅ Webhook signature verification
- ✅ Retry logic with exponential backoff
- ✅ Dead Letter Queue for failed messages
- ✅ Structured logging (JSON format)
- ✅ Health check endpoints
- ✅ Redis-based message tracking

## Architecture

```
Chatwork ⇄ Bridge Server ⇄ Lark
               ↓
            Redis
```

## Prerequisites

- Python 3.11+
- Redis 6.0+
- Chatwork API token
- Lark App credentials

## Quick Start

### 1. Clone and Setup

```bash
cd chatwork-lark-bridge
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
redis-server
```

### 4. Run Application

```bash
# Development
python -m src.main

# Or with uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify Health

```bash
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

See `.env.example` for all available options.

**Required:**
- `CHATWORK_API_TOKEN` - Your Chatwork API token
- `CHATWORK_WEBHOOK_SECRET` - Webhook signature verification secret
- `LARK_APP_ID` - Lark application ID
- `LARK_APP_SECRET` - Lark application secret
- `LARK_VERIFICATION_TOKEN` - Lark verification token

**Optional:**
- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379/0`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `MAX_RETRY_ATTEMPTS` - Maximum retry attempts (default: `5`)

## API Endpoints

### Health Checks

- `GET /health` - Overall health status
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Webhooks

- `POST /webhook/chatwork` - Chatwork webhook endpoint
- `POST /webhook/lark` - Lark event subscription endpoint

## Development

### Project Structure

```
chatwork-lark-bridge/
├── src/
│   ├── api/          # API endpoints
│   │   ├── chatwork.py
│   │   ├── lark.py
│   │   └── health.py
│   ├── core/         # Core functionality
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   └── retry.py
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   │   └── redis_client.py
│   ├── utils/        # Utilities
│   │   └── webhook_verification.py
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── config/           # Configuration files
├── logs/             # Log files
├── .env.example      # Environment template
├── requirements.txt  # Dependencies
└── README.md
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Sort imports
isort src/

# Lint
flake8 src/

# Type check
mypy src/
```

## Deployment

### Docker

```bash
# Build
docker build -t chatwork-lark-bridge .

# Run
docker run -d \
  --name chatwork-lark-bridge \
  -p 8000:8000 \
  --env-file .env \
  chatwork-lark-bridge
```

### Docker Compose

```bash
docker-compose up -d
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `http://localhost:9090/metrics` (if enabled).

**Key Metrics:**
- `message_sync_total` - Total messages synced
- `message_sync_failures` - Failed sync attempts
- `message_sync_latency_seconds` - Sync latency
- `webhook_requests_total` - Total webhook requests

### Logging

Logs are output in JSON format by default.

```json
{
  "timestamp": "2025-12-31T20:00:00Z",
  "level": "INFO",
  "event": "message_synced",
  "source_platform": "chatwork",
  "target_platform": "lark",
  "latency_ms": 234
}
```

## Troubleshooting

### Common Issues

**Redis Connection Failed**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

**Webhook Signature Verification Failed**
- Verify `CHATWORK_WEBHOOK_SECRET` is base64 encoded
- Check webhook secret in Chatwork API settings

**Messages Not Syncing**
- Check room mapping configuration
- Verify API tokens are valid
- Check logs for errors: `docker logs chatwork-lark-bridge`

## Contributing

1. Create feature branch
2. Make changes
3. Run tests: `pytest`
4. Submit pull request

## License

MIT

## Support

For issues and questions, please open a GitHub issue.

---

**Version:** 0.1.0 (Prototype)
**Status:** Development
