"""Reproducible, fictional football sequence. No licensed match data or footage."""
import json
from pathlib import Path


def build_match():
    teams = [{"id": "NBR", "name": "Northbridge AFC", "short": "Northbridge", "color": "#dfff83"},
             {"id": "RIV", "name": "Riverside United", "short": "Riverside", "color": "#b9bcff"}]
    names = ["Ellis Ward", "Leo Bennett", "Noah Reed", "Oscar Shaw", "Ethan Cole", "Theo Hayes",
             "Jude Morgan", "Finn Brooks", "Luca Vale", "Milo Hart", "Arlo Blake",
             "Hugo Bell", "Louis West", "Owen Fox", "Max Stone", "Eli Park", "Jack Lane",
             "Kai Ross", "Alex Frost", "Sam Wells", "Ben Lake", "Jay Cross"]
    positions = [(6, 50), (22, 20), (19, 42), (19, 63), (25, 82), (40, 34), (42, 63),
                 (58, 14), (62, 45), (59, 81), (75, 53)]
    roster = []
    for i, name in enumerate(names):
        team = "NBR" if i < 11 else "RIV"
        x, y = positions[i % 11]
        if team == "RIV":
            x, y = 100 - x, 100 - y
        roster.append({"id": f"{team}-{i % 11 + 1}", "name": name, "number": i % 11 + 1,
                       "team": team, "position": [x, y]})
    # Coordinates are normalized percentages on a synthetic 105 x 68 metre pitch.
    raw = [
        (1, "recovery", "NBR-3", None, [20, 42], [20, 42], "success", None),
        (3, "pass", "NBR-3", "NBR-6", [20, 42], [39, 34], "complete", None),
        (6, "pressure", "RIV-9", None, [42, 36], [39, 34], "applied", None),
        (8, "pass", "NBR-6", "NBR-2", [39, 34], [29, 18], "complete", None),
        (11, "pass", "NBR-2", "NBR-8", [29, 18], [55, 14], "complete", None),
        (14, "pressure", "RIV-8", None, [58, 20], [55, 14], "applied", None),
        (16, "pass", "NBR-8", "NBR-6", [55, 14], [48, 34], "complete", None),
        (20, "pass", "NBR-6", "NBR-10", [48, 34], [64, 80], "complete", None),
        (24, "pass", "NBR-10", "NBR-7", [64, 80], [70, 62], "complete", None),
        (27, "pressure", "RIV-5", None, [74, 64], [70, 62], "applied", None),
        (29, "pass", "NBR-7", "NBR-9", [70, 62], [83, 47], "complete", None),
        (32, "shot", "NBR-9", None, [83, 47], [100, 51], "saved", .18),
        (33, "recovery", "RIV-1", None, [96, 50], [96, 50], "success", None),
        (35, "pass", "RIV-1", "RIV-3", [96, 50], [81, 58], "complete", None),
        (37, "pass", "RIV-3", "RIV-6", [81, 58], [62, 60], "incomplete", None),
        (38, "tackle", "NBR-7", None, [64, 60], [64, 60], "won", None),
        (40, "pass", "NBR-7", "NBR-9", [64, 60], [82, 48], "complete", None),
        (42, "pass", "NBR-9", "NBR-11", [82, 48], [89, 54], "complete", None),
        (45, "shot", "NBR-11", None, [89, 54], [100, 48], "goal", .42),
    ]
    events = []
    for i, (second, kind, player, recipient, start, end, outcome, xg) in enumerate(raw, 1):
        event = {"id": f"evt-{i:03}", "second": second, "type": kind, "team": player[:3],
                 "playerId": player, "recipientId": recipient, "start": start, "end": end,
                 "outcome": outcome, "source": "pitchprism-synthetic-v1"}
        if xg is not None:
            event["xg"] = xg  # Scenario input, NOT an official or trained xG prediction.
        events.append(event)
    return {"id": "synthetic-nbr-riv-001", "schemaVersion": 1, "synthetic": True,
            "title": "The switch that changed the attack", "seed": "pitchprism-football-v1",
            "durationSeconds": 48, "clockStartSeconds": 4060,
            "coordinateSystem": {"unit": "percent", "lengthMetres": 105, "widthMetres": 68,
                                 "homeAttacks": "left-to-right"},
            "provenance": "Original fictional scenario; names, events, coordinates and shot xG inputs are synthetic.",
            "teams": teams, "roster": roster, "events": events,
            "production": {"mode": "editorial", "timeline": [
                {"kind": "live", "outputStart": 0, "outputEnd": 20, "sourceStart": 0, "sourceEnd": 20},
                {"kind": "freeze", "outputStart": 20, "outputEnd": 24, "sourceStart": 20, "sourceEnd": 20},
                {"kind": "live", "outputStart": 24, "outputEnd": 52, "sourceStart": 20, "sourceEnd": 48},
                {"kind": "replay", "outputStart": 52, "outputEnd": 60, "sourceStart": 38, "sourceEnd": 46},
                {"kind": "freeze", "outputStart": 60, "outputEnd": 64, "sourceStart": 46, "sourceEnd": 46}]}}


if __name__ == "__main__":
    target = Path(__file__).with_name("match.json")
    target.write_text(json.dumps(build_match(), indent=2) + "\n")
    print(target)
