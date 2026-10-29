#!/usr/bin/env bash
# ==============================================================================
# Automated AWS Cloud VPS (k3s) Deployment Script
# WooCommerce Hosting Platform with Team MCP Gateway on Kubernetes
# ==============================================================================
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

AWS_BIN="/opt/homebrew/bin/aws"
if ! command -v "${AWS_BIN}" >/dev/null 2>&1; then
    AWS_BIN="aws"
fi

INSTANCE_TYPE="${AWS_INSTANCE_TYPE:-t3.medium}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
KEY_NAME="${AWS_KEY_NAME:-ecommerce-vps-key}"
KEY_FILE="${ROOT_DIR}/${KEY_NAME}.pem"
SG_NAME="ecommerce-vps-sg"
TAG_NAME="ecommerce-k3s-cloud-vps"

echo "===================================================================="
echo "🚀 AWS CLOUD VPS (k3s) DEPLOYMENT INITIALIZER"
echo "===================================================================="
echo "Region:         ${REGION}"
echo "Instance Type:  ${INSTANCE_TYPE}"
echo "Key Name:       ${KEY_NAME}"
echo "Security Group: ${SG_NAME}"
echo "===================================================================="

# 1. Verify AWS CLI and Credentials
echo "🔍 [1/8] Verifying AWS Credentials..."
if ! "${AWS_BIN}" sts get-caller-identity >/dev/null 2>&1; then
    echo ""
    echo "❌ AWS Credentials not found or invalid!"
    echo "Please configure your AWS credentials using one of the following methods:"
    echo "  1) Run: aws configure"
    echo "  2) Or export the environment variables:"
    echo "     export AWS_ACCESS_KEY_ID='your-access-key'"
    echo "     export AWS_SECRET_ACCESS_KEY='your-secret-key'"
    echo "     export AWS_DEFAULT_REGION='${REGION}'"
    echo ""
    exit 1
fi

ACCOUNT_ID=$("${AWS_BIN}" sts get-caller-identity --query "Account" --output text)
USER_ARN=$("${AWS_BIN}" sts get-caller-identity --query "Arn" --output text)
echo "✅ Authenticated as: ${USER_ARN} (Account: ${ACCOUNT_ID})"

# 2. Get Default VPC
echo "🌐 [2/8] Fetching Default VPC..."
VPC_ID=$("${AWS_BIN}" ec2 describe-vpcs \
    --region "${REGION}" \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text)

if [ "${VPC_ID}" == "None" ] || [ -z "${VPC_ID}" ]; then
    echo "Default VPC not found. Fetching first available VPC..."
    VPC_ID=$("${AWS_BIN}" ec2 describe-vpcs \
        --region "${REGION}" \
        --query "Vpcs[0].VpcId" \
        --output text)
fi
echo "Using VPC: ${VPC_ID}"
if [ "${VPC_ID}" == "None" ] || [ -z "${VPC_ID}" ]; then
    echo "Error: No VPC is available in ${REGION}."
    exit 1
fi

# Resolve these before making any changes to AWS resources.
ADMIN_CIDR="${AWS_ADMIN_CIDR:-}"
if [ -z "${ADMIN_CIDR}" ]; then
    ADMIN_IP=$(curl --fail --silent --show-error --max-time 10 https://checkip.amazonaws.com)
    if [[ ! "${ADMIN_IP}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Error: Set AWS_ADMIN_CIDR to your trusted administration CIDR."
        exit 1
    fi
    ADMIN_CIDR="${ADMIN_IP}/32"
fi
ARCH=$("${AWS_BIN}" ec2 describe-instance-types --region "${REGION}" \
    --instance-types "${INSTANCE_TYPE}" \
    --query 'InstanceTypes[0].ProcessorInfo.SupportedArchitectures[0]' --output text)
case "${ARCH}" in
    x86_64) AMI_ARCH=amd64 ;;
    arm64) AMI_ARCH=arm64 ;;
    *) echo "Error: Unsupported instance architecture: ${ARCH}"; exit 1 ;;
esac

# 3. Create or Update Security Group
echo "🛡️  [3/8] Configuring Security Group (${SG_NAME})..."
SG_ID=$("${AWS_BIN}" ec2 describe-security-groups \
    --region "${REGION}" \
    --filters "Name=group-name,Values=${SG_NAME}" "Name=vpc-id,Values=${VPC_ID}" \
    --query "SecurityGroups[0].GroupId" \
    --output text 2>/dev/null || true)

