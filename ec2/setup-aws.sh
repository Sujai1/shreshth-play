#!/usr/bin/env bash
# ─────────────────────────────────────────────
# ec2/setup-aws.sh  —  one-time AWS prerequisites
# Run this ONCE before your first experiment.
# ─────────────────────────────────────────────
set -euo pipefail
source "$(dirname "$0")/config.sh"

echo "=== AWS One-Time Setup for RL Experiments ==="
echo "Region: $AWS_REGION"
echo ""

# ── 1. Verify AWS credentials ─────────────────
echo "[1/4] Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  ✓ Authenticated as account $ACCOUNT_ID"

# ── 2. Verify the key pair exists in AWS ──────
echo ""
echo "[2/4] Checking key pair '$KEY_NAME' in AWS..."
if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$AWS_REGION" &>/dev/null; then
    echo "  ✓ Key pair '$KEY_NAME' exists in AWS"
else
    echo "  ✗ Key pair '$KEY_NAME' not found in $AWS_REGION."
    echo "    If you created it in a different region, import it:"
    echo "    aws ec2 import-key-pair --key-name $KEY_NAME \\"
    echo "      --public-key-material fileb://<(ssh-keygen -y -f $KEY_PATH)"
    exit 1
fi
if [[ ! -f "$KEY_PATH" ]]; then
    echo "  ✗ Local PEM not found at $KEY_PATH"
    exit 1
fi
chmod 400 "$KEY_PATH"
echo "  ✓ Local PEM found and permissions set"

# ── 3. Create security group (idempotent) ─────
echo ""
echo "[3/4] Setting up security group '$SG_NAME'..."
EXISTING_SG=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || true)

if [[ -z "$EXISTING_SG" || "$EXISTING_SG" == "None" ]]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "$SG_DESC" \
        --region "$AWS_REGION" \
        --query 'GroupId' \
        --output text)
    echo "  ✓ Created security group $SG_ID"
else
    SG_ID="$EXISTING_SG"
    echo "  ✓ Security group already exists: $SG_ID"
fi

# Add SSH inbound rule from current IP (idempotent — ignores duplicate error)
MY_IP=$(curl -s https://ipinfo.io/ip)
echo "  Adding SSH access for your current IP: $MY_IP"
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr "${MY_IP}/32" \
    --region "$AWS_REGION" 2>/dev/null && echo "  ✓ SSH rule added" || echo "  ✓ SSH rule already exists"

# ── 4. Create S3 bucket (idempotent) ──────────
echo ""
echo "[4/4] Setting up S3 bucket '$S3_BUCKET'..."
if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "  ✓ Bucket already exists"
else
    aws s3api create-bucket \
        --bucket "$S3_BUCKET" \
        --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION"
    # Block public access
    aws s3api put-public-access-block \
        --bucket "$S3_BUCKET" \
        --public-access-block-configuration \
          "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    echo "  ✓ Created private bucket s3://$S3_BUCKET"
fi

echo ""
echo "=== Setup complete. You're ready to launch experiments. ==="
echo "    Security group ID: $SG_ID"
echo "    S3 bucket:         s3://$S3_BUCKET"
