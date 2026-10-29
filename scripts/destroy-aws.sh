#!/usr/bin/env bash
# ==============================================================================
# Tear down and clean up AWS Cloud VPS resources
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

AWS_BIN="/opt/homebrew/bin/aws"
if ! command -v "${AWS_BIN}" >/dev/null 2>&1; then
    AWS_BIN="aws"
fi

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
KEY_NAME="ecommerce-vps-key"
KEY_FILE="${ROOT_DIR}/${KEY_NAME}.pem"
SG_NAME="ecommerce-vps-sg"
TAG_NAME="ecommerce-k3s-cloud-vps"

echo "===================================================================="
echo "⚠️  AWS CLOUD VPS RESOURCE TEARDOWN"
echo "===================================================================="

# 1. Terminate Instances
INSTANCE_IDS=$("${AWS_BIN}" ec2 describe-instances \
    --region "${REGION}" \
    --filters "Name=tag:Name,Values=${TAG_NAME}" "Name=instance-state-name,Values=running,pending,stopped" \
    --query "Reservations[*].Instances[*].InstanceId" \
    --output text)

if [ -n "${INSTANCE_IDS}" ] && [ "${INSTANCE_IDS}" != "None" ]; then
    echo "Terminating EC2 instance(s): ${INSTANCE_IDS}..."
    "${AWS_BIN}" ec2 terminate-instances --region "${REGION}" --instance-ids ${INSTANCE_IDS}
    echo "Waiting for termination..."
    "${AWS_BIN}" ec2 wait instance-terminated --region "${REGION}" --instance-ids ${INSTANCE_IDS}
    echo "Instance(s) terminated."
else
    echo "No running or stopped instances found."
fi

# 2. Delete Key Pair
if "${AWS_BIN}" ec2 describe-key-pairs --region "${REGION}" --key-names "${KEY_NAME}" >/dev/null 2>&1; then
    echo "Deleting AWS Key Pair: ${KEY_NAME}..."
    "${AWS_BIN}" ec2 delete-key-pair --region "${REGION}" --key-name "${KEY_NAME}"
fi
rm -f "${KEY_FILE}" "${ROOT_DIR}/kubeconfig-aws.yaml"

# 3. Delete Security Group
VPC_ID=$("${AWS_BIN}" ec2 describe-vpcs --region "${REGION}" --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text 2>/dev/null || true)
SG_ID=$("${AWS_BIN}" ec2 describe-security-groups --region "${REGION}" --filters "Name=group-name,Values=${SG_NAME}" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [ -n "${SG_ID}" ] && [ "${SG_ID}" != "None" ]; then
    echo "Deleting Security Group: ${SG_ID}..."
    sleep 5 # Allow network interfaces to detach
    "${AWS_BIN}" ec2 delete-security-group --region "${REGION}" --group-id "${SG_ID}" || echo "Could not delete SG immediately (might take a moment to detach)."
fi

echo "✅ All AWS Cloud VPS resources cleaned up successfully!"
