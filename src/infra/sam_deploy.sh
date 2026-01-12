#!/usr/bin/env bash
set -euo pipefail

DEPLOY_LOG=${DEPLOY_LOG:-./sam-deploy.log}
exec > >(tee -a "$DEPLOY_LOG") 2>&1
echo "--- $(date -Iseconds) sam_deploy start (log: ${DEPLOY_LOG})"

command -v aws >/dev/null 2>&1 || { echo "AWS CLI not found on PATH" >&2; exit 1; }
command -v sam >/dev/null 2>&1 || { echo "AWS SAM CLI not found on PATH" >&2; exit 1; }

STACK_NAME=${STACK_NAME:-chat-service-stack}
ENVIRONMENT=${ENVIRONMENT:-local}
STATE_TABLE_NAME=${STATE_TABLE_NAME:-simplechat_connections}
EVENT_BUS_TABLE_NAME=${EVENT_BUS_TABLE_NAME:-chat_events}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
SOURCE_TEMPLATE_FILE=${SOURCE_TEMPLATE_FILE:-src/infra/template-dev.yaml}
BUILD_DIR=${BUILD_DIR:-.aws-sam/build}
TEMPLATE_FILE=${TEMPLATE_FILE:-${BUILD_DIR}/template.yaml}
PACKAGED_TEMPLATE_FILE=${PACKAGED_TEMPLATE_FILE:-.aws-sam/build/packaged-template.yaml}
DEPLOYMENT_BUCKET=${DEPLOYMENT_BUCKET:-}
S3_PREFIX=${S3_PREFIX:-chat-service}
PARAMETER_OVERRIDES=${PARAMETER_OVERRIDES:-}
EXTRA_SAM_ARGS=${EXTRA_SAM_ARGS:-}

ensure_bucket() {
  local bucket="$1"
  local region="${AWS_DEFAULT_REGION}"
  local endpoint_arg=""
  if [ -n "${AWS_ENDPOINT_URL:-}" ]; then
    endpoint_arg="--endpoint-url ${AWS_ENDPOINT_URL}"
  fi

  echo "Ensuring S3 bucket '${bucket}' exists (region: ${region})"
  if aws s3api head-bucket --bucket "${bucket}" ${endpoint_arg} 2>/dev/null; then
    echo "Bucket '${bucket}' already exists"
    return 0
  fi

  if [ "${region}" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "${bucket}" ${endpoint_arg}
  else
    aws s3api create-bucket \
      --bucket "${bucket}" \
      --create-bucket-configuration LocationConstraint="${region}" \
      ${endpoint_arg}
  fi
}

echo "Building SAM application from '${SOURCE_TEMPLATE_FILE}' into '${BUILD_DIR}'"
sam build --template-file "${SOURCE_TEMPLATE_FILE}"

[ -f "${TEMPLATE_FILE}" ] || { echo "Template file not found: ${TEMPLATE_FILE}" >&2; exit 1; }

if [ -z "${PARAMETER_OVERRIDES}" ]; then
  PARAMETER_OVERRIDES="Environment=${ENVIRONMENT} StateTableName=${STATE_TABLE_NAME} EventBusTableName=${EVENT_BUS_TABLE_NAME}"
fi

if [ -z "${DEPLOYMENT_BUCKET}" ]; then
  echo "DEPLOYMENT_BUCKET is required for 'sam package'" >&2
  exit 1
fi

ensure_bucket "${DEPLOYMENT_BUCKET}"

echo "Packaging template '${TEMPLATE_FILE}' to '${PACKAGED_TEMPLATE_FILE}' (bucket: ${DEPLOYMENT_BUCKET}, prefix: ${S3_PREFIX})"
sam package \
  --template-file "${TEMPLATE_FILE}" \
  --s3-bucket "${DEPLOYMENT_BUCKET}" \
  --s3-prefix "${S3_PREFIX}" \
  --output-template-file "${PACKAGED_TEMPLATE_FILE}"

echo "Deploying stack '${STACK_NAME}' with template '${PACKAGED_TEMPLATE_FILE}'"

sam deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${PACKAGED_TEMPLATE_FILE}" \
  --parameter-overrides ${PARAMETER_OVERRIDES} \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region "${AWS_DEFAULT_REGION}" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  ${EXTRA_SAM_ARGS}

