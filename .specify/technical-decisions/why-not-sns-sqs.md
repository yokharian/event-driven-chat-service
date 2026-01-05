# Decision: Rejecting SNS+SQS Combo

**Status**: Rejected  
**Date**: 2026-01-02  
**Context**: Evaluating SNS+SQS as the event bus pattern versus DynamoDB Streams for atomic writes and simplified
architecture.

## Executive Summary

We rejected SNS+SQS despite its compelling fan-out and decoupling benefits because it introduces dual-write complexity,
requires more infrastructure objects and IAM wiring, and lacks the atomicity guarantees we need. DynamoDB Streams
provides simpler architecture with atomic data+event writes.

## Problem Statement

We need reliable event delivery with atomic writes to our data store and event bus. The solution must minimize
operational complexity, reduce failure modes, and provide exactly-once processing semantics without requiring outbox
patterns or transactional publish mechanisms.

## Decision Rationale

SNS+SQS is a classic AWS pattern that cleanly separates concerns: SNS handles fan-out and pub-sub (who receives the
event), while SQS provides buffering, retries, backpressure, and independent scaling (how each consumer processes it).
This separation enables independent consumer failure domains, per-consumer retry policies, and easy addition of new
subscribers without touching publishers.

However, SNS+SQS introduces dual-write risk: you must write to DynamoDB (data) and publish to SNS (event) separately,
creating a classic distributed transaction problem. If the DB write succeeds but publish fails (or vice versa), you have
inconsistent state. Mitigating this requires outbox patterns or transactional publish mechanisms that add complexity.

The infrastructure overhead is significant: more infra objects (topics, subscriptions, queues), more IAM wiring, more
places to misconfigure (raw delivery, filter policies, permissions). For an MVP with a smaller team, fewer resources
mean fewer failure modes and faster iteration.

DynamoDB Streams wins on simplicity and atomicity: writing to DynamoDB automatically generates stream events,
eliminating dual-write risk. The data and event are coupled in a single atomic operation, reducing failure modes and
operational complexity. While SNS+SQS offers superior fan-out flexibility and decoupling, those benefits don't justify
the added complexity for our current scale.

The decision prioritizes atomicity and simplicity over fan-out flexibility. If we later need multiple independent
downstream consumers with different processing needs, SNS+SQS becomes the better choice. For now, DynamoDB Streams
provides the reliability we need with fewer moving parts.