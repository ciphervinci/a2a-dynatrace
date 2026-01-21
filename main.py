"""
A2A Dynatrace Agent Server - Main Entry Point
ServiceNow A2A Compatible Version

This agent provides:
- Problem detection and root cause analysis
- Service topology and dependency mapping
- Performance metrics analysis
- Deployment correlation
- AI-powered recommendations for SRE/Ops workflows
"""
import os
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import DynatraceAgentExecutor
from dynatrace_agent import DynatraceAgent

load_dotenv()

# Optional API Key for authentication
API_KEY = os.getenv("A2A_API_KEY", "")


def get_agent_card(host: str, port: int) -> AgentCard:
    """Create the Agent Card for the Dynatrace Agent."""
    
    # Skill 1: List Problems
    list_problems_skill = AgentSkill(
        id="list_problems",
        name="List Problems",
        description="List active problems and alerts from Dynatrace with filtering by status, severity, and time range.",
        tags=["problems", "alerts", "incidents", "monitoring"],
        examples=[
            "Show me open problems",
            "List critical alerts from last 24 hours",
            "Any performance issues today?",
        ],
    )
    
    # Skill 2: Analyze Problem
    analyze_problem_skill = AgentSkill(
        id="analyze_problem",
        name="Analyze Problem",
        description="Get detailed analysis of a specific problem including evidence, affected entities, and AI insights.",
        tags=["analysis", "investigation", "troubleshooting"],
        examples=[
            "Analyze problem P-12345",
            "Investigate P-12345",
            "What's wrong with P-12345?",
        ],
    )
    
    # Skill 3: Root Cause Analysis
    rca_skill = AgentSkill(
        id="root_cause_analysis",
        name="Root Cause Analysis",
        description="AI-powered root cause analysis correlating problems with deployments, metrics, and topology.",
        tags=["rca", "root-cause", "ai", "investigation"],
        examples=[
            "Root cause analysis for P-12345",
            "Why is the service slow?",
            "What caused the database latency?",
        ],
    )
    
    # Skill 4: Get Topology
    topology_skill = AgentSkill(
        id="get_topology",
        name="Service Topology",
        description="Get service topology, dependencies, and entity relationships from Dynatrace Smartscape.",
        tags=["topology", "smartscape", "dependencies", "architecture"],
        examples=[
            "Show service topology",
            "List all hosts",
            "Service dependencies for payment-service",
        ],
    )
    
    # Skill 5: Query Metrics
    metrics_skill = AgentSkill(
        id="query_metrics",
        name="Query Metrics",
        description="Query performance metrics including CPU, memory, response time, error rates, and throughput.",
        tags=["metrics", "performance", "monitoring", "data"],
        examples=[
            "Show CPU usage for last 2 hours",
            "Memory metrics for production hosts",
            "Response time performance",
        ],
    )
    
    # Skill 6: Get Deployments
    deployments_skill = AgentSkill(
        id="get_deployments",
        name="Recent Deployments",
        description="Get recent deployments and releases for correlation with problems and performance changes.",
        tags=["deployments", "releases", "changes", "cicd"],
        examples=[
            "Recent deployments",
            "What was deployed this week?",
            "Show releases for payment-service",
        ],
    )
    
    # Skill 7: Health Summary
    health_skill = AgentSkill(
        id="health_summary",
        name="Health Summary",
        description="Get comprehensive health summary of the monitored environment with AI insights.",
        tags=["health", "status", "overview", "dashboard"],
        examples=[
            "Environment health status",
            "Give me an overview",
            "How's production looking?",
        ],
    )
    
    # Skill 8: Natural Language Query
    query_skill = AgentSkill(
        id="query",
        name="Natural Language Query",
        description="Ask any question about your Dynatrace monitoring data in natural language.",
        tags=["question", "natural-language", "ai", "ask"],
        examples=[
            "Is there anything I should worry about?",
            "What's happening with production?",
            "Should I be concerned about the database?",
        ],
    )
    
    # Agent capabilities
    capabilities = AgentCapabilities(
        streaming=False,
        pushNotifications=False,
    )
    
    # Determine URL
    host_url = os.getenv("HOST_URL")
    if host_url:
        url = host_url.rstrip("/") + "/"
    else:
        url = f"http://{host}:{port}/"
    
    # Create Agent Card
    agent_card = AgentCard(
        name="Dynatrace AI Agent",
        description="AI-powered observability agent for SRE/Ops workflows. "
                    "Provides problem detection, root cause analysis, service topology, "
                    "performance metrics, and deployment correlation from Dynatrace. "
                    "Powered by Dynatrace API and Gemini AI.",
        url=url,
        version="1.0.0",
        defaultInputModes=DynatraceAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=DynatraceAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[
            list_problems_skill,
            analyze_problem_skill,
            rca_skill,
            topology_skill,
            metrics_skill,
            deployments_skill,
            health_skill,
            query_skill,
        ],
    )
    
    return agent_card


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "a2a-dynatrace-agent",
        "version": "1.0.0"
    })


