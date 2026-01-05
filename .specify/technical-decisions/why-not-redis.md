# Decision: Rejecting Redis for Message Queues

**Status**: Rejected  
**Date**: 2026-01-02  
**Context**: Evaluating Redis Streams and queue patterns for event-driven messaging requiring reliable delivery and
durability guarantees.

## Executive Summary

We rejected Redis because queues are not Redis's core strength. While Redis offers low latency and simple mental models,
its memory-first design creates durability risks, requires careful cluster management, and introduces operational
complexity that conflicts with our PaaS-first approach.

## Problem Statement

We need reliable, asynchronous message delivery with durability guarantees and minimal operational overhead. The
solution must handle failures gracefully without data loss and provide predictable behavior under load without requiring
deep infrastructure tuning.

## Decision Rationale

Redis's advantages—extremely low latency, simple mental model, ability to double as cache and queue, Redis Streams with
ordering and replay—are compelling for performance-sensitive use cases. However, Redis is fundamentally memory-first,
making persistence optional and fragile under pressure.

The durability trade-offs are significant: failover risks data loss unless carefully tuned, replication is asynchronous,
and you must manage cluster configuration, replication settings, and persistence modes. Even managed Redis requires
tuning memory, thinking about eviction policies, and debugging failover edge cases.

Redis Streams add complexity: consumer groups are easy to misconfigure, backpressure handling is manual, and scaling
Redis safely is non-trivial. The operational burden of ensuring durability, managing failover, and tuning memory
conflicts with our goal of minimizing infrastructure management.

Redis is infrastructure you must operate, even when managed. This violates our PaaS-first philosophy where we want to
offload operational risk to the cloud provider. SQS and other managed queue services provide "boring" reliability by
design—if a message queue wakes you up at 3am, you chose the wrong one.

The decision prioritizes durability and operational simplicity over latency. While Redis excels at caching and real-time
data structures, message queues require different guarantees. For our chat service, predictable reliability matters more
than microsecond latency, making managed queue services the better choice.