# Product source

The application entry point is **`football/`**. Follow the [project quick start](../README.md#quick-start), [architecture](../docs/football/ARCHITECTURE.md) and [contribution guide](../CONTRIBUTING.md).

| Area | Responsibility |
| --- | --- |
| `football/watch/` | Football player, companion and Tactical Studio |
| `football/data/` | Reviewed observations, English readings, media/source locks and a separate synthetic fixture |
| `football/clip.py` | Source-time snapshots and local editorial explanations |
| `football/foundry.py` | Optional bounded Azure tool loop |
| `football/server.py` | Local API and explicit media delivery |
| `football/scripts/` | Media fetch, render, packaging and static export |
| `watch/` | Shared interface modules and editorial time mapping |
| `broadcast-fx/` | Reusable video rendering primitives |
| `tests/`, `scripts/check.py` | Shared regression tests and full offline gate |

Other service, experiment and infrastructure directories are preserved for regression and historical reference. They are not required to run PitchPrism. [Archived engineering guide](../docs/archive/provenance/ENGINEERING.md).
