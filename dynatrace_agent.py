"""
Dynatrace AI Agent - Provides intelligent observability insights

This agent provides:
1. Problem detection and analysis
2. Root cause investigation
3. Service topology mapping
4. Performance metrics analysis
5. Deployment correlation
6. AI-powered recommendations
"""
import os
import json
from typing import Any
from google import genai

from dynatrace_client import DynatraceClient


class DynatraceAgent:
    """
    AI-powered Dynatrace Agent for SRE/Ops workflows.
    
    This agent:
    - Fetches observability data from Dynatrace
    - Uses Gemini AI for intelligent analysis
    - Correlates problems with deployments
    - Provides root cause recommendations
    """
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
    
    def __init__(self):
        """Initialize Dynatrace client and Gemini AI."""
        self.dynatrace = DynatraceClient()
        
        # Initialize Gemini for AI features
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.genai_client = genai.Client(api_key=api_key)
        # Use gemini-1.5-flash as it has better rate limits on free tier
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    async def _ai_analyze(self, prompt: str, context: str = "") -> str:
        """Use Gemini to analyze and generate insights."""
        import time
        
        full_prompt = f"""You are an expert SRE/DevOps engineer analyzing Dynatrace monitoring data.
Provide concise, actionable insights.

{context}

{prompt}"""
        
        # Try with retry logic for rate limits
        models_to_try = [self.model, "gemini-1.5-flash", "gemini-1.5-pro"]
        
        for model in models_to_try:
            try:
                response = self.genai_client.models.generate_content(
                    model=model,
                    contents=full_prompt
                )
                return response.text.strip()
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Rate limited, try next model or wait
                    if model != models_to_try[-1]:
                        continue
                    else:
                        # Last model also failed, return without AI
                        return "⚠️ AI analysis temporarily unavailable (rate limit). Dynatrace data shown above."
                else:
                    return f"AI analysis error: {str(e)[:100]}"
        
        return "⚠️ AI analysis unavailable"
    
    # =========================================================================
    # SKILL 1: List Problems
    # =========================================================================
    
    async def list_problems(
        self,
        status: str = None,
        severity: str = None,
        time_range: str = "24h"
    ) -> str:
        """
        List problems from Dynatrace.
        
        Args:
            status: Filter by OPEN or CLOSED
            severity: Filter by severity level
            time_range: Time range like "1h", "24h", "7d"
            
        Returns:
            Formatted list of problems
        """
        try:
            from_time = f"now-{time_range}"
            
            response = await self.dynatrace.get_problems(
                status=status,
                severity=severity,
                from_time=from_time
            )
            
            return self.dynatrace.format_problem_list(response)
            
        except Exception as e:
            return f"❌ Error fetching problems: {str(e)}"
    
    # =========================================================================
    # SKILL 2: Get Problem Details with Root Cause Analysis
    # =========================================================================
    
    async def analyze_problem(self, problem_id: str) -> str:
        """
        Get detailed problem analysis with root cause investigation.
        
        Args:
            problem_id: Problem ID (e.g., "P-12345")
            
        Returns:
            Detailed problem analysis with AI insights
        """
        try:
            # Get problem details
            problem = await self.dynatrace.get_problem_details(problem_id)
            
            # Format basic problem info
            output = [self.dynatrace.format_problem(problem)]
            
            # Extract evidence details
            evidence_details = problem.get("evidenceDetails", {})
            evidence_list = evidence_details.get("details", [])
            
            if evidence_list:
                output.append("\n## 🔍 Evidence (Root Cause Indicators)\n")
                for evidence in evidence_list[:5]:
                    evidence_type = evidence.get("evidenceType", "UNKNOWN")
                    display_name = evidence.get("displayName", "Unknown")
                    
                    # Get entity info
                    entity = evidence.get("entity", {})
                    entity_name = entity.get("name", "Unknown Entity")
                    
                    output.append(f"**{evidence_type}:** {display_name}")
                    output.append(f"  → Entity: {entity_name}")
                    
                    # Extract specific evidence data
                    if evidence_type == "EVENT":
                        event_type = evidence.get("eventType", "")
                        output.append(f"  → Event Type: {event_type}")
                    elif evidence_type == "METRIC":
                        metric_name = evidence.get("metricId", "")
                        output.append(f"  → Metric: {metric_name}")
                    
                    output.append("")
            
            # Check for recent deployments correlation
            affected_entities = problem.get("affectedEntities", [])
            if affected_entities:
                entity_ids = [e.get("entityId", {}).get("id", "") for e in affected_entities[:3]]
                entity_selector = ",".join([f'entityId("{eid}")' for eid in entity_ids if eid])
                
                if entity_selector:
                    try:
                        releases = await self.dynatrace.get_releases(
                            entity_selector=entity_selector,
                            from_time="now-7d"
                        )
                        
                        release_list = releases.get("releases", [])
                        if release_list:
                            output.append("\n## 🚀 Recent Deployments (Potential Correlation)\n")
                            for release in release_list[:3]:
                                version = release.get("version", "Unknown")
                                name = release.get("name", "Unknown")
                                timestamp = release.get("releaseTime", 0)
                                
                                from datetime import datetime
                                release_time = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown"
                                
                                output.append(f"• **{name}** v{version} - {release_time}")
                    except:
                        pass  # Releases API might not be available
            
            # Get AI analysis
            ai_context = f"""
Problem: {problem.get('title', 'Unknown')}
Severity: {problem.get('severityLevel', 'Unknown')}
Impact: {problem.get('impactLevel', 'Unknown')}
Affected Entities: {len(affected_entities)}
Evidence Count: {len(evidence_list)}

Evidence Details:
{json.dumps(evidence_list[:3], indent=2) if evidence_list else 'None'}
"""
            
            ai_analysis = await self._ai_analyze(
                "Based on this Dynatrace problem data, provide:\n"
                "1. **Likely Root Cause** (1-2 sentences)\n"
                "2. **Recommended Actions** (2-3 bullet points)\n"
                "3. **Risk Assessment** (Low/Medium/High with brief explanation)",
                context=ai_context
            )
            
            output.append("\n## 🤖 AI Analysis\n")
            output.append(ai_analysis)
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error analyzing problem {problem_id}: {str(e)}"
    
    # =========================================================================
    # SKILL 3: Get Service Topology
    # =========================================================================
    
    async def get_topology(
        self,
        entity_type: str = "SERVICE",
        tag: str = None,
        name_filter: str = None
    ) -> str:
        """
        Get service topology and dependencies.
        
        Args:
            entity_type: Type of entities (SERVICE, HOST, PROCESS_GROUP, etc.)
            tag: Filter by tag (e.g., "environment:production")
            name_filter: Filter by name pattern
            
        Returns:
            Topology information with dependencies
        """
        try:
            # Build entity selector
            selectors = [f'type("{entity_type}")']
            
            if tag:
                selectors.append(f'tag("{tag}")')
            if name_filter:
                selectors.append(f'entityName.contains("{name_filter}")')
            
            entity_selector = ",".join(selectors)
            
            # Get entities with relationship info
            fields = "+fromRelationships,+toRelationships,+properties,+tags"
            
            response = await self.dynatrace.get_entities(
                entity_selector=entity_selector,
                fields=fields
            )
            
            entities = response.get("entities", [])
            total = response.get("totalCount", 0)
            
            if not entities:
                return f"📊 No {entity_type} entities found matching criteria."
            
            output = [f"# 🗺️ Topology: {entity_type} ({total} total)\n"]
            
            for entity in entities[:10]:
                display_name = entity.get("displayName", "Unknown")
                entity_id = entity.get("entityId", "")
                
                output.append(f"## {display_name}")
                output.append(f"**ID:** `{entity_id}`")
                
                # Show relationships
                from_rels = entity.get("fromRelationships", {})
                to_rels = entity.get("toRelationships", {})
                
                if from_rels:
                    for rel_type, targets in list(from_rels.items())[:3]:
                        target_names = [t.get("name", t.get("id", "?")) for t in targets[:3]]
                        output.append(f"  → **{rel_type}:** {', '.join(target_names)}")
                
                if to_rels:
                    for rel_type, sources in list(to_rels.items())[:3]:
                        source_names = [s.get("name", s.get("id", "?")) for s in sources[:3]]
                        output.append(f"  ← **{rel_type}:** {', '.join(source_names)}")
                
                # Show tags
                tags = entity.get("tags", [])
                if tags:
                    tag_strs = [f"{t.get('key')}:{t.get('value', '')}" for t in tags[:5]]
                    output.append(f"  **Tags:** {', '.join(tag_strs)}")
                
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error fetching topology: {str(e)}"
    
    # =========================================================================
    # SKILL 4: Query Metrics
    # =========================================================================
    
    async def query_metrics(
        self,
        metric: str,
        entity_type: str = None,
        entity_id: str = None,
        time_range: str = "2h"
    ) -> str:
        """
        Query performance metrics.
        
        Args:
            metric: Metric to query (e.g., "cpu", "response_time", "error_rate")
            entity_type: Filter by entity type
            entity_id: Filter by specific entity ID
            time_range: Time range like "1h", "2h", "24h"
            
        Returns:
            Formatted metric data
        """
        try:
            # Map common metric names to Dynatrace selectors
            metric_mappings = {
                "cpu": "builtin:host.cpu.usage:avg",
                "memory": "builtin:host.mem.usage:avg",
                "disk": "builtin:host.disk.usedPct:avg",
                "response_time": "builtin:service.response.time:avg",
                "error_rate": "builtin:service.errors.total.rate:avg",
                "throughput": "builtin:service.requestCount.total:avg",
                "availability": "builtin:host.availability:avg",
                "network": "builtin:host.net.nic.trafficIn:avg",
            }
            
            # Get metric selector
            metric_lower = metric.lower().replace(" ", "_")
            metric_selector = metric_mappings.get(metric_lower, metric)
            
            # Build entity selector
            entity_selector = None
            if entity_id:
                entity_selector = f'entityId("{entity_id}")'
            elif entity_type:
                entity_selector = f'type("{entity_type}")'
            
            response = await self.dynatrace.query_metrics(
                metric_selector=metric_selector,
                entity_selector=entity_selector,
                from_time=f"now-{time_range}",
                resolution="10m" if time_range in ["1h", "2h"] else "1h"
            )
            
            return self.dynatrace.format_metrics_data(response)
            
        except Exception as e:
            return f"❌ Error querying metrics: {str(e)}"
    
    # =========================================================================
    # SKILL 5: Get Recent Deployments
    # =========================================================================
    
    async def get_deployments(
        self,
        time_range: str = "7d",
        entity_filter: str = None
    ) -> str:
        """
        Get recent deployments/releases.
        
        Args:
            time_range: Time range to search
            entity_filter: Filter by entity name or ID
            
        Returns:
            List of recent deployments
        """
        try:
            entity_selector = None
            if entity_filter:
                entity_selector = f'entityName.contains("{entity_filter}")'
            
            response = await self.dynatrace.get_releases(
                entity_selector=entity_selector,
                from_time=f"now-{time_range}"
            )
            
            releases = response.get("releases", [])
            total = response.get("totalCount", 0)
            
            if not releases:
                return "🚀 No deployments found in the specified timeframe."
            
            output = [f"# 🚀 Recent Deployments ({total} total)\n"]
            
            from datetime import datetime
            
            for release in releases[:15]:
                name = release.get("name", "Unknown")
                version = release.get("version", "?")
                stage = release.get("stage", "?")
                product = release.get("product", "?")
                timestamp = release.get("releaseTime", 0)
                
                release_time = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown"
                
                # Get affected entities
                affected = release.get("affectedEntities", [])
                affected_count = len(affected)
                
                output.append(f"## {name} v{version}")
                output.append(f"**Product:** {product}")
                output.append(f"**Stage:** {stage}")
                output.append(f"**Released:** {release_time}")
                output.append(f"**Affected Entities:** {affected_count}")
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error fetching deployments: {str(e)}"
    
    # =========================================================================
    # SKILL 6: Root Cause Analysis (AI-Powered)
    # =========================================================================
    
    async def root_cause_analysis(
        self,
        problem_id: str = None,
        symptoms: str = None
    ) -> str:
        """
        Perform AI-powered root cause analysis.
        
        Args:
            problem_id: Specific problem to analyze
            symptoms: Description of symptoms if no problem ID
            
        Returns:
            Detailed root cause analysis with recommendations
        """
        try:
            context_data = {}
            
            if problem_id:
                # Get problem details
                problem = await self.dynatrace.get_problem_details(problem_id)
                context_data["problem"] = problem
                
                # Get affected entities' metrics
                affected = problem.get("affectedEntities", [])
                if affected:
                    entity_id = affected[0].get("entityId", {}).get("id", "")
                    if entity_id:
                        try:
                            # Get CPU and memory metrics
                            cpu_metrics = await self.dynatrace.query_metrics(
                                metric_selector="builtin:host.cpu.usage:avg",
                                entity_selector=f'entityId("{entity_id}")',
                                from_time="now-6h"
                            )
                            context_data["cpu_metrics"] = cpu_metrics
                        except:
                            pass
                
                # Get recent deployments for correlation
                try:
                    releases = await self.dynatrace.get_releases(from_time="now-7d")
                    context_data["recent_releases"] = releases.get("releases", [])[:5]
                except:
                    pass
            
            else:
                # Get open problems
                problems_response = await self.dynatrace.get_problems(
                    status="OPEN",
                    from_time="now-24h"
                )
                context_data["open_problems"] = problems_response.get("problems", [])[:5]
            
            # Build AI prompt
            ai_prompt = f"""
Analyze the following Dynatrace monitoring data and provide a comprehensive root cause analysis.

{"Symptoms reported: " + symptoms if symptoms else ""}

Monitoring Data:
{json.dumps(context_data, indent=2, default=str)[:4000]}

Provide a structured analysis with:

## 🔍 Root Cause Analysis

### Primary Cause
[Identify the most likely root cause]

### Contributing Factors
[List secondary factors that may have contributed]

### Evidence Chain
[Connect the dots between symptoms and root cause]

## 📊 Impact Assessment
[Describe the scope and severity of impact]

## 🛠️ Recommended Actions

### Immediate Actions (Next 15 minutes)
[List critical steps to mitigate]

### Short-term Actions (Next 24 hours)
[List follow-up remediation steps]

### Preventive Measures
[Suggest ways to prevent recurrence]

## ⚠️ Risk Assessment
[Rate overall risk and urgency]
"""
            
            analysis = await self._ai_analyze(ai_prompt)
            
            return analysis
            
        except Exception as e:
            return f"❌ Error performing root cause analysis: {str(e)}"
    
    # =========================================================================
    # SKILL 7: Natural Language Query
    # =========================================================================
    
    async def query(self, question: str) -> str:
        """
        Answer natural language questions about Dynatrace data.
        
        Args:
            question: Natural language question
            
        Returns:
            AI-generated answer with relevant data
        """
        try:
            # Determine what data to fetch based on the question
            question_lower = question.lower()
            
            context_data = {}
            
            # Fetch relevant data based on question keywords
            if any(word in question_lower for word in ["problem", "issue", "alert", "incident"]):
                problems = await self.dynatrace.get_problems(from_time="now-24h")
                context_data["problems"] = problems
            
            if any(word in question_lower for word in ["deploy", "release", "change"]):
                releases = await self.dynatrace.get_releases(from_time="now-7d")
                context_data["releases"] = releases
            
            if any(word in question_lower for word in ["service", "topology", "dependency"]):
                services = await self.dynatrace.get_entities(
                    entity_selector='type("SERVICE")',
                    fields="+fromRelationships,+toRelationships"
                )
                context_data["services"] = services
            
            if any(word in question_lower for word in ["host", "server", "infrastructure"]):
                hosts = await self.dynatrace.get_entities(
                    entity_selector='type("HOST")',
                    fields="+properties"
                )
                context_data["hosts"] = hosts
            
            if any(word in question_lower for word in ["cpu", "memory", "performance", "metric"]):
                try:
                    cpu = await self.dynatrace.query_metrics(
                        metric_selector="builtin:host.cpu.usage:avg:names",
                        from_time="now-2h"
                    )
                    context_data["cpu_metrics"] = cpu
                except:
                    pass
            
            # If no specific data fetched, get a general overview
            if not context_data:
                problems = await self.dynatrace.get_problems(from_time="now-24h")
                context_data["recent_problems"] = problems
            
            # Generate response with AI
            ai_prompt = f"""
Question: {question}

Available Dynatrace Data:
{json.dumps(context_data, indent=2, default=str)[:4000]}

Provide a helpful, conversational answer to the question based on the monitoring data.
If the data doesn't contain enough information to fully answer the question,
explain what data would be needed and provide what insights you can.
"""
            
            response = await self._ai_analyze(ai_prompt)
            return response
            
        except Exception as e:
            return f"❌ Error processing query: {str(e)}"
    
    # =========================================================================
    # SKILL 8: Health Summary
    # =========================================================================
    
    async def get_health_summary(self) -> str:
        """
        Get overall health summary of the monitored environment.
        
        Returns:
            Comprehensive health overview
        """
        try:
            # Gather data from multiple sources
            open_problems = await self.dynatrace.get_problems(status="OPEN", from_time="now-24h")
            recent_releases = await self.dynatrace.get_releases(from_time="now-7d")
            
            open_count = open_problems.get("totalCount", 0)
            release_count = recent_releases.get("totalCount", 0)
            
            problems = open_problems.get("problems", [])
            
            # Categorize by severity
            severity_counts = {}
            for p in problems:
                sev = p.get("severityLevel", "UNKNOWN")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            # Build output
            health_emoji = "🟢" if open_count == 0 else ("🟡" if open_count < 5 else "🔴")
            
            output = [
                f"# {health_emoji} Environment Health Summary",
                "",
                f"## 📊 Current Status",
                f"**Open Problems:** {open_count}",
                f"**Recent Deployments (7d):** {release_count}",
                ""
            ]
            
            if severity_counts:
                output.append("## 🔥 Problems by Severity")
                for sev, count in sorted(severity_counts.items()):
                    emoji = {"AVAILABILITY": "⛔", "ERROR": "❌", "PERFORMANCE": "⚡"}.get(sev, "⚠️")
                    output.append(f"  {emoji} **{sev}:** {count}")
                output.append("")
            
            if problems:
                output.append("## 🔴 Active Problems")
                for p in problems[:5]:
                    output.append(f"• **{p.get('displayId')}:** {p.get('title')}")
                output.append("")
            
            # Add AI insights
            ai_context = f"""
Open Problems: {open_count}
Severity Distribution: {json.dumps(severity_counts)}
Recent Deployments: {release_count}
"""
            
            ai_summary = await self._ai_analyze(
                "Provide a brief 2-3 sentence executive summary of the environment health status. "
                "Highlight any critical concerns or positive trends.",
                context=ai_context
            )
            
            output.append("## 🤖 AI Summary")
            output.append(ai_summary)
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error generating health summary: {str(e)}"
