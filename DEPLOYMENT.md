# Deployment Information

> **Student:** Bui Hoang Linh
> **Date:** 12/06/2026

---

## 1. Production Agent (FastAPI)

### Public URL
https://ai-agent-lab-production.up.railway.app

### Platform
Railway

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | App info |
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe |
| `/ask` | POST | Agent endpoint (requires X-API-Key) |
| `/metrics` | GET | Metrics (requires X-API-Key) |
| `/chat` | GET | Frontend chat UI |
| `/docs` | GET | Swagger docs |

### Test Commands

**Health Check:**
```bash
curl https://ai-agent-lab-production.up.railway.app/health
# Expected: {"status":"ok","version":"1.0.0","uptime_seconds":...}
```

**Root endpoint:**
```bash
curl https://ai-agent-lab-production.up.railway.app/
# Expected: {"app":"Day12 Production Agent","version":"1.0.0",...}
```

**Ask with authentication:**
```bash
curl -X POST https://ai-agent-lab-production.up.railway.app/ask \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
# Expected: {"question":"What is Docker?","answer":"...","model":"gpt-4o-mini"}
```

**Without authentication (should return 401):**
```bash
curl -X POST https://ai-agent-lab-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Expected: {"detail":"Invalid or missing API key..."}
```

**Rate limiting test (should return 429 after 20 requests):**
```bash
for i in {1..25}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://ai-agent-lab-production.up.railway.app/ask \
    -H "X-API-Key: secret-key-123" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test $i\"}"
done
```

### Environment Variables Set

| Variable | Value | Description |
|----------|-------|-------------|
| `PORT` | 8000 | Server port |
| `ENVIRONMENT` | production | Environment name |
| `APP_NAME` | Day12 Production Agent | App display name |
| `AGENT_API_KEY` | secret-key-123 | API authentication key |
| `JWT_SECRET` | my-jwt-secret-456 | JWT signing secret |
| `RATE_LIMIT_PER_MINUTE` | 20 | Max requests per minute |
| `DAILY_BUDGET_USD` | 5.0 | Daily cost budget |

---

## 2. Research Agent (Streamlit)

### Public URL
https://research-agent-production-e0a8.up.railway.app

### Platform
Railway

### Features
- Multi-provider support (OpenRouter, OpenAI, Anthropic, Gemini)
- Tool calling (search, fetch, summarize, etc.)
- Conversation history
- Transcript export

### Environment Variables Set

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `TAVILY_API_KEY` | Tavily search API key |
| `FIRECRAWL_API_KEY` | Firecrawl web scraping key |
| `RAPIDAPI_KEY` | RapidAPI key (Twitter, etc.) |
| `RAPIDAPI_TWITTER_HOST` | Twitter API host |
| `ARXIV_USER_AGENT` | arXiv API user agent |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |

---

## Screenshots

- Railway dashboard: https://railway.com/project/1818ddf0-6a78-4d90-a5a5-f5de3906d0e5
- Production Agent: https://ai-agent-lab-production.up.railway.app
- Research Agent: https://research-agent-production-e0a8.up.railway.app
