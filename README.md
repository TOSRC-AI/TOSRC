# TOSRC

**TOSRC: Tenant-Oriented Open Semantic Routing & Control**

TOSRC is a 100% self-controllable, zero-external-dependency semantic routing engine. It adopts a "universal core package + tenant-separated project" architecture, focusing on local semantic recognition, policy-driven routing, and plugin-based scenario adaptation. It is perfectly suited for offline, intranet, and sensitive deployment environments.

> Important: This project is **not** a large language model application. All semantic recognition capabilities are implemented via a local rule engine and lightweight offline models, with no reliance on cloud-based LLMs.

---

## Architecture

| Component | Positioning | Scenario |
|-----------|-------------|----------|
| **TOSRC-Core** | Universal core package | Encapsulates all tenant-agnostic logic as an independent Python package |
| **TOSRC-Single** | Single-tenant offline edition | Fits offline / private-cloud scenarios such as server rooms, schools, and enterprise intranets. Based on SQLite, no network required |

## Core Capabilities

### 1. Semantic Understanding (NLU)
- Local lightweight rule engine for intent and entity parsing, fully offline-capable
- Emotion analysis: positive/negative detection, intensity scoring, sarcasm detection, fine-grained emotion types
- Semantic classification: TF-IDF + lightweight machine learning
- Zero cloud LLM dependency, fully autonomous

### 2. Policy Routing
- Rule-based, visual configuration of routing policies
- Precise request dispatching to plugins, devices, work orders, etc.
- Full-link request tracing, statistics, and auditing

### 3. Plugin Adaptation
- Standardized plugin interfaces, supporting local plugin loading, unloading, and versioning
- General plugin templates for rapid industry scenario development (rental, campus, smart park, government, etc.)
- Zero-code expansion for new industries via rule packages

### 4. Event Bus
- Generic event publishing and subscription mechanisms
- Supports device events and business event linkage processing
- Extensible to various automated business workflows

## Directory Structure

```
TOSRC/
├── TOSRC-Core/            # Universal core (Python package)
│   ├── src/
│   │   ├── semantic/        # NLU core
│   │   ├── router/          # Routing core
│   │   ├── plugin/          # Plugin management core
│   │   ├── event/           # Event bus core
│   │   └── common/          # Common utilities
│   ├── test/                # Common test cases
│   ├── pyproject.toml       # Packaging config
│   └── README.md            # Core docs
├── TOSRC-Single/          # Single-tenant offline edition
│   ├── config/              # Local config
│   ├── deploy/              # Offline deploy scripts
│   ├── src/
│   │   ├── adapter/         # Offline adapter
│   │   ├── api/             # Business APIs
│   │   └── bionic/          # Bionic architecture DB layer
│   ├── static/              # Admin frontend static assets
│   ├── tests/               # Unit tests
│   ├── main.py              # Entry point
│   └── requirements.txt     # Dependencies
├── docs/                    # Project documentation
│   └── README_zh.md         # Chinese README
├── rules/                   # Rule packages
├── scripts/                 # Utility scripts
├── LICENSE                  # MIT License
└── README.md                # This file
```

## Quick Start

### Single-Tenant Offline Deployment (TOSRC-Single)

Suitable for offline / intranet / server room scenarios. Unzip and run, no network needed:

```bash
cd TOSRC-Single
pip install -r requirements.txt
python main.py
```

Access: http://localhost:8080/admin/

### Core Package Development (TOSRC-Core)

```bash
cd TOSRC-Core
pip install -e .
```

Build and publish:

```bash
python -m build
twine upload dist/*
```

## Architecture Advantages

1. **Fully Autonomous & Controllable**: No third-party LLM dependencies, all capabilities implemented locally, meeting compliance requirements
2. **Scenario-Accurate**: Single-tenant offline lightweight deployment, suitable for sensitive environments
3. **High Maintainability**: Universal core iterates independently, tenant projects only need adapter layers
4. **Highly Extensible**: Plugin-based architecture, on-demand loading, flexible adaptation to various industries
5. **Simple Deployment**: Single-tenant offline "unzip and run", extremely low O&M cost

## Versioning

- **TOSRC-Core**: Semantic versioning (e.g., 1.0.0), major version upgrades on core interface changes
- **TOSRC-Single**: Aligned with Core versions (e.g., 1.0.0-single), only offline adapter layer iterations

## Contribution Guide

This is a monorepo. Please submit to the corresponding directory:

1. Universal features → `TOSRC-Core/`
2. Single-tenant adaptations → `TOSRC-Single/`
3. All commits must pass unit tests

## License

MIT License — see [LICENSE](./LICENSE) for details.

## Documentation

- [中文文档](./docs/README_zh.md)

---
Copyright (c) 2026 TOSRC-AI
