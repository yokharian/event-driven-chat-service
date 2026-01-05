# Decision: DynamoDB with Streams as Event Bus

**Status**: Accepted  
**Date**: 2026-01-02  
**Context**: Selecting data store and event bus for event-driven chat service requiring atomic writes, reliable
delivery, and minimal operational overhead.

## Executive Summary

We chose DynamoDB with Streams over SNS+SQS, Kafka, RabbitMQ, and Redis because it provides atomic writes eliminating
dual-write risks, reduces operational complexity through managed services, and aligns with our AWS-native architecture.
The trade-off of limited replay and fan-out flexibility is acceptable for MVP needs.

## Problem Statement

We need a data store that serves as source of truth for messages and automatically generates events for downstream
processing. The solution must provide atomic writes (data + event), maintain ordering per conversation, support
exactly-once processing semantics, and minimize operational burden.

## Decision Rationale

The primary driver is atomicity: writing a message to DynamoDB automatically generates a stream event in the same
operation, eliminating the classic dual-write problem where DB write succeeds but event publish fails (or vice versa).
This atomic coupling of data and events reduces failure modes and simplifies error handling compared to separate SNS+SQS
publishes.

DynamoDB Streams provide built-in change feed without requiring explicit topics, subscriptions, or queue permissions.
For an MVP with smaller teams, fewer resources mean fewer failure modes and faster iteration. The operational burden is
low because DynamoDB, Streams, and Lambda are strongly "managed primitives" in AWS—you inherit AWS reliability and scale
expectations without running brokers.

Exactly-once processing is easier to reason about: while Streams/Lambda provides at-least-once delivery, you can use
idempotency keys with DynamoDB conditional writes and transactions to achieve exactly-once effects at the storage level.
This deterministic state management is critical for chat message ordering and idempotent event processing.

The honest drawbacks: Streams retain records for ~24 hours (limiting replay windows), fan-out is less flexible than
SNS (every consumer attaches to the table's change feed), ordering is per-shard/partition-key (not global), and
throughput is coupled to table write patterns. However, these limitations don't block MVP functionality and can be
addressed later if needed.

The decision prioritizes atomicity, simplicity, and operational ease over replay flexibility and fan-out capabilities.
DynamoDB Streams provides the reliability we need with fewer moving parts. If we later need longer replay windows,
richer routing, or multiple independent consumers, we can migrate to SNS+SQS with clear justification.