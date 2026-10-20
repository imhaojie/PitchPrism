"""Deterministic football facts. All aggregates are restricted to the played excerpt."""
import math


def validate_match(match):
    if match.get("synthetic") is not True:
        raise ValueError("This demo accepts only explicitly synthetic match data")
    ids, players, previous = set(), {p["id"]: p for p in match["roster"]}, -1
    for event in match["events"]:
        if event["id"] in ids or not previous <= event["second"] <= match["durationSeconds"]:
            raise ValueError("Duplicate or unordered event")
        if event["type"] not in {"pass", "pressure", "recovery", "tackle", "shot"}:
            raise ValueError("Unsupported football event")
        if event["playerId"] not in players or players[event["playerId"]]["team"] != event["team"]:
            raise ValueError("Unknown player or mismatched team")
        if event.get("recipientId") and (event["recipientId"] not in players or players[event["recipientId"]]["team"] != event["team"]):
            raise ValueError("Invalid pass recipient")
        for coordinate in [event["start"], event["end"]]:
            if len(coordinate) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 100 for v in coordinate):
                raise ValueError("Coordinates must be normalized percentages")
        if "xg" in event and (event["type"] != "shot" or not math.isfinite(event["xg"]) or not 0 <= event["xg"] <= 1):
            raise ValueError("Invalid synthetic shot xG")
        ids.add(event["id"])
        previous = event["second"]
    return match


def pass_distance(event, match):
    pitch = match["coordinateSystem"]
    return math.hypot((event["end"][0] - event["start"][0]) * pitch["lengthMetres"] / 100,
                      (event["end"][1] - event["start"][1]) * pitch["widthMetres"] / 100)


def snapshot(match, second):
    if type(second) not in (float, int) or not math.isfinite(second):
        raise ValueError("Time must be finite")
    second = min(match["durationSeconds"], max(0, second))
    events = [e for e in match["events"] if e["second"] <= second]
    stats = {}
    for team in match["teams"]:
        own = [e for e in events if e["team"] == team["id"]]
        passes, shots = [e for e in own if e["type"] == "pass"], [e for e in own if e["type"] == "shot"]
        complete = sum(e["outcome"] == "complete" for e in passes)
        xg = [e["xg"] for e in shots if "xg" in e]
        stats[team["id"]] = {"passes": len(passes), "completedPasses": complete,
            "passAccuracy": round(100 * complete / len(passes), 1) if passes else None,
            "shots": len(shots), "goals": sum(e["outcome"] == "goal" for e in shots),
            "xg": round(sum(xg), 2) if shots and len(xg) == len(shots) else None,
            "pressureEvents": sum(e["type"] == "pressure" for e in own),
            "scope": "played excerpt only", "evidenceIds": [e["id"] for e in own]}
    latest_pass = next((e for e in reversed(events) if e["type"] == "pass"), None)
    facts = []
    if latest_pass:
        facts.append({"id": "latest-pass-distance", "label": "Pass distance", "value": round(pass_distance(latest_pass, match), 1),
                      "unit": "m", "scope": "latest pass", "evidenceIds": [latest_pass["id"]],
                      "formula": "hypot(dx × 105 / 100, dy × 68 / 100)"})
    return {"matchId": match["id"], "synthetic": True, "sourceSecond": second, "events": events,
            "stats": stats, "facts": facts, "clockSeconds": match["clockStartSeconds"] + int(second),
            "scope": "played excerpt only; not full-match or season statistics"}


def available_angles(state):
    events = state["events"]
    result = [{"id": "build-up", "headline": "Read the next pass.",
               "casual": "Follow the ball as Northbridge build from the back. The event trail shows who receives each pass.",
               "analyst": "Inspect completed passes and their recipients in this excerpt. The passing map uses supplied synthetic event coordinates.",
               "evidenceIds": [e["id"] for e in events if e["type"] == "pass"][-3:]}]
    switch = next((e for e in events if e["type"] == "pass" and abs(e["end"][1] - e["start"][1]) >= 40), None)
    if switch:
        result.append({"id": "switch", "headline": "One switch. A different picture.",
            "casual": "Northbridge move the ball from one side to the other. Watch the receiving player on the far side.",
            "analyst": "A completed diagonal switch changes the side of the attack. The event coordinates establish the lateral change; they do not establish its cause.",
            "evidenceIds": [switch["id"]]})
    shots = [e for e in events if e["type"] == "shot"]
    if shots:
        shot = shots[-1]
        result.append({"id": "shot", "headline": "A chance, in context." if shot["outcome"] != "goal" else "The finish is only half the story.",
            "casual": "The shot is saved. Look back at the passes before the chance." if shot["outcome"] != "goal" else "Northbridge score after regaining the ball. Replay the short passing sequence before the finish.",
            "analyst": "Separate the shot outcome from its scenario xG input. This chance estimate is synthetic, not an official model prediction.",
            "evidenceIds": [e["id"] for e in events if e["type"] in {"shot", "pass", "tackle"}][-3:]})
    return [a for a in result if a["evidenceIds"]]


def local_story(state, mode="casual", team="all", player="all"):
    angles = available_angles(state)
    if not angles:
        return {"headline": "Every match has a story.", "explanation": "Press play to begin the synthetic event sequence.",
                "evidenceIds": [], "provider": "local", "mode": mode, "sourceSecond": state["sourceSecond"]}
    angle = angles[-1]
    focused = [e for e in state["events"] if (player == "all" or player in {e["playerId"], e.get("recipientId")}) and (team == "all" or e["team"] == team)]
    if (player != "all" or team != "all") and focused:
        angle = {"headline": "Your view. Your part of the game.",
                 "casual": "Follow your selection through the highlighted event trail. Each highlighted action links back to the synthetic feed.",
                 "analyst": "The selected event trail isolates your chosen team or player's actions and receipts. Team aggregates retain their excerpt scope.",
                 "evidenceIds": [e["id"] for e in focused][-3:]}
    elif player != "all" or team != "all":
        return {"headline": "Waiting for your selection.", "explanation": "Your selection has no events in the played excerpt yet.",
                "evidenceIds": [], "provider": "local", "mode": mode, "sourceSecond": state["sourceSecond"]}
    return {"headline": angle["headline"], "explanation": angle[mode], "evidenceIds": angle["evidenceIds"],
            "provider": "local", "mode": mode, "sourceSecond": state["sourceSecond"], "angle": angle.get("id", "focus")}
