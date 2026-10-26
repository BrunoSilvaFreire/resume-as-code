---
id: demo-queue-recovery
type: project
title: Queue Recovery Controller
company: Example Systems
project: Queue Recovery Controller
start_date: 2023-03
end_date: 2023-11
technologies:
  - Python
  - PostgreSQL
  - Prometheus
domains:
  - distributed systems
  - reliability engineering
competencies:
  - performance engineering
  - failure recovery
seniority_signals:
  - architecture ownership
tags:
  - queues
  - backend
visibility: public
verification: verified
related_records:
  - demo-platform-role
  - demo-public-release-report
claims:
  - id: demo-queue-latency
    statement: Cut stalled-work recovery p99 from 12 minutes to 70 seconds with lease-based claims and bounded retries.
    visibility: public
    confidence: verified
    safe_to_paraphrase: true
    evidence:
      - demo-public-release-report
  - id: demo-queue-correctness
    statement: Preserved at-least-once processing while making duplicate work observable and safe to replay.
    visibility: public
    confidence: verified
    safe_to_paraphrase: true
    evidence:
      - demo-public-release-report
---

# Problem

Workers could remain stuck after partial failures, delaying customer-visible processing and forcing manual database intervention.

# My contribution

Designed the claim lifecycle, retry boundaries, observability, and rollout plan.

# Tradeoffs

Kept at-least-once delivery and required idempotent handlers rather than adding a distributed transaction coordinator.

# Alternative resume framings

- Reliability: emphasize recovery time and replay safety.
- Backend: emphasize leases, PostgreSQL coordination, and bounded retries.

