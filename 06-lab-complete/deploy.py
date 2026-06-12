"""
Production AI Agent — Single file deploy (Railway compatible)
All dependencies loaded from single Python file.
"""
import os
import time
import signal
import random
import logging
import json
from datetime import datetime, timezone
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ─── Config ─────────────────────────────────────────
from dataclasses import dataclass, field

@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-jwt-secret"))
    allowed_origins: list = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(","))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")))
    daily_budget_usd: float = field(default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "5.0")))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

settings = Settings()

# ─── Mock LLM ───────────────────────────────────────
MOCK_RESPONSES = {
    "default": [
        "Day la cau tra loi tu AI agent (mock). Trong production, day se la response tu OpenAI/Anthropic.",
        "Agent dang hoat dong tot! (mock response) Hoi them cau hoi di nhe.",
        "Toi la AI agent duoc deploy len cloud. Cau hoi cua ban da duoc nhan.",
    ],
    "docker": ["Container la cach dong goi app de chay o moi noi. Build once, run anywhere!"],
    "deploy": ["Deployment la qua trinh dua code tu may ban len server de nguoi khac dung duoc."],
    "health": ["Agent dang hoat dong binh thuong. All systems operational."],
}

def llm_ask(question: str, delay: float = 0.1) -> str:
    time.sleep(delay + random.uniform(0, 0.05))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])

# ─── Logging ────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0

# ─── Rate Limiter ───────────────────────────────────
_rate_windows = defaultdict(deque)

def check_rate_limit(key: str):
    now = time.time()
    window = _rate_windows[key]
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )
    window.append(now)

# ─── Cost Guard ─────────────────────────────────────
_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

def check_and_record_cost(input_tokens: int, output_tokens: int):
    global _daily_cost, _cost_reset_day
    today = time.strftime("%Y-%m-%d")
    if today != _cost_reset_day:
        _daily_cost = 0.0
        _cost_reset_day = today
    if _daily_cost >= settings.daily_budget_usd:
        raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    _daily_cost += cost

# ─── Auth ───────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key

# ─── Lifespan ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({"event": "startup", "app": settings.app_name}))
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))
    yield
    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─── App ───────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count
    start = time.time()
    _request_count += 1
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    duration = round((time.time() - start) * 1000, 1)
    logger.info(json.dumps({"event": "request", "method": request.method, "path": request.url.path, "status": response.status_code, "ms": duration}))
    return response

# ─── Models ─────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str

# ─── Endpoints ─────────────────────────────────────
@app.get("/")
def root():
    return {"app": settings.app_name, "version": settings.app_version, "endpoints": {"ask": "POST /ask (requires X-API-Key)", "health": "GET /health", "ready": "GET /ready"}}

@app.post("/ask", response_model=AskResponse)
async def ask_agent(body: AskRequest, _key: str = Depends(verify_api_key)):
    check_rate_limit(_key[:8])
    input_tokens = len(body.question.split()) * 2
    check_and_record_cost(input_tokens, 0)
    answer = llm_ask(body.question)
    output_tokens = len(answer.split()) * 2
    check_and_record_cost(0, output_tokens)
    return AskResponse(question=body.question, answer=answer, model=settings.llm_model, timestamp=datetime.now(timezone.utc).isoformat())

@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version, "uptime_seconds": round(time.time() - START_TIME, 1), "total_requests": _request_count}

@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}

@app.get("/metrics")
def metrics(_key: str = Depends(verify_api_key)):
    return {"uptime_seconds": round(time.time() - START_TIME, 1), "total_requests": _request_count, "daily_cost_usd": round(_daily_cost, 4), "daily_budget_usd": settings.daily_budget_usd}

# ─── Graceful Shutdown ─────────────────────────────
signal.signal(signal.SIGTERM, lambda s, f: logger.info(json.dumps({"event": "signal", "signum": s})))

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port, timeout_graceful_shutdown=30)
