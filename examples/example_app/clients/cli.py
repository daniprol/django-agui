"""CLI client for interacting with django-agui agents."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from typing import Any

import requests


class AgentClient:
    """HTTP client for interacting with AG-UI agents."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.thread_id = str(uuid.uuid4())

    def list_agents(self) -> list[dict[str, Any]]:
        """List all available agents."""
        response = self.session.get(f"{self.base_url}/api/agents/")
        response.raise_for_status()
        return response.json().get("agents", [])

    def run_agent(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
        streaming: bool = True,
    ) -> requests.Response:
        """Run an agent with a message."""
        url = f"{self.base_url}/api/agents/{agent_name}/"

        payload = {
            "thread_id": thread_id or self.thread_id,
            "run_id": str(uuid.uuid4()),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message,
                        }
                    ],
                }
            ],
        }

        headers = {"Accept": "text/event-stream" if streaming else "application/json"}

        response = self.session.post(
            url, json=payload, headers=headers, stream=streaming
        )
        response.raise_for_status()
        return response

    def run_agent_non_streaming(
        self,
        agent_name: str,
        message: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Run an agent and get the full response."""
        url = f"{self.base_url}/api/agents/{agent_name}/run/"

        payload = {
            "thread_id": thread_id or self.thread_id,
            "run_id": str(uuid.uuid4()),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message,
                        }
                    ],
                }
            ],
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def parse_sse_event(line: str) -> dict[str, Any] | None:
    """Parse a single SSE event line."""
    if not line.startswith("data:"):
        return None
    data = line[5:].strip()
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def handle_sse_response(response: requests.Response) -> None:
    """Handle streaming SSE response and print events."""
    print("\n--- Agent Response ---\n")

    for line in response.iter_lines():
        if not line:
            continue

        line = line.decode("utf-8")

        if line == ":":
            continue

        event_data = parse_sse_event(line)
        if not event_data:
            continue

        event_type = event_data.get("type", "")

        if event_type == "run_started":
            print(
                f"[Run Started] thread_id={event_data.get('thread_id')}, run_id={event_data.get('run_id')}"
            )

        elif event_type == "text_message_start":
            role = event_data.get("role", "assistant")
            print(f"\n[{role.upper()}] ", end="", flush=True)

        elif event_type == "text_message_content":
            delta = event_data.get("delta", "")
            print(delta, end="", flush=True)

        elif event_type == "text_message_end":
            print("\n")

        elif event_type == "tool_call_start":
            name = event_data.get("tool_call_name", "")
            print(f"\n[TOOL CALL: {name}] ", end="", flush=True)

        elif event_type == "tool_call_args":
            delta = event_data.get("delta", "")
            print(delta, end="", flush=True)

        elif event_type == "tool_call_end":
            print("\n")

        elif event_type == "tool_call_result":
            content = event_data.get("content", "")
            print(f"\n[TOOL RESULT] {content[:100]}...")

        elif event_type == "run_finished":
            print("\n--- Run Finished ---\n")

        elif event_type == "run_error":
            print(f"\n[ERROR] {event_data.get('message')}\n")

        elif event_type == "state_snapshot":
            snapshot = event_data.get("snapshot", {})
            print(f"\n[State] {json.dumps(snapshot, indent=2)[:200]}...")

        elif event_type == "step_started":
            step = event_data.get("step_name", "")
            print(f"\n[Step: {step}] ", end="", flush=True)

        elif event_type == "step_finished":
            print(" [Done]")

        else:
            print(f"\n[Unknown event: {event_type}]")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="CLI client for django-agui agents")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    list_parser = subparsers.add_parser("list", help="List available agents")

    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument("agent", help="Agent name")
    run_parser.add_argument("message", help="Message to send")
    run_parser.add_argument("--thread-id", help="Thread ID for conversation")
    run_parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Don't stream response",
    )

    args = parser.parse_args()

    base_url = os.getenv("AGUI_BASE_URL", "http://localhost:8000")
    client = AgentClient(base_url)

    if args.command == "list":
        try:
            agents = client.list_agents()
            print("\nAvailable Agents:\n")
            for agent in agents:
                print(f"  - {agent['name']}")
                print(f"    Framework: {agent['framework']}")
                print(f"    Description: {agent.get('description', 'N/A')}")
                print()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "run":
        try:
            if args.no_stream:
                result = client.run_agent_non_streaming(
                    args.agent,
                    args.message,
                    args.thread_id,
                )
                print("\n--- Response ---\n")
                for event in result.get("events", []):
                    if event.get("type") == "text_message_content":
                        print(event.get("delta", ""), end="")
                print("\n")
            else:
                response = client.run_agent(
                    args.agent,
                    args.message,
                    args.thread_id,
                    streaming=True,
                )
                handle_sse_response(response)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
