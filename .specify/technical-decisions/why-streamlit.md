# Decision: Streamlit for Frontend

**Status**: Accepted  
**Date**: 2026-01-02  
**Context**: Selecting a frontend framework for a minimal chat service prototype requiring rapid development,
simplicity, and ease of deployment.

## Executive Summary

We chose Streamlit over React, Astro, and other modern frameworks because it provides the fastest path to a working chat
interface with minimal code, simple deployment, and built-in WebSocket support. The trade-off of less UI flexibility is
acceptable for MVP velocity.

## Problem Statement

We need a frontend that allows clients to send and receive chat messages with minimal development effort. The solution
must support WebSocket connections, deploy easily, and enable rapid prototyping without requiring extensive frontend
infrastructure or build tooling.

## Decision Rationale

Streamlit's core value is simplicity: you write Python scripts that automatically generate interactive web UIs. For a
chat service prototype, this means focusing on business logic (message handling, WebSocket connections) rather than
React components, state management, routing, and build tooling.

While the team has experience with React, Astro, Tailwind CSS, Vite, and TypeScript, those tools introduce complexity
that doesn't accelerate MVP development. Streamlit's "KISS" (Keep It Simple, Stupid) philosophy aligns with our goal of
building a minimal chat service quickly.

Deployment simplicity is significant: Streamlit apps deploy as simple Python applications without complex build
pipelines, bundling, or CDN configuration. This reduces operational overhead and enables faster iteration cycles
compared to modern JavaScript toolchains.

The decision acknowledges Streamlit's limitations: less UI flexibility, Python-based (not JavaScript), and different
mental model than component-based frameworks. However, for an MVP chat interface, these trade-offs are acceptable. If we
later need sophisticated UI, real-time animations, or complex state management, we can migrate to React or other
frameworks with clear justification.

The choice prioritizes development velocity and operational simplicity over UI sophistication. Streamlit gets us to a
working prototype fastest, which is the primary goal. We can always refactor to a more flexible framework once we
validate the core chat functionality and understand actual requirements.