def create_app(host: str = "0.0.0.0", port: int = 8000):
    """Create and configure the A2A Starlette application."""
    
    agent_executor = DynatraceAgentExecutor()
    agent_card = get_agent_card(host, port)
    
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    base_app = a2a_app.build()
    
    # Additional routes
    additional_routes = [
        Route("/health", health_check, methods=["GET"]),
        Route("/healthz", health_check, methods=["GET"]),
    ]
    
    # CORS middleware for ServiceNow
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "x-sn-apikey",
                "x-api-key",
                "Accept",
                "Origin",
                "X-Requested-With",
            ],
            expose_headers=["*"],
            max_age=3600,
        )
    ]
    
    all_routes = list(base_app.routes) + additional_routes
    
    app = Starlette(
        routes=all_routes,
        middleware=middleware,
    )
    
    return app


def validate_environment():
    """Validate required environment variables."""
    required_vars = [
        ("DYNATRACE_URL", "Dynatrace environment URL (e.g., https://xyz.live.dynatrace.com)"),
        ("DYNATRACE_API_TOKEN", "Dynatrace API token with required scopes"),
        ("GEMINI_API_KEY", "Google Gemini API key for AI features"),
    ]
    
    optional_vars = [
        ("A2A_API_KEY", "API key for authenticating A2A requests"),
        ("HOST_URL", "Public URL of the service"),
    ]
    
    missing = []
    for var, description in required_vars:
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")
    
    if missing:
        print("❌ Missing required environment variables:")
        print("\n".join(missing))
        print("\nSee .env.example for configuration details.")
        return False
    
    print("\n📝 Configuration:")
    for var, description in required_vars:
        value = os.getenv(var)
        if "KEY" in var or "TOKEN" in var:
            print(f"  ✓ {var}: configured (hidden)")
        else:
            # Mask URL partially
            if "URL" in var and value:
                masked = value[:20] + "..." if len(value) > 20 else value
                print(f"  ✓ {var}: {masked}")
            else:
                print(f"  ✓ {var}: {value}")
    
    for var, description in optional_vars:
        value = os.getenv(var)
        if value:
            if "KEY" in var:
                print(f"  ✓ {var}: configured (hidden)")
            else:
                print(f"  ✓ {var}: {value}")
        else:
            print(f"  - {var}: not set")
    
    return True


def main():
    """Main entry point for the server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="A2A Dynatrace Agent Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", 8000)),
        help="Port to listen on"
    )
    
    args = parser.parse_args()
    
    if not validate_environment():
        exit(1)
    
    host_url = os.getenv("HOST_URL", f"http://{args.host}:{args.port}")
    
    print("\n" + "=" * 60)
    print("🔍 Dynatrace A2A Agent - ServiceNow Compatible")
    print("=" * 60)
    print(f"📍 Server: http://{args.host}:{args.port}")
    print(f"🌐 Public URL: {host_url}")
    print(f"📋 Agent Card: {host_url}/.well-known/agent.json")
    print(f"❤️  Health Check: {host_url}/health")
    print("=" * 60)
    
    print("\n📖 ServiceNow Configuration:")
    print(f"   Agent Card URL: {host_url}/.well-known/agent.json")
    print(f"   Agent Execution URL: {host_url}/")
    if API_KEY:
        print(f"   Authentication: API Key (x-sn-apikey header)")
    else:
        print(f"   Authentication: None (add A2A_API_KEY to enable)")
    print("=" * 60)
    print("\n🚀 Starting server...\n")
    
    app = create_app(args.host, args.port)
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        timeout_keep_alive=120,
    )


if __name__ == "__main__":
    main()
