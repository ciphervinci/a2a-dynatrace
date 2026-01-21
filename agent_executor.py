"""
Agent Executor - Bridges the Dynatrace Agent with the A2A Protocol

This executor:
1. Receives A2A protocol messages
2. Parses user intent to determine observability query type
3. Routes to appropriate Dynatrace agent skills
4. Returns formatted responses
"""
import re
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from dynatrace_agent import DynatraceAgent


class DynatraceAgentExecutor(AgentExecutor):
    """
    A2A Agent Executor for the Dynatrace AI Agent.
    
    Routes incoming A2A messages to appropriate Dynatrace agent skills:
    - list_problems: List problems from Dynatrace
    - analyze_problem: Detailed problem analysis
    - get_topology: Service topology and dependencies
    - query_metrics: Performance metrics
    - get_deployments: Recent releases/deployments
    - root_cause_analysis: AI-powered RCA
    - health_summary: Environment health overview
    - query: Natural language questions
    """
    
    def __init__(self):
        self.agent = DynatraceAgent()
    
    def _extract_query(self, context: RequestContext) -> str:
        """Extract the user's text message from the A2A request."""
        try:
            user_input = context.get_user_input()
            if user_input:
                return user_input
        except Exception:
            pass
        
        try:
            if context.message and context.message.parts:
                for part in context.message.parts:
                    if hasattr(part, 'text') and part.text:
                        return part.text
        except Exception:
            pass
        
        try:
            if context.request and context.request.message:
                msg = context.request.message
                if hasattr(msg, 'parts') and msg.parts:
                    for part in msg.parts:
                        if hasattr(part, 'text') and part.text:
                            return part.text
        except Exception:
            pass
        
        return ""
    
    def _extract_problem_id(self, query: str) -> str | None:
        """Extract problem ID from query."""
        # Match patterns like P-12345, P-123456789, or full problem IDs
        patterns = [
            r'\b(P-\d+)\b',
            r'\bproblem\s+(?:id\s+)?[#]?(\d+)\b',
            r'\b([A-Z0-9_-]+_\d+V\d+)\b',  # Full problem ID format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_time_range(self, query: str) -> str:
        """Extract time range from query."""
        patterns = [
            (r'last\s+(\d+)\s*h(?:our)?s?', lambda m: f"{m.group(1)}h"),
            (r'last\s+(\d+)\s*d(?:ay)?s?', lambda m: f"{m.group(1)}d"),
            (r'last\s+(\d+)\s*w(?:eek)?s?', lambda m: f"{int(m.group(1))*7}d"),
            (r'past\s+(\d+)\s*h(?:our)?s?', lambda m: f"{m.group(1)}h"),
            (r'past\s+(\d+)\s*d(?:ay)?s?', lambda m: f"{m.group(1)}d"),
            (r'(\d+)\s*h(?:our)?s?\s+ago', lambda m: f"{m.group(1)}h"),
            (r'(\d+)\s*d(?:ay)?s?\s+ago', lambda m: f"{m.group(1)}d"),
            (r'today', lambda m: "24h"),
            (r'this\s+week', lambda m: "7d"),
        ]
        
        for pattern, formatter in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return formatter(match)
        
        return "24h"  # Default
    
    def _extract_entity_type(self, query: str) -> str | None:
        """Extract entity type from query."""
        entity_mappings = {
            'service': 'SERVICE',
            'services': 'SERVICE',
            'host': 'HOST',
            'hosts': 'HOST',
            'server': 'HOST',
            'servers': 'HOST',
            'process': 'PROCESS_GROUP',
            'processes': 'PROCESS_GROUP',
            'application': 'APPLICATION',
            'applications': 'APPLICATION',
            'database': 'DATABASE',
            'databases': 'DATABASE',
        }
        
        query_lower = query.lower()
        for keyword, entity_type in entity_mappings.items():
            if keyword in query_lower:
                return entity_type
        
        return None
    
    def _extract_metric_type(self, query: str) -> str | None:
        """Extract metric type from query."""
        metric_mappings = {
            'cpu': 'cpu',
            'processor': 'cpu',
            'memory': 'memory',
            'ram': 'memory',
            'disk': 'disk',
            'storage': 'disk',
            'response time': 'response_time',
            'latency': 'response_time',
            'error rate': 'error_rate',
            'errors': 'error_rate',
            'throughput': 'throughput',
            'requests': 'throughput',
            'availability': 'availability',
            'uptime': 'availability',
            'network': 'network',
            'traffic': 'network',
        }
        
        query_lower = query.lower()
        for keyword, metric in metric_mappings.items():
            if keyword in query_lower:
                return metric
        
        return None
    
    def _parse_intent(self, query: str) -> tuple[str, dict]:
        """
        Parse user query to determine which skill to invoke.
        
        Returns:
            tuple: (skill_name, parameters)
        """
        query_lower = query.lower().strip()
        
        # =====================================================================
        # Intent: Analyze Specific Problem
        # Examples: "analyze problem P-12345", "what's wrong with P-12345"
        # =====================================================================
        problem_id = self._extract_problem_id(query)
        if problem_id and any(word in query_lower for word in ['analyze', 'detail', 'investigate', 'what', 'explain', 'tell me about']):
            return ("analyze_problem", {"problem_id": problem_id})
        
        # =====================================================================
        # Intent: Root Cause Analysis
        # Examples: "root cause analysis", "why is the service slow", "RCA"
        # =====================================================================
        if any(phrase in query_lower for phrase in ['root cause', 'rca', 'why is', 'what caused', 'investigate']):
            problem_id = self._extract_problem_id(query)
            symptoms = query if not problem_id else None
            return ("root_cause_analysis", {"problem_id": problem_id, "symptoms": symptoms})
        
        # =====================================================================
        # Intent: List Problems
        # Examples: "show me problems", "list open alerts", "any issues"
        # =====================================================================
        if any(word in query_lower for word in ['problem', 'problems', 'alert', 'alerts', 'issue', 'issues', 'incident']):
            status = "OPEN" if 'open' in query_lower else ("CLOSED" if 'closed' in query_lower else None)
            
            severity = None
            if 'critical' in query_lower or 'availability' in query_lower:
                severity = "AVAILABILITY"
            elif 'error' in query_lower:
                severity = "ERROR"
            elif 'performance' in query_lower or 'slow' in query_lower:
                severity = "PERFORMANCE"
            
            time_range = self._extract_time_range(query)
            
            return ("list_problems", {"status": status, "severity": severity, "time_range": time_range})
        
        # =====================================================================
        # Intent: Get Topology
        # Examples: "show service topology", "list all hosts", "dependencies"
        # =====================================================================
        if any(word in query_lower for word in ['topology', 'dependencies', 'architecture', 'map']):
            entity_type = self._extract_entity_type(query) or "SERVICE"
            return ("get_topology", {"entity_type": entity_type})
        
        if any(phrase in query_lower for phrase in ['list services', 'show services', 'all services', 'list hosts', 'show hosts', 'all hosts']):
            entity_type = self._extract_entity_type(query) or "SERVICE"
            return ("get_topology", {"entity_type": entity_type})
        
        # =====================================================================
        # Intent: Query Metrics
        # Examples: "show cpu usage", "what's the memory", "response time metrics"
        # =====================================================================
        metric_type = self._extract_metric_type(query)
        if metric_type or any(word in query_lower for word in ['metric', 'metrics', 'performance', 'usage']):
            entity_type = self._extract_entity_type(query)
            time_range = self._extract_time_range(query)
            return ("query_metrics", {
                "metric": metric_type or "cpu",
                "entity_type": entity_type,
                "time_range": time_range
            })
        
        # =====================================================================
        # Intent: Get Deployments
        # Examples: "recent deployments", "show releases", "what was deployed"
        # =====================================================================
        if any(word in query_lower for word in ['deploy', 'deployment', 'deployments', 'release', 'releases', 'change', 'changes']):
            time_range = self._extract_time_range(query)
            return ("get_deployments", {"time_range": time_range})
        
        # =====================================================================
        # Intent: Health Summary
        # Examples: "health check", "environment status", "how's everything"
        # =====================================================================
        if any(phrase in query_lower for phrase in ['health', 'status', 'overview', 'summary', 'how is', "how's", 'dashboard']):
            return ("health_summary", {})
        
        # =====================================================================
        # Default: Natural Language Query
        # =====================================================================
        return ("query", {"question": query})
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle incoming A2A requests."""
        query = self._extract_query(context)
        
        print(f"[DEBUG] Extracted query: '{query}'")
        
        if not query or query.strip() == "":
            response = self._get_help_message()
            await event_queue.enqueue_event(new_agent_text_message(response))
            return
        
        skill, params = self._parse_intent(query)
        
        print(f"[DEBUG] Parsed intent: {skill}, params: {params}")
        
        try:
            if skill == "list_problems":
                response = await self.agent.list_problems(
                    status=params.get("status"),
                    severity=params.get("severity"),
                    time_range=params.get("time_range", "24h")
                )
            
            elif skill == "analyze_problem":
                response = await self.agent.analyze_problem(
                    problem_id=params["problem_id"]
                )
            
            elif skill == "get_topology":
                response = await self.agent.get_topology(
                    entity_type=params.get("entity_type", "SERVICE"),
                    tag=params.get("tag"),
                    name_filter=params.get("name_filter")
                )
            
            elif skill == "query_metrics":
                response = await self.agent.query_metrics(
                    metric=params.get("metric", "cpu"),
                    entity_type=params.get("entity_type"),
                    entity_id=params.get("entity_id"),
                    time_range=params.get("time_range", "2h")
                )
            
            elif skill == "get_deployments":
                response = await self.agent.get_deployments(
                    time_range=params.get("time_range", "7d"),
                    entity_filter=params.get("entity_filter")
                )
            
            elif skill == "root_cause_analysis":
                response = await self.agent.root_cause_analysis(
                    problem_id=params.get("problem_id"),
                    symptoms=params.get("symptoms")
                )
            
            elif skill == "health_summary":
                response = await self.agent.get_health_summary()
            
            else:  # query (natural language)
                response = await self.agent.query(
                    question=params.get("question", query)
                )
        
        except Exception as e:
            response = f"❌ Error: {str(e)}"
        
        await event_queue.enqueue_event(new_agent_text_message(response))
    
    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle cancellation requests."""
        await event_queue.enqueue_event(
            new_agent_text_message("Task cancelled.")
        )
    
    def _get_help_message(self) -> str:
        """Return help message explaining available capabilities."""
        return """# 🔍 Dynatrace AI Agent

I'm your AI-powered observability assistant! I help SREs and Ops engineers analyze Dynatrace monitoring data.

## 📋 Available Commands

### 🔴 Problems & Alerts
- "Show me open problems"
- "List critical alerts from last 24 hours"
- "Any performance issues today?"

### 🔬 Problem Analysis
- "Analyze problem P-12345"
- "Investigate P-12345"
- "What's wrong with P-12345?"

### 🔍 Root Cause Analysis
- "Root cause analysis for P-12345"
- "Why is the service slow?"
- "What caused the outage?"

### 🗺️ Topology & Dependencies
- "Show service topology"
- "List all hosts"
- "Service dependencies"

### 📊 Metrics
- "Show CPU usage"
- "Memory metrics for last 2 hours"
- "Response time performance"

### 🚀 Deployments
- "Recent deployments"
- "What was deployed this week?"
- "Show releases"

### ❤️ Health Summary
- "Environment health status"
- "Give me an overview"
- "How's everything looking?"

### 💬 Natural Language
- "Is there anything I should worry about?"
- "What's happening with production?"

---
**Tip:** I can correlate problems with deployments and provide AI-powered root cause analysis!
"""
