"""Bounded tool-using Foundry agent, ported from GameBuddy's read/validate loop.

Uses the Microsoft-documented OpenAI v1 REST surface, not an AWS compatibility shim.
No model call is counted as successful until the returned story passes validation.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .analytics import available_angles, local_story


class FoundryError(RuntimeError):
    pass


def settings():
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
    auth = bool(os.environ.get("AZURE_OPENAI_API_KEY")) or os.environ.get("AZURE_USE_ENTRA") == "1"
    if endpoint:
        url = urllib.parse.urlsplit(endpoint)
        if url.scheme != "https" or not url.hostname or not url.hostname.endswith((".openai.azure.com", ".services.ai.azure.com", ".cognitiveservices.azure.com")) or url.username or url.password or url.query or url.fragment or url.path not in ("", "/", "/openai/v1"):
            raise FoundryError("Use an Azure resource HTTPS endpoint, without a secret or query in the URL")
    return {"endpoint": endpoint, "deployment": deployment, "configured": bool(endpoint and deployment and auth)}


def auth_headers():
    key = os.environ.get("AZURE_OPENAI_API_KEY")
    if key:
        return {"api-key": key}
    if os.environ.get("AZURE_USE_ENTRA") == "1":
        try:
            from azure.identity import DefaultAzureCredential
            token = DefaultAzureCredential(exclude_interactive_browser_credential=True).get_token("https://cognitiveservices.azure.com/.default")
            return {"Authorization": "Bearer " + token.token}
        except Exception as error:
            raise FoundryError("Azure identity unavailable; run az login and check Cognitive Services OpenAI User access") from error
    raise FoundryError("Azure credentials are not configured")


def request_model(messages, tools, remaining_seconds=25):
    config = settings()
    if not config["configured"]:
        raise FoundryError("Foundry is not configured")
    base = config["endpoint"]
    if not base.endswith("/openai/v1"):
        base += "/openai/v1"
    body = {"model": config["deployment"], "messages": messages, "tools": tools,
            "tool_choice": "required", "max_completion_tokens": 900}
    request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **auth_headers()}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=min(25, remaining_seconds)) as response:
            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise FoundryError("Foundry response exceeds limit")
            result = json.loads(raw)
            return result, response.headers.get("x-request-id") or response.headers.get("apim-request-id")
    except urllib.error.HTTPError as error:
        # Error bodies can include deployment, prompts or account identifiers. Do not expose them.
        raise FoundryError(f"Foundry HTTP {error.code}; check model deployment, quota and identity") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise FoundryError("Foundry request timed out or returned an invalid response") from error


def function(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}}


TOOLS = [
    function("read_match_state", "Read time-bounded synthetic events, canonical stats and allowed editorial angles.", {}, []),
    function("read_evidence", "Read exact source events by ID. Future or unknown IDs are rejected.",
             {"evidenceIds": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8}}, ["evidenceIds"]),
    function("validate_story", "Submit a grounded story. Numbers are rendered from facts, never written into prose.",
             {"headline": {"type": "string"}, "explanation": {"type": "string"},
              "angle": {"type": "string"}, "evidenceIds": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8}},
             ["headline", "explanation", "angle", "evidenceIds"]),
]

SYSTEM = """You are PitchPrism's football storytelling agent. This is an ORIGINAL SYNTHETIC football scenario, never a real Premier League match.
Use read_match_state, then read_evidence for every ID you cite, then validate_story. You may repair a validation error.
Choose an angle from the returned availableAngles. Explain what matters in English for the requested audience and focus.
Casual: plain language and a specific thing to watch. Analyst: precise event sequence and uncertainty.
Use ONLY supplied synthetic events. No invented identity, speed, possession, score, offside, pressure attribution or causal tactical certainty.
State shot xG is a synthetic scenario input, not official or model-predicted. All stats apply ONLY to the played excerpt.
Never write any numbers or numeric claims in headline/explanation. Code renders canonical figures separately.
No claims about unseen space, defenders' intentions, causation, tracking or future events. Keep headline under 70 characters, explanation under 340 characters.
Team/player focus must affect the explanation when supplied. No markdown. Submit by tool, never ordinary assistant prose."""


def validate_story(candidate, state, inspected, read_state):
    if not read_state:
        raise ValueError("Read the match state first")
    ids = candidate.get("evidenceIds")
    known = {e["id"] for e in state["events"]}
    if not isinstance(ids, list) or not 1 <= len(ids) <= 8 or len(set(ids)) != len(ids) or not all(isinstance(i, str) and i in known and i in inspected for i in ids):
        raise ValueError("Cite only distinct, actually inspected events already present in the played excerpt")
    angles = {a["id"]: a for a in available_angles(state)}
    if candidate.get("angle") not in angles or not set(angles[candidate["angle"]]["evidenceIds"]).issubset(ids):
        raise ValueError("Choose an available angle and cite all its supporting events")
    for key, limit in [("headline", 70), ("explanation", 340)]:
        value = candidate.get(key)
        if not isinstance(value, str) or not 3 <= len(value.strip()) <= limit:
            raise ValueError(f"Invalid {key} length")
        if re.search(r"[\d%<>]|\b(one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|half|double|twice|percent|percentage)\b", value, re.I):
            raise ValueError("Numbers and quantitative claims belong only in canonical fact fields")
        if re.search(r"\b(official xg|real match|tracking data|proved|guaranteed|caused|forced|because)\b", value, re.I):
            raise ValueError("Unsupported provenance or causal assertion")
    return {key: candidate[key] for key in ("headline", "explanation", "angle", "evidenceIds")}


def run_agent(state, mode="casual", team="all", player="all", transport=request_model):
    if not state["events"] or not available_angles(state):
        return local_story(state, mode, team, player)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps({
        "audience": mode, "favoriteTeam": team, "favoritePlayer": player, "sourceSecond": state["sourceSecond"],
        "task": "Read, inspect, explain and validate this moment."})}]
    inspected, trace, seen_calls, read_state = set(), [], set(), False
    start, tokens = time.monotonic(), 0
    for round_number in range(1, 7):
        remaining = 50 - (time.monotonic() - start)
        if remaining <= 0 or tokens >= 12000:
            break
        response, request_id = transport(messages, TOOLS, remaining)
        tokens += response.get("usage", {}).get("total_tokens", 0)
        if tokens > 12000:
            break
        try:
            message = response["choices"][0]["message"]
            calls = message.get("tool_calls", [])
            if message.get("role") != "assistant" or not 1 <= len(calls) <= 4:
                raise ValueError("Expected bounded tool calls")
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise FoundryError("Foundry did not return the tool protocol") from error
        messages.append({k: message[k] for k in ("role", "content", "tool_calls") if k in message})
        accepted = None
        for call in calls:
            identifier = call.get("id")
            if not isinstance(identifier, str) or identifier in seen_calls:
                raise FoundryError("Duplicate or invalid tool call")
            seen_calls.add(identifier)
            name = call.get("function", {}).get("name")
            try:
                args = json.loads(call["function"]["arguments"])
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be an object")
                if name == "read_match_state":
                    read_state = True
                    output = {k: state[k] for k in ("matchId", "synthetic", "sourceSecond", "stats", "facts", "scope")}
                    output["eventIndex"] = [{k: e[k] for k in ("id", "second", "type", "playerId", "outcome")} for e in state["events"]]
                    output["availableAngles"] = available_angles(state)
                elif name == "read_evidence":
                    ids = args.get("evidenceIds")
                    known = {e["id"]: e for e in state["events"]}
                    if not isinstance(ids, list) or not 1 <= len(ids) <= 8 or not all(isinstance(i, str) and i in known for i in ids):
                        raise ValueError("Unknown or future event ID")
                    inspected.update(ids)
                    output = {"events": [known[i] for i in ids]}
                elif name == "validate_story":
                    accepted = validate_story(args, state, inspected, read_state)
                    output = {"accepted": True}
                else:
                    raise ValueError("Unknown tool")
            except (ValueError, KeyError, TypeError) as error:
                output = {"accepted": False, "error": str(error)}
            trace.append({"round": round_number, "tool": name, "requestId": request_id,
                          "ok": "error" not in output, "elapsedMs": round((time.monotonic() - start) * 1000)})
            messages.append({"role": "tool", "tool_call_id": identifier, "content": json.dumps(output)})
        if accepted:
            return {**accepted, "provider": "azure-foundry", "deployment": settings()["deployment"],
                    "mode": mode, "sourceSecond": state["sourceSecond"], "trace": trace, "tokens": tokens,
                    "validation": "protocol, time bounds, references and numeric guard passed; prose is model interpretation"}
    raise FoundryError("Foundry agent exhausted its bounded read/validate budget")
