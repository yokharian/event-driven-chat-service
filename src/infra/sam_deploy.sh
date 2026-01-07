#!/usr/bin/env bash
set -euo pipefail

command -v sam >/dev/null 2>&1 || { echo "AWS SAM CLI not found on PATH" >&2; exit 1; }

STACK_NAME=${STACK_NAME:-chat-service-stack}
ENVIRONMENT=${ENVIRONMENT:-local}
STATE_TABLE_NAME=${STATE_TABLE_NAME:-simplechat_connections}
EVENT_BUS_TABLE_NAME=${EVENT_BUS_TABLE_NAME:-chat_events}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
TEMPLATE_FILE=${TEMPLATE_FILE:-.aws-sam/build/template.yaml}
PARAMETER_OVERRIDES=${PARAMETER_OVERRIDES:-}
EXTRA_SAM_ARGS=${EXTRA_SAM_ARGS:-}

[ -f "${TEMPLATE_FILE}" ] || { echo "Template file not found: ${TEMPLATE_FILE}" >&2; exit 1; }

if [ -z "${PARAMETER_OVERRIDES}" ]; then
  PARAMETER_OVERRIDES="Environment=${ENVIRONMENT} StateTableName=${STATE_TABLE_NAME} EventBusTableName=${EVENT_BUS_TABLE_NAME}"
fi

echo "Deploying stack '${STACK_NAME}' with template '${TEMPLATE_FILE}'"

sam deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE_FILE}" \
  --parameter-overrides ${PARAMETER_OVERRIDES} \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region "${AWS_DEFAULT_REGION}" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  ${EXTRA_SAM_ARGS}

