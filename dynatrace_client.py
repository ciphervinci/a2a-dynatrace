"""
Dynatrace API Client - Fetches data from Dynatrace Environment API v2

Supports:
- Problems API v2: List and get problem details
- Monitored Entities API v2: Query topology and entities
- Metrics API v2: Query metrics data
- Events API v2: List and ingest events
- Releases API: Deployment information
"""
import os
from datetime import datetime, timedelta
from typing import Any, Optional
import httpx


class DynatraceClient:
    """
    Client for Dynatrace Environment API v2.
    
    Required token scopes:
    - problems.read: Read problems
    - entities.read: Read monitored entities
    - metrics.read: Read metrics
    - events.read: Read events
    - releases.read: Read releases/deployments
    """
    
    def __init__(self):
        """Initialize the Dynatrace client with environment variables."""
        self.base_url = os.getenv("DYNATRACE_URL", "").rstrip("/")
        self.api_token = os.getenv("DYNATRACE_API_TOKEN", "")
        
        if not self.base_url:
            raise ValueError("DYNATRACE_URL environment variable is required")
        if not self.api_token:
            raise ValueError("DYNATRACE_API_TOKEN environment variable is required")
        
        # Ensure base URL has /api/v2
        if not self.base_url.endswith("/api/v2"):
            self.base_url = f"{self.base_url}/api/v2"
    
    def _get_headers(self) -> dict:
        """Get authorization headers."""
        return {
            "Authorization": f"Api-Token {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: dict = None,
        json_body: dict = None
    ) -> dict[str, Any]:
        """Make an async HTTP request to the Dynatrace API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                params=params,
                json=json_body
            )
            response.raise_for_status()
            return response.json()
    
    # =========================================================================
    # PROBLEMS API v2
    # =========================================================================
    
    async def get_problems(
        self,
        status: str = None,  # "OPEN", "CLOSED"
        severity: str = None,  # "AVAILABILITY", "ERROR", "PERFORMANCE", "RESOURCE_CONTENTION", "CUSTOM_ALERT"
        impact_level: str = None,  # "APPLICATION", "SERVICE", "INFRASTRUCTURE"
        entity_selector: str = None,
        from_time: str = "now-24h",
        to_time: str = "now",
        page_size: int = 50
    ) -> dict[str, Any]:
        """
        Get list of problems from Dynatrace.
        
        Args:
            status: Filter by problem status (OPEN, CLOSED)
            severity: Filter by severity level
            impact_level: Filter by impact level
            entity_selector: Filter by entity (e.g., type("HOST"), entityId("HOST-xxx"))
            from_time: Start time (relative like "now-24h" or absolute timestamp)
            to_time: End time
            page_size: Number of results per page (max 500)
            
        Returns:
            Dict with totalCount and list of problems
        """
        params = {
            "from": from_time,
            "to": to_time,
            "pageSize": page_size
        }
        
        # Build problem selector
        selectors = []
        if status:
            selectors.append(f'status("{status}")')
        if severity:
            selectors.append(f'severityLevel("{severity}")')
        if impact_level:
            selectors.append(f'impactLevel("{impact_level}")')
        
        if selectors:
            params["problemSelector"] = ",".join(selectors)
        
        if entity_selector:
            params["entitySelector"] = entity_selector
        
        return await self._make_request("GET", "/problems", params=params)
    
    async def get_problem_details(
        self,
        problem_id: str,
        fields: str = "+evidenceDetails,+impactAnalysis,+recentComments"
    ) -> dict[str, Any]:
        """
        Get detailed information about a specific problem.
        
        Args:
            problem_id: The problem ID - can be display ID (P-12345) or internal ID
            fields: Additional fields to include
            
        Returns:
            Problem details including root cause evidence
        """
        # Check if this is a display ID (P-XXXXXX format) - need to look it up first
        if problem_id.upper().startswith("P-"):
            # Search for the problem by display ID
            display_id = problem_id.upper()
            search_params = {
                "problemSelector": f'displayId("{display_id}")',
                "pageSize": 1,
                "from": "now-90d",  # Search last 90 days
            }
            
            search_result = await self._make_request("GET", "/problems", params=search_params)
            problems = search_result.get("problems", [])
            
            if not problems:
                raise ValueError(f"Problem {display_id} not found")
            
            # Get the internal problem ID
            internal_id = problems[0].get("problemId")
            if not internal_id:
                raise ValueError(f"Could not resolve internal ID for {display_id}")
            
            problem_id = internal_id
        
        # Now fetch the full details using the internal ID
        params = {"fields": fields} if fields else {}
        return await self._make_request("GET", f"/problems/{problem_id}", params=params)
    
    # =========================================================================
    # MONITORED ENTITIES API v2
    # =========================================================================
    
    async def get_entities(
        self,
        entity_selector: str,
        fields: str = None,
        from_time: str = "now-2h",
        page_size: int = 50
    ) -> dict[str, Any]:
        """
        Query monitored entities using entity selector.
        
        Args:
            entity_selector: Entity selector string
                Examples:
                - type("HOST")
                - type("SERVICE")
                - entityId("HOST-xxx")
                - type("HOST"),tag("environment:production")
            fields: Comma-separated list of fields to include
            from_time: Time filter for entity activity
            page_size: Results per page
            
        Returns:
            Dict with totalCount and list of entities
        """
        params = {
            "entitySelector": entity_selector,
            "from": from_time,
            "pageSize": page_size
        }
        
        if fields:
            params["fields"] = fields
        
        return await self._make_request("GET", "/entities", params=params)
    
    async def get_entity(
        self,
        entity_id: str,
        fields: str = None
    ) -> dict[str, Any]:
        """
        Get details of a specific entity.
        
        Args:
            entity_id: Entity ID (e.g., HOST-xxx, SERVICE-xxx)
            fields: Additional fields to include
            
        Returns:
            Entity details
        """
        params = {}
        if fields:
            params["fields"] = fields
        
        return await self._make_request("GET", f"/entities/{entity_id}", params=params)
    
    async def get_entity_types(self) -> dict[str, Any]:
        """Get list of all entity types."""
        return await self._make_request("GET", "/entityTypes")
    
    # =========================================================================
    # METRICS API v2
    # =========================================================================
    
    async def get_metrics(
        self,
        metric_selector: str = None,
        text: str = None,
        page_size: int = 100
    ) -> dict[str, Any]:
        """
        List available metrics.
        
        Args:
            metric_selector: Filter metrics by selector (supports wildcards)
                Examples: "builtin:host.*", "builtin:service.response.*"
            text: Free text search
            page_size: Results per page
            
        Returns:
            List of metric definitions
        """
        params = {"pageSize": page_size}
        
        if metric_selector:
            params["metricSelector"] = metric_selector
        if text:
            params["text"] = text
        
        return await self._make_request("GET", "/metrics", params=params)
    
    async def query_metrics(
        self,
        metric_selector: str,
        entity_selector: str = None,
        from_time: str = "now-2h",
        to_time: str = "now",
        resolution: str = "1h"
    ) -> dict[str, Any]:
        """
        Query metric data points.
        
        Args:
            metric_selector: Metric to query
                Examples:
                - "builtin:host.cpu.usage"
                - "builtin:service.response.time:avg"
                - "builtin:host.disk.avail:names"
            entity_selector: Filter by entities
            from_time: Start time
            to_time: End time
            resolution: Time resolution (e.g., "1m", "5m", "1h", "1d")
            
        Returns:
            Metric data with timestamps and values
        """
        params = {
            "metricSelector": metric_selector,
            "from": from_time,
            "to": to_time,
            "resolution": resolution
        }
        
        if entity_selector:
            params["entitySelector"] = entity_selector
        
        return await self._make_request("GET", "/metrics/query", params=params)
    
    # =========================================================================
    # EVENTS API v2
    # =========================================================================
    
    async def get_events(
        self,
        event_selector: str = None,
        entity_selector: str = None,
        from_time: str = "now-24h",
        to_time: str = "now",
        page_size: int = 100
    ) -> dict[str, Any]:
        """
        Get events from Dynatrace.
        
        Args:
            event_selector: Filter events by type
                Examples: eventType("CUSTOM_DEPLOYMENT"), eventType("ERROR_EVENT")
            entity_selector: Filter by entities
            from_time: Start time
            to_time: End time
            page_size: Results per page
            
        Returns:
            List of events
        """
        params = {
            "from": from_time,
            "to": to_time,
            "pageSize": page_size
        }
        
        if event_selector:
            params["eventSelector"] = event_selector
        if entity_selector:
            params["entitySelector"] = entity_selector
        
        return await self._make_request("GET", "/events", params=params)
    
    # =========================================================================
    # RELEASES API (Deployments)
    # =========================================================================
    
    async def get_releases(
        self,
        entity_selector: str = None,
        from_time: str = "now-7d",
        to_time: str = "now",
        page_size: int = 50
    ) -> dict[str, Any]:
        """
        Get release/deployment information.
        
        Args:
            entity_selector: Filter by entities
            from_time: Start time
            to_time: End time
            page_size: Results per page
            
        Returns:
            List of releases/deployments
        """
        params = {
            "from": from_time,
            "to": to_time,
            "pageSize": page_size
        }
        
        if entity_selector:
            params["releasesSelector"] = f"affectedEntities({entity_selector})"
        
        return await self._make_request("GET", "/releases", params=params)
    
    # =========================================================================
    # FORMATTING HELPERS
    # =========================================================================
    
    def format_problem(self, problem: dict) -> str:
        """Format a problem into readable text."""
        status = problem.get("status", "UNKNOWN")
        severity = problem.get("severityLevel", "UNKNOWN")
        impact = problem.get("impactLevel", "UNKNOWN")
        title = problem.get("title", "Unknown Problem")
        display_id = problem.get("displayId", "")
        problem_id = problem.get("problemId", "")
        
        # Format timestamps
        start_ts = problem.get("startTime", 0)
        end_ts = problem.get("endTime", -1)
        
        start_time = datetime.fromtimestamp(start_ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if start_ts else "Unknown"
        end_time = datetime.fromtimestamp(end_ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if end_ts > 0 else "Ongoing"
        
        # Get affected entities
        affected = problem.get("affectedEntities", [])
        affected_names = []
        for e in affected[:5]:
            # Handle different entity structures
            if isinstance(e, dict):
                name = e.get("name") or e.get("displayName")
                if not name:
                    entity_id = e.get("entityId", {})
                    if isinstance(entity_id, dict):
                        name = entity_id.get("id", "Unknown")
                    else:
                        name = str(entity_id) if entity_id else "Unknown"
                affected_names.append(name)
        
        # Status emoji
        status_emoji = "🔴" if status == "OPEN" else "🟢"
        severity_emoji = {
            "AVAILABILITY": "⛔",
            "ERROR": "❌", 
            "PERFORMANCE": "⚡",
            "RESOURCE_CONTENTION": "📊",
            "CUSTOM_ALERT": "⚠️"
        }.get(severity, "❓")
        
        # Use display ID if available, otherwise show problem ID
        id_display = display_id if display_id else problem_id[:20] + "..." if len(problem_id) > 20 else problem_id
        
        output = f"""
{status_emoji} **Problem {id_display}**: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Status:** {status}
**Severity:** {severity_emoji} {severity}
**Impact:** {impact}
**Started:** {start_time}
**Ended:** {end_time}

