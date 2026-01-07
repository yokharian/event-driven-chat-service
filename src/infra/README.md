# Deployment Configuration

## Overview

The chat service has been refactored to separate WebSocket API resources from the main template to accommodate
LocalStack's licensing model.

## Template Structure

### 1. Main Template: src/infra/template-dev.yaml

- **Purpose**: Core infrastructure that works with LocalStack Community Edition

### 2. WebSocket Template: src/infra/template-prod.yaml

- **Purpose**: WebSocket API resources for production deployments only

## Environment Variables

### For Local Development

```yaml
ENVIRONMENT: local
DYNAMODB_ENDPOINT_URL: http://localhost:4566
AWS_ACCESS_KEY_ID: test
AWS_SECRET_ACCESS_KEY: test
AWS_REGION: us-east-1
```

### For Production

```yaml
ENVIRONMENT: prod
AWS_REGION: <your-region>
# AWS credentials via IAM role or environment
```

## Notes

1. **LocalStack Limitations**: API Gateway V2 (WebSocket) is a paid feature in LocalStack Pro
2. **Local Alternative**: Use the FastAPI-based WebSocket server for local development
3. **Worker Functions**: DynamoDB Streams work in LocalStack Community, so agent and delivery workers function normally
4. **Cross-Stack References**: If needed, use CloudFormation exports/imports between the two stacks in production
