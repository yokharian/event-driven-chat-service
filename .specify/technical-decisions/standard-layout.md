# Technical Decision Document Layout

Standardized layout for technical decision documents. Each document should follow this structure for consistency.

---

## Document Structure

### 1. Header Section

- **Decision Title**: Clear, descriptive name
- **Status**: Accepted | Rejected | Deferred | Superseded
- **Date**: YYYY-MM-DD
- **Context**: 1-2 sentences describing the problem/need

### 2. Executive Summary

- **One-sentence verdict**: What was decided
- **Key rationale**: 2-3 bullet points explaining why

### 3. Problem Statement

- **What problem are we solving?**
- **Constraints and requirements**

### 4. Decision Rationale

- **Why this option?**: Primary drivers
- **Risk assessment**: What could go wrong
- **Mitigation strategies**: How risks are addressed

---

## Word Count Guidelines

- **Total target**: < 500 words
- **Header**: ~50 words
- **Executive Summary**: ~50 words
- **Problem Statement**: ~50 words
- **Decision Rationale**: ~300 words

---

## Formatting Standards

- Use clear headings (H2 for main sections, H3 for subsections)
- Bullet points for lists
- Bold for emphasis on key terms
- Code blocks for technical examples
- Tables for comparisons when helpful

---

## Example Structure

```markdown
# Decision: Use DynamoDB Streams as Event Bus

**Status**: Accepted  
**Date**: 2026-01-02  
**Context**: Need reliable event delivery with minimal operational overhead

## Executive Summary

We chose DynamoDB Streams over SNS+SQS, Kafka, RabbitMQ, and Redis because it provides atomic writes with our data
model, reduces operational complexity, and aligns with our AWS-native architecture.

## Problem Statement

We need reliable, asynchronous message delivery between loosely coupled services. The solution must handle high
throughput, maintain ordering per conversation, and minimize operational overhead for our MVP.

## Decision Rationale

Primary drivers: atomicity with DynamoDB writes eliminates dual-write risks, managed service reduces operational burden,
and AWS-native patterns simplify our infrastructure. We rejected Kafka (overkill for MVP), RabbitMQ (broker management
overhead), and SNS+SQS (dual-write complexity) because they introduce unnecessary operational complexity or correctness
risks for our current scale.
```
