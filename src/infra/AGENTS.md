Infrastructure-as-code for Lambda, API Gateway, and data stores. Templates separated for LocalStack-friendly dev and
production WebSocket needs.

Stack pieces
------------

- `template-dev.yaml`: core REST/DynamoDB/streams stack; works on LocalStack CE.
- `template-prod.yaml`: adds WebSocket API resources for real AWS.
- `Dockerfile`: batteries-included AWS SAM IaC deployment.
- `sam_deploy.sh`: wrapper to deploy selected template with env vars.
