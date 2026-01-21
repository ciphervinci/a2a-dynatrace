"""
Test Client for the A2A Dynatrace Agent

Usage:
    python test_client.py [--url http://localhost:8000]
"""
import argparse
import json
import httpx
import uuid


def get_agent_card(base_url: str) -> dict:
    """Fetch the agent card from the server."""
    url = f"{base_url}/.well-known/agent.json"
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    return response.json()


def send_message(base_url: str, message: str, api_key: str = None) -> dict:
    """Send a message to the A2A agent."""
    request_body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "messageId": str(uuid.uuid4()),
            }
        }
    }
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-sn-apikey"] = api_key
    
    response = httpx.post(
        base_url,
        json=request_body,
        headers=headers,
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()


def extract_response_text(response: dict) -> str:
    """Extract the text response from the JSON-RPC response."""
    try:
        result = response.get("result", {})
        
        if "parts" in result:
            parts = result["parts"]
            for part in parts:
                if part.get("kind") == "text":
                    return part.get("text", "")
        
        if "messages" in result:
            messages = result["messages"]
            if messages:
                last_message = messages[-1]
                parts = last_message.get("parts", [])
                for part in parts:
                    if part.get("kind") == "text":
                        return part.get("text", "")
        
        if "artifacts" in result:
            artifacts = result["artifacts"]
            if artifacts:
                for artifact in artifacts:
                    parts = artifact.get("parts", [])
                    for part in parts:
                        if part.get("kind") == "text":
                            return part.get("text", "")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error parsing response: {e}"


def main():
    parser = argparse.ArgumentParser(description="Test client for A2A Dynatrace Agent")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    args = parser.parse_args()
    
    base_url = args.url.rstrip("/")
    
    print("=" * 70)
    print("🔍 A2A Dynatrace Agent - Test Client")
    print("=" * 70)
    
    # Fetch agent card
    print("\n📇 Fetching Agent Card...")
    try:
        agent_card = get_agent_card(base_url)
        print(f"   ✅ Name: {agent_card.get('name')}")
        print(f"   ✅ Version: {agent_card.get('version')}")
        print(f"   ✅ URL: {agent_card.get('url')}")
        print(f"   ✅ Skills: {len(agent_card.get('skills', []))}")
        for skill in agent_card.get('skills', []):
            print(f"      • {skill['name']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test messages
    test_messages = [
        ("Help", ""),
        ("Health Summary", "Environment health status"),
        ("List Problems", "Show me open problems from last 24 hours"),
        ("Topology", "Show service topology"),
        ("Natural Language", "Is there anything I should worry about?"),
    ]
    
    for test_name, msg in test_messages:
        print(f"\n{'='*70}")
        print(f"📤 Test: {test_name}")
        print(f"   Message: '{msg or '(empty)'}'")
        print("-" * 70)
        
        try:
            response = send_message(base_url, msg, args.api_key)
            text = extract_response_text(response)
            
            # Truncate long responses
            if len(text) > 800:
                print(f"📥 Response (truncated):\n{text[:800]}...")
            else:
                print(f"📥 Response:\n{text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n{'='*70}")
    print("✅ Test complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
