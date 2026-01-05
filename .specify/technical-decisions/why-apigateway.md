# Decision: Use AWS API Gateway

**Status**: Accepted  
**Date**: 2026-01-04  
**Context**: Need a serverless API solution that supports both REST and WebSocket protocols with built-in
authentication, throttling, and seamless Lambda integration for our event-driven chat service.

## Executive Summary

We chose AWS API Gateway because it provides full WebSocket compatibility in a serverless architecture, integrates
seamlessly with Cognito for OAuth authorization per endpoint, offers built-in throttling, and enables REST API
deployment with FastAPI-like ease while leveraging Lambda Powertools for observability.

## Problem Statement

We need a serverless API gateway that supports both REST endpoints and WebSocket connections for real-time chat
functionality. The solution must provide per-endpoint authorization via OAuth/Cognito, rate limiting/throttling
capabilities, and integrate smoothly with AWS Lambda for our backend services. Success means deploying APIs with minimal
infrastructure management while maintaining security and observability.

## Decision Rationale

API Gateway addresses our core requirements through its native serverless architecture and comprehensive feature set.
The full WebSocket compatibility eliminates the need for separate WebSocket infrastructure, allowing us to handle
real-time chat connections alongside REST endpoints in a unified service. This reduces operational complexity and aligns
with our serverless-first approach.

The integration with AWS Cognito enables fine-grained authorization at the endpoint level, supporting OAuth flows
without custom authentication middleware. This built-in security model reduces development time and operational risk
compared to managing authentication infrastructure separately. The per-endpoint authorization capability allows us to
implement different access controls for different API operations, which is essential for a chat service with varying
permission requirements.

Built-in throttling and rate limiting protect our backend services from traffic spikes and abuse without requiring
additional infrastructure or custom rate-limiting logic. This is particularly valuable for a public-facing chat service
where traffic patterns can be unpredictable.

The seamless Lambda integration means we can deploy REST APIs with a development experience similar to FastAPI—writing
handler functions that API Gateway automatically routes and invokes. Combined with AWS Lambda Powertools, we get
structured logging, distributed tracing, and error handling out of the box, significantly improving our observability
without additional tooling.

The primary risk is vendor lock-in to AWS, but this aligns with our broader AWS-native architecture decision. Cost can
scale with traffic, but API Gateway's pricing is predictable and manageable for our MVP scale. The WebSocket connection
management requires careful state handling, but API Gateway's connection management APIs provide the necessary
primitives.

By choosing API Gateway, we avoid the operational overhead of managing API infrastructure, reduce security
implementation complexity, and gain built-in observability patterns that accelerate development while maintaining
production-grade reliability.
