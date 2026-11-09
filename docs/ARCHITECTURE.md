# Blagden architecture

This document describes how Blagden is built: the modules, their public interfaces, the data that flows between them, how the Python and TypeScript implementations are kept identical, how everything is tested and deployed, and the day-by-day build plan. The science behind each number is in docs/SCIENCE.md; decisions and their reasons are in docs/DECISIONS.md.

## 1. System overview

```mermaid
flowchart LR
  subgraph IN["Inputs"]
    RF["Run file (.fit, .gpx, .tcx)"]
    OM[("Open-Meteo API")]
    PB["PaceBrain checkpoint (optional)"]
  end

  subgraph PY["Python package: blagden"]
    ING["ingest: read, resample to 1 min, quality flags"]
    PHY["physio: ectemp, psi"]
    WX["weather: client + cache, solar, wbgt, heat index, risk, venues"]
    PRD["predict: riegel, pacebrain adapter, heat adjust"]
    BRF["brief: facts, templates, grounding check, optional LLM"]
    CLI["cli: Typer app"]
    CON["constants: every sourced number"]
  end

  subgraph SH["Shared (language neutral)"]
    FX[("fixtures/golden/*.json")]
    TPL[("shared/brief_templates.json, shared/venues.json")]
  end

  subgraph WEB["web: Next.js on Vercel"]
    WIN["lib/ingest: FIT, GPX, TCX in the browser"]
    WCO["lib/core: TypeScript port of physio, solar, wbgt, heat index, risk, riegel, adjust, brief"]
    UI["app: demo page, forecast panel, landing page"]
  end

  RF --> ING --> PHY --> BRF
  OM --> WX --> PRD --> BRF
  WX --> BRF
  PB -. optional extra .-> PRD
  CON --> PHY
  CON --> WX
  CON --> PRD
  PHY --> CLI
  WX --> CLI
  PRD --> CLI
  BRF --> CLI
  RF --> WIN --> WCO --> UI
  OM --> WCO
  TPL --> BRF
  TPL --> WCO
  PHY -. "scripts/make_fixtures.py writes" .-> FX
  WX -. writes .-> FX
  PRD -. writes .-> FX
  FX -. "vitest asserts" .-> WCO
```

Reading the diagram:

- The run file never leaves the device. In the CLI it is read from disk; in the web demo it is parsed in the browser by `lib/ingest` and never uploaded.
- Weather enters from Open-Meteo. The CLI fetches through the Python client with an on-disk cache; the browser fetches directly from the user's device (D-003, D-010).
- Python is the reference implementation. The TypeScript core is a port, and the golden fixtures are the contract between them (section 4).
- `constants` is the single place where a sourced number lives. Every entry names its section in docs/SCIENCE.md and its status, and a test fails if any UNVERIFIED value is referenced by code.
- Shared JSON files hold the brief templates and venue presets, so both languages read the same text and coordinates.
