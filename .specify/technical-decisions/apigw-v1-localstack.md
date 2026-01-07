# Decision: API Gateway V1 for LocalStack, V2 for Production

**Status**: Accepted
**Date**: 2026-01-05
**Context**: WebSocket API Gateway deployment strategy for local development (LocalStack) versus production (AWS)

## Executive Summary

We use API Gateway V2 (WebSocket API) for production and a custom local server for LocalStack development. This strategy
involves a strict split: API Gateway V1 is used only for REST API endpoints, while API Gateway V2 is reserved for
WebSocket endpoints. In LocalStack, we rely on V1 for REST and use a Python script to proxy WebSocket requests, ensuring
we effectively "always use V1" capabilities available in the free tier.

## Problem Statement

LocalStack's free tier does not support API Gateway V2 (WebSocket API), which is a paid feature. We need a local
development environment that fully reproduces WebSocket API Gateway behavior without requiring paid LocalStack features
or cloud deployments during development.

## Decision Rationale

We strictly split our API Gateway usage:

- **API Gateway V1**: Used exclusively for REST API endpoints.
- **API Gateway V2**: Used exclusively for WebSocket endpoints.

In the LocalStack environment, to avoid the limitations/costs of V2, we utilize `src/websocket_api/local_server.py`.
This script acts as a proxy that routes WebSocket requests directly to our Lambda handlers internally.

By doing this, we bypass the need for API Gateway V2 in LocalStack. Our local infrastructure configuration therefore
relies "always on V1" (for REST), while the WebSocket functionality is emulated purely via code.

This local server:

1. **Proxies Requests**: Intercepts WebSocket connections and messages, then invokes the corresponding Lambda handlers (
   `onconnect`, `ondisconnect`, `sendmessage`) directly.
2. **Emulates Management API**: Monkey-patches `boto3` to redirect `apigatewaymanagementapi` calls to the local
   connection manager instead of AWS.
3. **Maintains Parity**: Generates event structures identical to AWS API Gateway V2, ensuring Lambda handlers require no
   code changes between environments.

This approach ensures zero-cost local development and maintains a clean separation of concerns, leveraging the
appropriate gateway version for each protocol in production while simplifying the local stack.