**Affected Entities ({len(affected)}):**
{chr(10).join(f"  • {name}" for name in affected_names) if affected_names else "  • None identified"}
"""
        return output.strip()
    
    def format_problem_list(self, problems_response: dict) -> str:
        """Format a list of problems."""
        total = problems_response.get("totalCount", 0)
        problems = problems_response.get("problems", [])
        
        if total == 0:
            return "✅ No problems found in the specified timeframe."
        
        output = [f"# 🔍 Dynatrace Problems ({total} total)\n"]
        
        for problem in problems[:10]:  # Limit to 10
            status = problem.get("status", "UNKNOWN")
            severity = problem.get("severityLevel", "")
            title = problem.get("title", "Unknown")
            display_id = problem.get("displayId", "")
            
            status_emoji = "🔴" if status == "OPEN" else "🟢"
            output.append(f"{status_emoji} **{display_id}** - {title} [{severity}]")
        
        if total > 10:
            output.append(f"\n... and {total - 10} more problems")
        
        return "\n".join(output)
    
    def format_entity(self, entity: dict) -> str:
        """Format an entity into readable text."""
        entity_id = entity.get("entityId", "Unknown")
        display_name = entity.get("displayName", "Unknown")
        entity_type = entity.get("type", "Unknown")
        
        # Get properties
        props = entity.get("properties", {})
        tags = entity.get("tags", [])
        
        output = f"""
