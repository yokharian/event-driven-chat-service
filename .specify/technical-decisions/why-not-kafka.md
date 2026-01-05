# Decision: Rejecting Apache Kafka

**Status**: Rejected  
**Date**: 2026-01-02  
**Context**: Evaluating Kafka for event-driven messaging in an MVP chat service requiring reliable delivery with minimal
operational complexity.

## Executive Summary

We rejected Kafka because it's optimized for organizational-scale problems we don't have: replayable event logs,
multi-consumer analytics pipelines, and massive throughput. The operational complexity of partitions, rebalancing, lag
monitoring, and storage growth is overkill for our MVP needs.

## Problem Statement

We need reliable, asynchronous message delivery between services with ordering guarantees per conversation. The solution
must minimize operational overhead and support our MVP scale without requiring deep messaging infrastructure expertise
or complex cluster management.

## Decision Rationale

Kafka excels at problems we don't have: replayable event logs for analytics, strict ordering across thousands of
partitions, and massive throughput (MB/s). These capabilities come with significant operational costs: partition
management, consumer rebalancing, lag monitoring, disk growth planning, and careful schema evolution.

Even managed Kafka services (MSK, Confluent Cloud) leak operational complexity and cost. You still must understand
partitions, replication factors, consumer groups, and failure modes. The mental model and operational burden remain high
compared to simpler queue-based solutions.

Kafka shines when multiple teams consume the same event stream for different purposes at organizational scale. Our MVP
chat service doesn't need replay from day one, doesn't need ordering across thousands of partitions, and doesn't need
MB/s throughput. We need reliable delivery of chat messages with per-conversation ordering—a problem better solved by
simpler messaging primitives.

The decision acknowledges Kafka's strengths but recognizes it solves scale problems we haven't reached. Choosing Kafka
would introduce unnecessary complexity, operational risk, and cost for capabilities we don't require. If we later need
replay, multi-consumer analytics, or massive throughput, we can migrate to Kafka with clear justification. For now,
simpler solutions provide better velocity and reliability.