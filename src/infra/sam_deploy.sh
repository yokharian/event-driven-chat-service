#!/bin/bash
set -euo pipefail

DEPLOY_LOG=${DEPLOY_LOG:-./sam-deploy.log}
exec > >(tee -a "$DEPLOY_LOG") 2>&1
echo "--- $(date -Iseconds) sam_deploy start (log: ${DEPLOY_LOG})"

PARAM_OVERRIDES="${PARAMETER_OVERRIDES:-$DEFAULT_PARAMETER_OVERRIDES}"
EXTRA_ARGS="${EXTRA_SAM_ARGS:-}"

echo "Building SAM application from ${SOURCE_TEMPLATE_FILE} into ${BUILD_DIR}"
sam build --template-file "${SOURCE_TEMPLATE_FILE}"

[[ -f "${TEMPLATE_FILE}" ]] || { echo "Template file not found: ${TEMPLATE_FILE}" >&2; exit 1; }

echo "Deploying stack ${STACK_NAME}"
sam deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE_FILE}" \
  --parameter-overrides ${PARAM_OVERRIDES} \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region "${AWS_DEFAULT_REGION}" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  ${EXTRA_ARGS}