**{display_name}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Type:** {entity_type}
**ID:** {entity_id}
"""
        
        if props:
            output += "\n**Properties:**\n"
            for key, value in list(props.items())[:10]:
                output += f"  • {key}: {value}\n"
        
        if tags:
            tag_strs = [f"{t.get('key')}:{t.get('value', '')}" for t in tags[:5]]
            output += f"\n**Tags:** {', '.join(tag_strs)}"
        
        return output.strip()
    
    def format_metrics_data(self, metrics_response: dict) -> str:
        """Format metrics query results."""
        results = metrics_response.get("result", [])
        
        if not results:
            return "📊 No metric data found."
        
        output = ["# 📊 Metrics Data\n"]
        
        for metric in results:
            metric_id = metric.get("metricId", "Unknown")
            data = metric.get("data", [])
            
            output.append(f"## {metric_id}\n")
            
            for series in data[:5]:  # Limit series
                dimensions = series.get("dimensions", [])
                timestamps = series.get("timestamps", [])
                values = series.get("values", [])
                
                if dimensions:
                    output.append(f"**Dimensions:** {', '.join(dimensions)}")
                
                if values and timestamps:
                    # Show latest value
                    latest_value = values[-1] if values else None
                    latest_time = datetime.fromtimestamp(timestamps[-1] / 1000).strftime("%H:%M:%S") if timestamps else ""
                    
                    if latest_value is not None:
                        output.append(f"**Latest ({latest_time}):** {latest_value:.2f}")
                    
                    # Show min/max/avg
                    valid_values = [v for v in values if v is not None]
                    if valid_values:
                        output.append(f"**Range:** {min(valid_values):.2f} - {max(valid_values):.2f}")
                        output.append(f"**Average:** {sum(valid_values)/len(valid_values):.2f}")
                
                output.append("")
        
        return "\n".join(output)
