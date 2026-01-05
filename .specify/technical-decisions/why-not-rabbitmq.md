# Decision: Rejecting RabbitMQ

**Status**: Rejected  
**Date**: 2026-01-02  
**Context**: Evaluating RabbitMQ as a message broker for event-driven chat service requiring reliable delivery with
minimal operational overhead.

## Executive Summary

We rejected RabbitMQ because it requires operating brokers or trusting managed vendors, introduces clustering
complexity, and adds more moving parts than managed queue services for similar outcomes. The rich routing capabilities
don't justify the operational burden for our MVP needs.

## Problem Statement

We need reliable message delivery between loosely coupled services with minimal operational complexity. The solution
must support our MVP scale without requiring broker management, cluster operations, or deep messaging infrastructure
expertise.

## Decision Rationale

RabbitMQ's strengths—rich routing (topics, headers, fanout), mature AMQP model, flexible delivery semantics—are valuable
for complex messaging patterns we don't need. Our chat service requires simple point-to-point or pub-sub patterns that
don't benefit from RabbitMQ's sophisticated routing capabilities.

The operational costs are significant: you must operate brokers or trust a managed vendor, clustering is complex and
risky, upgrades require careful planning, and memory pressure can cascade failures. Scaling RabbitMQ is not "infinite"
but requires careful capacity planning and operational expertise.

RabbitMQ is excellent when you need complex routing, control your infrastructure, and have operational maturity. Our
requirements favor zero-ops solutions with simpler semantics and reliability over flexibility. Managed queue services
like SQS provide the reliability we need without the operational burden.

The decision prioritizes operational simplicity and reliability over routing flexibility. While RabbitMQ offers more
sophisticated messaging patterns, those capabilities don't justify the operational complexity for our MVP. If we later
need complex routing or have operational maturity to manage brokers, RabbitMQ becomes a viable option. For now, simpler
managed services provide better velocity and fewer failure modes.