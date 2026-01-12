#!/bin/bash
set -euo pipefail

DEPLOY_LOG=${DEPLOY_LOG:-./sam-deploy.log}
exec > >(tee -a "$DEPLOY_LOG") 2>&1
echo "--- $(date -Iseconds) sam_deploy start (log: ${DEPLOY_LOG})"

PARAM_OVERRIDES="${PARAMETER_OVERRIDES:-$DEFAULT_PARAMETER_OVERRIDES}"
EXTRA_ARGS="${EXTRA_SAM_ARGS:-}"

ENDPOINT_ARG=()
if [[ -n "${AWS_ENDPOINT_URL:-}" ]]; then
  ENDPOINT_ARG+=(--endpoint-url "${AWS_ENDPOINT_URL}")
fi

echo "Building SAM application from ${SOURCE_TEMPLATE_FILE} into ${BUILD_DIR}"
sam build --template-file "${SOURCE_TEMPLATE_FILE}"

[[ -f "${TEMPLATE_FILE}" ]] || { echo "Template file not found: ${TEMPLATE_FILE}" >&2; exit 1; }
[[ -n "${DEPLOYMENT_BUCKET:-}" ]] || { echo "DEPLOYMENT_BUCKET is required" >&2; exit 1; }


echo "Ensuring S3 bucket ${DEPLOYMENT_BUCKET} exists"
if aws s3api head-bucket --bucket "${DEPLOYMENT_BUCKET}" 2>/dev/null;
  then echo "Bucket ${DEPLOYMENT_BUCKET} already exists";

else echo "Creating bucket ${DEPLOYMENT_BUCKET}";
  if aws s3api create-bucket --bucket "${DEPLOYMENT_BUCKET}" 2>/dev/null;
    then echo "Bucket ${DEPLOYMENT_BUCKET} successfully created";

    else echo "ERROR creating ${DEPLOYMENT_BUCKET}";
  fi;
fi;


echo "Packaging template to ${PACKAGED_TEMPLATE_FILE}"
sam package \
  --template-file "${TEMPLATE_FILE}" \
  --s3-bucket "${DEPLOYMENT_BUCKET}" \
  --s3-prefix "${S3_PREFIX}" \
  --output-template-file "${PACKAGED_TEMPLATE_FILE}"

echo "Deploying stack ${STACK_NAME}"
sam deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${PACKAGED_TEMPLATE_FILE}" \
  --parameter-overrides ${PARAM_OVERRIDES} \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region "${AWS_DEFAULT_REGION}" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  ${EXTRA_ARGS}