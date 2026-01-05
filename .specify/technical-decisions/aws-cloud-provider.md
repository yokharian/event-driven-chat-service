# Decision: AWS as Cloud Provider

**Status**: Accepted  
**Date**: 2026-01-02  
**Context**: Selecting a cloud provider for a serverless, event-driven chat service requiring local development
capabilities and managed services.

## Executive Summary

We chose AWS over GCP, Azure, and Hostinger primarily for LocalStack compatibility enabling local development, extensive
serverless ecosystem, and team expertise. AWS's battle-tested primitives and shared responsibility model align with our
PaaS-first approach.

## Problem Statement

We need a cloud provider that supports serverless architecture, provides managed services for event-driven patterns,
enables local development workflows, and offers predictable operational models. The provider must support Lambda,
DynamoDB, API Gateway, and WebSocket services with strong documentation and community support.

## Decision Rationale

The primary driver is LocalStack compatibility, which allows us to develop and test AWS services locally without cloud
costs or network latency. This dramatically improves development velocity and enables offline workflows critical for our
team's productivity.

AWS's serverless ecosystem is the most mature, with Lambda, DynamoDB, API Gateway, and WebSocket API providing the exact
primitives we need. While GCP and Azure offer similar services, AWS's documentation, community resources, and
battle-tested reliability at scale provide confidence for production workloads.

The AWS Shared Responsibility Model clearly delineates what AWS manages (availability, durability, replication, scaling,
infrastructure) versus what we own (message format, retry logic, idempotency, business semantics). This explicit
offloading of operational risk aligns with our PaaS-first philosophy.

AWS excels at providing primitives rather than abstractions, which matches our event-driven architecture built on
fundamental building blocks. While AWS's console and APIs can be verbose compared to GCP's cleaner UX, the trade-off is
acceptable given the ecosystem maturity and our team's existing AWS expertise.

The decision acknowledges that we lack deep experience with GCP and Azure, making AWS the pragmatic choice that balances
capability, familiarity, and development tooling. Economies of scale in AWS's managed services provide predictable costs
and reliability that outweigh the potential benefits of alternative providers for our use case.

