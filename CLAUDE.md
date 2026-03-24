# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI agent for the **VPP AI Agent Challenge** (deadline: April 18, 2026), organized by TAS Design Group. The agent must autonomously process documents (PDFs, images, Excel, Word) from Virtual Power Plant (VPP) projects to perform two types of tasks:

1. **Folder Organisation** — Classify each file into 1 of 21 predefined folder categories
2. **Question Answering** — Answer structured questions by extracting information from documents

## Environment Setup

Create a `.env` file with:
```
OPENAI_KEY=<your-openai-api-key>
```

Install Python dependencies (no requirements.txt yet — key packages):
- `openai` — GPT-4o Vision LLM
- `pymupdf` (fitz) — PDF text/image extraction
- `pdfplumber` — PDF table extraction
- `Pillow` — Image processing
- `pydantic` — Data models

## Running Experiments

Benchmark and research scripts are in `experiments/toan/`:

```bash
# PDF extraction benchmark
python experiments/toan/01_pdf_benchmark.py

# Run full processing pipeline on all 44 tasks
python experiments/toan/02_run_pipeline_on_tasks.py

# Test Vision LLM on scanned PDFs
python experiments/toan/05_vision_llm_test.py
```

## Architecture

### Document Processing Pipeline (`src/document_processor/`)

The core module processes raw files into structured `ProcessedDocument` objects:

- **`schema.py`** — Pydantic models: `BBox`, `TextElement`, `TableElement`, `ImageElement`, `PageContent`, `ProcessedDocument`, `KeyEntities`. `ProcessedDocument` is the canonical output of all processors.
- **`pdf_processor.py`** — Two-path strategy:
  - Text PDFs (7.6%): PyMuPDF for text/bbox + pdfplumber for tables
  - Scanned PDFs (92.4%): render pages to PNG at 150 DPI → Vision LLM
  - Entry point: `process_pdf(file_path) → ProcessedDocument`
- **`image_processor.py`** — Heuristic content classification + GPT-4o vision for caption/folder classification. Entry point: `process_image_file(file_path) → ProcessedDocument`
- **`utils.py`** — Date/numeric/language extraction helpers, `save_document()`/`load_document()` for JSON caching, `build_document_summary()` for agent context.

### Planned Agent Architecture (not yet implemented)

Per `docs/approach.md`:
```
Simulator API → Planner → Executor → Validator → Submit
                    ↑          ↓
                 Context/State (shared)
```

- **Planner:** Parse prompt template with LLM → structured subtasks
- **Executor:** Process documents in parallel → search/extract answers
- **Validator:** 3-layer validation (input, plan, output)

### Simulator API (from `docs/api_reference.md`)

```
POST /sessions          → Start/resume session (returns session_id)
GET  /tasks/next        → Get next task (prompt_template + resource tokens)
GET  /download?token=   → Download file by JWT token
POST /submissions       → Submit {session_id, task_id, answers[], thought_log, used_tools[]}
```
Auth: `X-API-Key` header + Bearer token.

## Key Domain Knowledge

### 21 Folder Categories (from `docs/folder_structure_rules.md`)
The classifier must assign each file to one of these tags:
- Tag 01: Spine/Cover (Bìa/Gáy)
- Tag 02: Table of Contents
- Tag 03: Equipment Handover List
- Tag 04: Construction Completion Report
- Tag 05: Construction Schedule
- Tag 06: As-built/Construction Drawings
- Tag 07: Test Reports/Inspection Sheets *(most common, 14%)*
- Tag 08: Self-Inspection Sheets
- Tag 10: Equipment Configuration/List
- Tag 11: PCS/Power Conditioners
- Tag 12: Modules
- Tag 13: Monitoring/Communication Devices
- Tag 14: Equipment Specs
- Tag 15: User/Operation Manuals
- Tag 16: Administrative Documents
- Tag 17: Utility Documents/Responses (Hồ sơ điện lực)
- Tag 18: Warranties
- Tag 19: Construction Photos/Album
- Tag 20: Strength Calculation Documents
- Tag 22: Other/Manifests *(most common overall, 50%)*

### Critical Data Facts
- **92.4% of PDFs are scanned** (no text layer) → Vision LLM is required for nearly all files
- Vision LLM costs ~$0.006/file and takes ~21.8s per file
- 744 total files across 44 tasks (22 QA + 22 Folder Organisation)
- Documents are primarily in Japanese; some Vietnamese and English

## Data & Outputs

- `data/task_<uuid>/task_info.json` — Japanese prompt
- `data/task_<uuid>/task_info_vi.json` — Vietnamese prompt + ground truth tags
- `data/task_<uuid>/Public/` — Resource files for the task
- `experiments/toan/sample_outputs/` — Cached `ProcessedDocument` JSON outputs
- `experiments/toan/results/` — Benchmark metric JSONs