if [ "${SG_ID}" == "None" ] || [ -z "${SG_ID}" ]; then
    echo "Creating Security Group ${SG_NAME}..."
    SG_ID=$("${AWS_BIN}" ec2 create-security-group \
        --region "${REGION}" \
        --group-name "${SG_NAME}" \
        --description "Inbound access for eCommerce MCP Stack on k3s" \
        --vpc-id "${VPC_ID}" \
        --query "GroupId" \
        --output text)

    echo "Authorizing public HTTP/HTTPS and administration from ${ADMIN_CIDR}..."
    "${AWS_BIN}" ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 22 --cidr "${ADMIN_CIDR}"
    "${AWS_BIN}" ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 80 --cidr 0.0.0.0/0
    "${AWS_BIN}" ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 443 --cidr 0.0.0.0/0
    "${AWS_BIN}" ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 6443 --cidr "${ADMIN_CIDR}"
else
    echo "Security Group already exists: ${SG_ID}"
fi

# 4. Create or Verify Key Pair
echo "🔑 [4/8] Configuring SSH Key Pair (${KEY_NAME})..."
if [ ! -f "${KEY_FILE}" ]; then
    # Check if key pair already exists in AWS
    EXISTS=$("${AWS_BIN}" ec2 describe-key-pairs --region "${REGION}" --key-names "${KEY_NAME}" --query "KeyPairs[0].KeyName" --output text 2>/dev/null || true)
    if [ "${EXISTS}" == "${KEY_NAME}" ]; then
        echo "Error: Remote key ${KEY_NAME} exists but its local private key is missing."
        echo "Restore the private key or choose a new AWS_KEY_NAME. No key was deleted."
        exit 1
    fi

    echo "Generating new SSH key pair: ${KEY_FILE}..."
    "${AWS_BIN}" ec2 create-key-pair \
        --region "${REGION}" \
        --key-name "${KEY_NAME}" \
        --query "KeyMaterial" \
        --output text > "${KEY_FILE}"
    chmod 400 "${KEY_FILE}"
    echo "Saved SSH private key to: ${KEY_FILE}"
else
    echo "Using existing local SSH key: ${KEY_FILE}"
fi

