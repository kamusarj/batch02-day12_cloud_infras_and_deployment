# Day 12 Lab - Mission Answers

> **Student:** Bui Hoang Linh
> **Date:** 12/06/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `develop/app.py`

1. **API key hardcode** - `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` - Lộ secret nếu push lên GitHub
2. **Database URL hardcode** - `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"` - Password trong code
3. **Debug mode bật cứng** - `DEBUG = True` - Không nên bật trong production
4. **Không có health check** - Platform không biết container có sống không để restart
5. **Port cố định** - `port=8000` - Railway/Render inject PORT qua env var
6. **Host chỉ localhost** - `host="localhost"` - Không nhận kết nối từ bên ngoài container
7. **Print secrets ra log** - `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` - Lộ key trong log
8. **Debug reload trong production** - `reload=True` - Tốn tài nguyên, không an toàn
9. **Không xử lý shutdown** - Không có signal handler cho SIGTERM
10. **Không có structured logging** - Dùng `print()` thay vì JSON logging

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| Config | Hardcode | Env vars | Bảo mật, linh hoạt giữa env |
| Secrets | Trong code | Env vars / .env | Không lộ khi push code |
| Port | Cố định 8000 | Từ PORT env var | Cloud platform inject tự động |
| Host | localhost | 0.0.0.0 | Container cần accept từ bên ngoài |
| Health check | Không có | GET /health, GET /ready | Platform monitor và restart |
| Logging | print() | JSON structured | Dễ parse, aggregate, alert |
| Shutdown | Đột ngột | Graceful (SIGTERM) | Hoàn thành request trước khi tắt |
| Debug mode | True | False (env-based) | An toàn, nhanh hơn |
| CORS | Không có | Configured origins | Bảo mật API |
| Reload | True | Chỉ khi DEBUG=true | Performance, security |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image là gì?** - `python:3.11` (develop) / `python:3.11-slim` (production) - Slim nhỏ hơn, ít attack surface
2. **Working directory là gì?** - `/app` - Nơi chứa source code trong container
3. **Tại sao COPY requirements.txt trước?** - Docker layer cache. Nếu code thay đổi nhưng deps không đổi, Docker dùng lại layer đã cache, build nhanh hơn
4. **CMD vs ENTRYPOINT?** - CMD là default command (có thể override), ENTRYPOINT là executable chính (không override dễ dàng)

### Exercise 2.3: Image size comparison

- **Develop (single-stage):** ~800-1000 MB (python:3.11 full)
- **Production (multi-stage):** ~150-200 MB (python:3.11-slim, chỉ copy runtime)
- **Difference:** Giảm ~75-80% kích thước

**Tại sao nhỏ hơn?**
- Stage 1 (builder): Có gcc, pip, build tools để compile dependencies
- Stage 2 (runtime): Chỉ copy site-packages, không có build tools
- Non-root user: Không chạy với root
- HEALTHCHECK: Docker tự restart nếu fail

### Exercise 2.4: Docker Compose stack

**Services:**
1. **agent** - FastAPI AI agent (2-3 replicas)
2. **redis** - Cache cho session và rate limiting
3. **nginx** - Reverse proxy, load balancer

**Communication:**
- Nginx (port 80) → agent (port 8000) qua internal network
- Agent → Redis (port 6379) qua internal network
- Docker DNS tự resolve tên service

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://ai-agent-lab-production.up.railway.app
- **Platform:** Railway
- **Build:** Nixpacks (auto-detect Python)
- **Start command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`

**Test results:**
```bash
# Health check
$ curl https://ai-agent-lab-production.up.railway.app/health
{"status":"ok","uptime_seconds":29.6,"platform":"Railway","timestamp":"2026-06-12T14:38:34Z"}

# Ask endpoint
$ curl -X POST https://ai-agent-lab-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
{"question":"Hello","answer":"...","platform":"Railway"}
```

### Exercise 3.2: render.yaml vs railway.toml

| | railway.toml | render.yaml |
|--|--------------|-------------|
| Format | TOML | YAML |
| Builder | NIXPACKS / DOCKERFILE | auto-detect |
| Start command | `startCommand` | `startCommand` |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Env vars | CLI / Dashboard | `envVars` trong YAML |
| Free tier | $5 credit | 750h/month |

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

**Flow:**
1. Client gửi header `X-API-Key: <key>`
2. Server verify key có match với `AGENT_API_KEY` trong env
3. Nếu sai → 401 Unauthorized
4. Nếu đúng → process request

**Test:**
```bash
# Không có key → 401
$ curl -X POST https://ai-agent-lab-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
{"detail":"Invalid or missing API key..."}

