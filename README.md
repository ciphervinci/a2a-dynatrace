# 🔍 A2A Dynatrace AI Agent

An [A2A Protocol](https://a2a-protocol.org/) compliant observability agent that integrates **Dynatrace** with **ServiceNow AI Agent Studio** for intelligent SRE/Ops workflows.

![A2A Protocol](https://img.shields.io/badge/A2A-v0.3-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🎯 Use Case: Intelligent Incident Response

This agent enables the following SRE workflow:

```
┌─────────────────────┐                    ┌─────────────────────┐
│   Dynatrace         │                    │   ServiceNow        │
│   Davis AI          │                    │   AI Agent Studio   │
│   detects problem   │                    │                     │
└────────┬────────────┘                    └──────────┬──────────┘
         │                                            │
         │ 1. Alert: DB latency spike                 │
         ▼                                            │
┌─────────────────────────────────────────────────────┴──────────┐
│                    A2A Protocol (JSON-RPC 2.0)                 │
└─────────────────────────────────────────────────────┬──────────┘
                                                      │
         ┌────────────────────────────────────────────┴──────────┐
         │                                                       │
         ▼                                                       ▼
┌─────────────────────┐                    ┌─────────────────────┐
│   Dynatrace A2A     │ ◄─── 2. Query ─── │   IT Root-Cause     │
│   Agent (This!)     │ ─── 3. Data ────► │   Agent             │
│                     │                    │                     │
│ • Problem details   │                    │ • Correlate logs    │
│ • Service topology  │                    │ • Check deployments │
│ • Metrics data      │                    │ • Analyze changes   │
│ • Recent deploys    │                    │                     │
└─────────────────────┘                    └──────────┬──────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────────┐
                                           │  "Root cause likely │
                                           │   a DB index change │
                                           │   on 2026-01-17.    │
                                           │   Suggested: revert │
                                           │   + monitor"        │
                                           └─────────────────────┘
```

## 🎯 Features (A2A Skills)

| Skill | Description | Example Query |
|-------|-------------|---------------|
| **List Problems** | Get active problems and alerts | `"Show open problems"` |
| **Analyze Problem** | Deep-dive into specific problem | `"Analyze P-12345"` |
| **Root Cause Analysis** | AI-powered RCA with correlation | `"Why is the service slow?"` |
| **Service Topology** | Smartscape topology and dependencies | `"Show service topology"` |
| **Query Metrics** | Performance metrics (CPU, memory, etc.) | `"CPU usage last 2 hours"` |
| **Get Deployments** | Recent releases for correlation | `"Recent deployments"` |
| **Health Summary** | Environment overview with AI insights | `"Environment status"` |
| **Natural Language** | Ask anything about your environment | `"Anything I should worry about?"` |

## 🚀 Quick Start

### 1. Get API Keys

**Dynatrace API Token:**
1. Go to Dynatrace → Access Tokens
2. Generate a token with these scopes:
   - `problems.read` - Read problems
   - `entities.read` - Read monitored entities
   - `metrics.read` - Read metrics
   - `events.read` - Read events (optional)
   - `releases.read` - Read deployments (optional)

**Google Gemini API Key:**
1. Go to [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. Create a new API key

### 2. Clone & Setup

```bash
git clone <your-repo-url>
cd a2a-dynatrace-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
DYNATRACE_URL=https://xyz12345.live.dynatrace.com
DYNATRACE_API_TOKEN=dt0c01.xxxx.yyyy
GEMINI_API_KEY=your_gemini_key

# For production deployment
HOST_URL=https://your-service.onrender.com
```

### 4. Run Locally

```bash
python main.py
```

### 5. Test

```bash
python test_client.py

# Or curl
curl http://localhost:8000/.well-known/agent.json
```

## ☁️ Deploy to Render

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git push -u origin main
```

### Step 2: Create Render Service

1. Go to [render.com](https://render.com)
2. **New** → **Web Service** → Connect repo
3. Configure:
   - **Name:** `a2a-dynatrace-agent`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`

### Step 3: Add Environment Variables

| Variable | Value | Required |
|----------|-------|----------|
| `DYNATRACE_URL` | Your Dynatrace URL | ✅ Yes |
| `DYNATRACE_API_TOKEN` | Your API token | ✅ Yes |
| `GEMINI_API_KEY` | Your Gemini key | ✅ Yes |
| `HOST_URL` | `https://your-service.onrender.com` | ✅ Yes |
| `A2A_API_KEY` | Your secure API key | Optional |

> ⚠️ **CRITICAL:** Set `HOST_URL` to your public Render URL!

### Step 4: Verify

```bash
curl https://your-service.onrender.com/.well-known/agent.json
```

## 🔗 ServiceNow Integration

### Prerequisites

- ServiceNow **Zurich Patch 4+** or **Yokohama Patch 11+**
- **Now Assist AI Agents 6.0.x+**
- Now Assist SKU (Pro Plus or Enterprise Plus)

### Configuration Steps

1. **Enable External Agents** in AI Agent Studio → Settings

2. **Create Connection Alias:**
   - IntegrationHub → Connections & Credential Aliases
   - Connection URL: `https://your-service.onrender.com`

3. **Add External Agent:**
   - AI Agent Studio → AI agents → Add → External
   - Select **Agent2Agent (A2A) Protocol**
   - Agent Card URL: `https://your-service.onrender.com/.well-known/agent.json`

## 📡 API Reference

### Dynatrace API Token Scopes

| Scope | Required | Description |
|-------|----------|-------------|
| `problems.read` | ✅ | List and view problems |
| `entities.read` | ✅ | Query Smartscape topology |
| `metrics.read` | ✅ | Query performance metrics |
| `events.read` | Optional | List events |
| `releases.read` | Optional | List deployments |

### A2A Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/agent.json` | GET | Agent Card |
| `/` | POST | Message endpoint |
| `/health` | GET | Health check |

### Example Request

```bash
curl -X POST https://your-service.onrender.com/ \
  -H "Content-Type: application/json" \
  -H "x-sn-apikey: your-api-key" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Show open problems"}],
        "messageId": "msg-1"
      }
    }
  }'
```

## 📁 Project Structure

```
a2a-dynatrace-agent/
├── main.py                 # A2A server entry point
├── dynatrace_client.py     # Dynatrace API v2 client
├── dynatrace_agent.py      # AI-powered agent with skills
├── agent_executor.py       # A2A protocol request handler
├── test_client.py          # Test client
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container configuration
├── render.yaml             # Render deployment config
├── .env.example            # Environment template
└── README.md               # This file
```

## 🔧 Troubleshooting

### 503 Network Error

**Cause:** Agent Card returns internal URL

**Fix:** Set `HOST_URL` environment variable to your public URL

### 401 Unauthorized from Dynatrace

**Cause:** Invalid or expired API token

**Fix:** Generate a new token with required scopes

### Cold Start Timeout (Free Tier)

**Cause:** Render free tier spins down after 15 min

**Fix:** Set up keep-alive ping or upgrade to Starter plan

## 🤝 Multi-Agent Collaboration

This agent is designed to work with other A2A agents:

- **ServiceNow IT Root-Cause Agent** - Correlates data across sources
- **Log Analysis Agent** - Deep-dives into application logs
- **CI/CD Agent** - Provides deployment pipeline context
- **CMDB Agent** - Configuration and change information

## 📚 Resources

- [A2A Protocol Documentation](https://a2a-protocol.org/latest/)
- [ServiceNow A2A Integration](https://www.servicenow.com/community/now-assist-articles/enable-mcp-and-a2a-for-your-agentic-workflows-with-faqs-updated/ta-p/3373907)
- [Dynatrace API v2](https://docs.dynatrace.com/docs/discover-dynatrace/references/dynatrace-api)
- [Dynatrace Problems API](https://docs.dynatrace.com/docs/discover-dynatrace/references/dynatrace-api/environment-api/problems-v2)

## 📄 License

MIT License

---

**Built for SRE/Ops teams who want intelligent, automated incident response! 🚀**
