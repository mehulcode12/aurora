# Aurora
# 1. Aurora

## Overview

Aurora is a real-time, multi-agent field assistant that helps frontline teams gather information, triage situations by voice, and coordinate actions—all in under a minute.

## Core Components

### 1. Voice Triage Agent

- Accepts 60s field voice clips
- Outputs incident severity, key facts, and suggested actions
- Uses LiveKit + Cerebras for ultra-fast inference

### 2. RAG Evidence Agent

- Searches ingested corpus (manuals, SOPs, guides)
- Returns exact citations supporting recommended actions
- Vector DB + Llama retrieval architecture

### 3. Orchestration Agent (Dockerized)

- Decides escalation paths and coordination actions
- Calls microservices for tickets, notifications
- All services run in containers via Docker

## Technical Architecture

```
┌────────────────┐  ┌──────────────────┐  ┌───────────────────┐
│ Voice Capture  │  │ Multi-Agent      │  │ Evidence & Action │
│                │──┤ Orchestrator     │──┤                   │
│ LiveKit + ASR  │  │ Cerebras + Llama │  │ RAG + Microagents │
└────────────────┘  └──────────────────┘  └───────────────────┘
```

## Sponsor Integration

### Cerebras

- Ultra low-latency multi-agent orchestration
- Benchmark: 3 parallel agents in 420ms vs 2.4s baseline
- Enables real-time voice response capabilities

### Meta (Llama)

- Provides instruction-tuned reasoning for triage
- Grounded responses with fewer hallucinations
- LoRA adapters for domain-specific understanding

### Docker

- Containerizes all components for easy deployment
- MCP Gateway for reliable scaling
- One-click demo via docker-compose

## 7-Day Implementation Plan

1. **Day 1**: Skeleton architecture, prompts, simple UI
2. **Day 2**: Voice pipeline + ASR integration
3. **Day 3**: Vector DB + RAG citation system
4. **Day 4**: Cerebras integration and benchmarking
5. **Day 5**: Dockerize everything, create compose file
6. **Day 6**: Polish UI, record demo video
7. **Day 7**: Final testing and submission

## Impact & Differentiation

- Reduces critical decision time from minutes to seconds
- Provides evidence-backed recommendations with citations
- Automates coordination tasks to focus humans on exceptions

## Demo Highlights

- 45s field report → immediate triage result
- Citation display showing exact SOP sections
- One-click escalation with automatic notifications
- Cerebras latency benchmarks showing speed advantage
