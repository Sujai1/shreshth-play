#!/usr/bin/env bash
# ─────────────────────────────────────────────
# ec2/launch.sh  —  spin up a spot GPU instance
#
# Usage:
#   ./ec2/launch.sh [instance-type] [experiment-name]
#   ./ec2/launch.sh g4dn.xlarge my-reward-experiment
#
# Outputs:
#   - SSH command ready to copy-paste
#   - Updates ~/.ssh/config with host alias
#   - Appends entry to ec2/.instances registry
# ─────────────────────────────────────────────
set -euo pipefail
source "$(dirname "$0")/config.sh"

INSTANCE_TYPE="${1:-$DEFAULT_INSTANCE_TYPE}"
EXPERIMENT_NAME="${2:-experiment-$(date +%Y%m%d-%H%M%S)}"

echo "=== Launching EC2 Spot Instance ==="
echo "  Type:       $INSTANCE_TYPE"
echo "  Experiment: $EXPERIMENT_NAME"
echo "  Region:     $AWS_REGION"
echo ""

# ── 1. Resolve AMI ────────────────────────────
# Use CUSTOM_AMI env var if set, otherwise resolve latest DLAMI
if [[ -n "${CUSTOM_AMI:-}" ]]; then
    echo "[1/5] Using custom AMI..."
    AMI_ID="$CUSTOM_AMI"
    echo "  ✓ AMI: $AMI_ID (custom)"
else
    echo "[1/5] Resolving latest DLAMI..."
    AMI_ID=$(aws ec2 describe-images \
        --owners "$AMI_OWNER" \
        --filters "Name=name,Values=${AMI_FILTER}" "Name=state,Values=available" \
        --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
        --output text \
        --region "$AWS_REGION")
    echo "  ✓ AMI: $AMI_ID"
fi

# ── 2. Get security group ─────────────────────
echo "[2/5] Resolving security group..."
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region "$AWS_REGION")

if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
    echo "  ✗ Security group '$SG_NAME' not found."
    echo "    Run: ./ec2/setup-aws.sh"
    exit 1
fi
echo "  ✓ Security group: $SG_ID"

# Update SSH rule to current IP (in case IP changed since setup)
MY_IP=$(curl -s https://ipinfo.io/ip)
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr "${MY_IP}/32" \
    --region "$AWS_REGION" 2>/dev/null || true
echo "  ✓ SSH allowed from $MY_IP"

# ── 3. Launch spot instance ───────────────────
echo "[3/5] Requesting spot instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"one-time"}}' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EXPERIMENT_NAME},{Key=Experiment,Value=$EXPERIMENT_NAME}]" \
    --count 1 \
    --region "$AWS_REGION" \
    --query 'Instances[0].InstanceId' \
    --output text)
echo "  ✓ Instance requested: $INSTANCE_ID"

# ── 4. Wait for running + get IP ──────────────
echo "[4/5] Waiting for instance to be running..."
aws ec2 wait instance-running \
    --instance-ids "$INSTANCE_ID" \
    --region "$AWS_REGION"

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region "$AWS_REGION")
echo "  ✓ Running at $PUBLIC_IP"

# ── 5. Configure SSH + wait for sshd ──────────
echo "[5/5] Waiting for SSH to be ready..."
SSH_ALIAS="ec2-$EXPERIMENT_NAME"

# Add/update ~/.ssh/config entry
SSH_CONFIG="$HOME/.ssh/config"
# Remove old entry for this alias if it exists
if grep -q "Host $SSH_ALIAS" "$SSH_CONFIG" 2>/dev/null; then
    # Remove the block (Host line + next 3 lines)
    sed -i.bak "/^Host $SSH_ALIAS/,/^$/d" "$SSH_CONFIG"
fi
cat >> "$SSH_CONFIG" <<EOF

Host $SSH_ALIAS
    HostName $PUBLIC_IP
    User $EC2_USER
    IdentityFile $KEY_PATH
    StrictHostKeyChecking no
    ServerAliveInterval 60
EOF
echo "  ✓ SSH config updated (alias: $SSH_ALIAS)"

# Poll until SSH accepts connections
RETRIES=0
until ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
    -i "$KEY_PATH" "${EC2_USER}@${PUBLIC_IP}" "echo ok" &>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [[ $RETRIES -gt 30 ]]; then
        echo "  ✗ SSH not reachable after 5 minutes. Check security group."
        exit 1
    fi
    sleep 10
done
echo "  ✓ SSH is ready"

# ── Save to instance registry ─────────────────
mkdir -p "$(dirname "$INSTANCE_REGISTRY")"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | $INSTANCE_ID | $PUBLIC_IP | $INSTANCE_TYPE | $EXPERIMENT_NAME | $SSH_ALIAS" \
    >> "$INSTANCE_REGISTRY"

echo ""
echo "══════════════════════════════════════════════"
echo "  Instance ready!"
echo "  ID:    $INSTANCE_ID"
echo "  IP:    $PUBLIC_IP"
echo "  SSH:   ssh $SSH_ALIAS"
echo "  Stop:  ./ec2/stop.sh $INSTANCE_ID"
echo "══════════════════════════════════════════════"
echo ""
echo "INSTANCE_ID=$INSTANCE_ID"
echo "PUBLIC_IP=$PUBLIC_IP"
echo "SSH_ALIAS=$SSH_ALIAS"