# Có key → 200
$ curl -X POST https://ai-agent-lab-production.up.railway.app/ask \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
{"question":"Hello","answer":"..."}
```

### Exercise 4.2: JWT authentication

**Flow:**
1. POST `/auth/token` với username/password → nhận JWT token
2. Gọi API với header `Authorization: Bearer <token>`
3. Server verify signature, check expiry
4. Extract user info (username, role) từ payload

**Advantages over API Key:**
- Token có expiry (auto-rotate)
- Chứa user info (role-based access)
- Không cần store token trên server (stateless)

### Exercise 4.3: Rate limiting

**Algorithm:** Sliding Window Counter
- Mỗi user có deque chứa timestamps
- Window: 60 giây
- Limit: 10 req/min (user), 100 req/min (admin)
- Vượt quá → 429 Too Many Requests với `Retry-After` header

**Test:**
```bash
# Gọi 15 lần liên tiếp
for i in {1..15}; do
  curl -H "X-API-Key: secret-key-123" -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "Test '$i'"}' \
    https://ai-agent-lab-production.up.railway.app/ask
done
# Sau 10 lần → 429 Rate limit exceeded
```

### Exercise 4.4: Cost guard implementation

**Approach:**
- Track daily spending per user
- GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output
- Budget: $1/user/day, $10 global/day
- Reset daily (theo ngày UTC)
- Warning khi dùng 80% budget
- Block khi vượt 100% (HTTP 402)

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

**Liveness probe (`/health`):**
- Trả 200 nếu process đang chạy
- Platform gọi định kỳ (30s)
- Non-200 → platform restart container

**Readiness probe (`/ready`):**
- Trả 200 nếu sẵn sàng nhận traffic
- Check dependencies (Redis, DB)
- 503 khi đang startup hoặc quá tải
- Load balancer dùng để quyết định route traffic

### Exercise 5.2: Graceful shutdown

**Flow:**
1. Platform gửi SIGTERM
2. Stop nhận request mới
3. Đợi in-flight requests hoàn thành (timeout 30s)
4. Đóng connections (Redis, DB)
5. Exit

**Test:**
```bash
python app.py &
PID=$!
curl http://localhost:8000/ask -X POST -d '{"question":"Long task"}' &
kill -TERM $PID
# Request hoàn thành trước khi tắt
```

### Exercise 5.3: Stateless design

**Anti-pattern (stateful):**
```python
conversation_history = {}  # Trong memory → mất khi restart
```

**Correct (stateless):**
```python
history = redis.lrange(f"history:{user_id}", 0, -1)  # Trong Redis
```

**Tại sao?** Khi scale lên 3 instances, mỗi instance có memory riêng. User gửi request 1 → instance 1, request 2 → instance 2. Nếu state trong memory, instance 2 không có history.

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
# 3 agent instances + Nginx load balancer
# Nginx round-robin giữa các instances
# Nếu 1 instance die → traffic sang instances khác
```

---

## Part 6: Final Project

### Deployment Information

**Research Agent (Streamlit):**
- URL: https://research-agent-production-e0a8.up.railway.app
- Platform: Railway
- Features: Tool calling, multi-provider (OpenRouter, Gemini, etc.)

**Production Agent (FastAPI):**
- URL: https://ai-agent-lab-production.up.railway.app
- Platform: Railway
- Features: API Key auth, rate limiting, cost guard, health checks

### Checklist

- [x] Agent trả lời câu hỏi qua REST API
- [x] Dockerized với multi-stage build
- [x] Config từ environment variables
- [x] API key authentication
- [x] Rate limiting (10-20 req/min per user)
- [x] Cost guard ($5-10/day per user)
- [x] Health check endpoint
- [x] Readiness check endpoint
- [x] Graceful shutdown
- [x] Structured JSON logging
- [x] Deploy lên Railway
- [x] Public URL hoạt động