# 5. Fetch Latest Ubuntu 24.04 LTS AMI
echo "📦 [5/8] Locating Ubuntu 24.04 LTS AMI..."
AMI_ID=$("${AWS_BIN}" ec2 describe-images \
    --region "${REGION}" \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-${AMI_ARCH}-server-*" \
              "Name=state,Values=available" \
    --query "sort_by(Images, &CreationDate)[-1].ImageId" \
    --output text)

if [ "${AMI_ID}" == "None" ] || [ -z "${AMI_ID}" ]; then
    echo "Error: No Ubuntu AMI found for ${ARCH} in ${REGION}."
    exit 1
fi
echo "Using AMI: ${AMI_ID}"

# 6. Check for Existing Running Instance
EXISTING_INSTANCE_ID=$("${AWS_BIN}" ec2 describe-instances \
    --region "${REGION}" \
    --filters "Name=tag:Name,Values=${TAG_NAME}" "Name=instance-state-name,Values=running,pending" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text 2>/dev/null || true)

if [ "${EXISTING_INSTANCE_ID}" != "None" ] && [ -n "${EXISTING_INSTANCE_ID}" ]; then
    echo "Found existing running EC2 instance: ${EXISTING_INSTANCE_ID}"
    INSTANCE_ID="${EXISTING_INSTANCE_ID}"
else
    # 7. Launch EC2 Instance with Cloud-Init UserData
    echo "🚀 [6/8] Launching EC2 ${INSTANCE_TYPE} instance..."

    USER_DATA_FILE=$(mktemp)
    cat << 'EOF' > "${USER_DATA_FILE}"
#!/bin/bash
set -e

# Update and install dependencies
apt-get update -y
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git jq

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Install Helm
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Get Public IP for k3s TLS SAN
IMDS_TOKEN=$(curl -fsS -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 300' http://169.254.169.254/latest/api/token)
PUBLIC_IP=$(curl -fsS -H "X-aws-ec2-metadata-token: ${IMDS_TOKEN}" http://169.254.169.254/latest/meta-data/public-ipv4)

# Install k3s with Traefik enabled and TLS SAN for remote kubectl
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--write-kubeconfig-mode 600 --tls-san ${PUBLIC_IP}" sh -

# Setup kubeconfig for ubuntu user
mkdir -p /home/ubuntu/.kube
cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube
chmod 700 /home/ubuntu/.kube
chmod 600 /home/ubuntu/.kube/config
echo "export KUBECONFIG=/home/ubuntu/.kube/config" >> /home/ubuntu/.bashrc

echo "K3s Cloud-Init Complete!" > /home/ubuntu/cloud-init-done.txt
EOF

    RUN_RES=$("${AWS_BIN}" ec2 run-instances \
        --region "${REGION}" \
        --image-id "${AMI_ID}" \
        --instance-type "${INSTANCE_TYPE}" \
        --key-name "${KEY_NAME}" \
        --security-group-ids "${SG_ID}" \
        --metadata-options HttpTokens=required,HttpEndpoint=enabled,HttpPutResponseHopLimit=2 \
        --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":60,\"VolumeType\":\"gp3\",\"Encrypted\":true,\"DeleteOnTermination\":true}}]" \
        --user-data "file://${USER_DATA_FILE}" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${TAG_NAME}}]" \
        --output json)

    rm -f "${USER_DATA_FILE}"
    INSTANCE_ID=$(echo "${RUN_RES}" | jq -r ".Instances[0].InstanceId")
    echo "Launched Instance ID: ${INSTANCE_ID}"
fi

echo "⏳ Waiting for instance ${INSTANCE_ID} to be in running state..."
"${AWS_BIN}" ec2 wait instance-running --region "${REGION}" --instance-ids "${INSTANCE_ID}"

PUBLIC_IP=$("${AWS_BIN}" ec2 describe-instances \
    --region "${REGION}" \
    --instance-ids "${INSTANCE_ID}" \
    --query "Reservations[0].Instances[0].PublicIpAddress" \
    --output text)

echo "✅ Instance is running! Public IP: ${PUBLIC_IP}"

# 8. Wait for SSH & k3s to be Ready
echo "⏳ [7/8] Waiting for SSH and cloud-init completion on ${PUBLIC_IP}..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "${KEY_FILE}" ubuntu@"${PUBLIC_IP}" "test -f /home/ubuntu/cloud-init-done.txt" >/dev/null 2>&1; then
        echo "✅ Cloud VPS initialization complete!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "Waiting for k3s initialization... (${ATTEMPT}/${MAX_ATTEMPTS})"
    sleep 10
done
if [ "${ATTEMPT}" -ge "${MAX_ATTEMPTS}" ]; then
    echo "Error: Cloud initialization did not complete. Check /var/log/cloud-init-output.log on ${PUBLIC_IP}."
    exit 1
fi

# Pull remote kubeconfig to local machine
echo "📥 [8/8] Downloading cluster kubeconfig to local machine..."
KUBECONFIG_LOCAL="${ROOT_DIR}/kubeconfig-aws.yaml"
ssh -o StrictHostKeyChecking=no -i "${KEY_FILE}" ubuntu@"${PUBLIC_IP}" "sudo cat /etc/rancher/k3s/k3s.yaml" > "${KUBECONFIG_LOCAL}"
# Replace 127.0.0.1 with the public IP
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/127.0.0.1/${PUBLIC_IP}/g" "${KUBECONFIG_LOCAL}"
else
    sed -i "s/127.0.0.1/${PUBLIC_IP}/g" "${KUBECONFIG_LOCAL}"
fi
chmod 600 "${KUBECONFIG_LOCAL}"

echo "===================================================================="
echo "🎉 AWS CLOUD VPS (k3s) READY!"
echo "===================================================================="
echo "Public IP:       ${PUBLIC_IP}"
echo "SSH Access:      ssh -i ${KEY_FILE} ubuntu@${PUBLIC_IP}"
echo "Local Kubectl:   KUBECONFIG=${KUBECONFIG_LOCAL} kubectl get nodes"
echo ""
echo "To deploy the ecommerce stack to this cloud VPS, run:"
echo "  ./scripts/deploy-stack-to-aws.sh ${PUBLIC_IP}"
echo "===================================================================="
