#!/usr/bin/env bash
# ─────────────────────────────────────────────
# ec2/stop.sh  —  terminate an EC2 instance
#
# Usage:
#   ./ec2/stop.sh <instance-id>
#   ./ec2/stop.sh i-0abc123def456
#
# Also syncs results to S3 if a results dir is given:
#   ./ec2/stop.sh <instance-id> [remote-results-dir]
# ─────────────────────────────────────────────
set -euo pipefail
source "$(dirname "$0")/config.sh"

INSTANCE_ID="${1:-}"
REMOTE_RESULTS_DIR="${2:-}"

if [[ -z "$INSTANCE_ID" ]]; then
    echo "Usage: ./ec2/stop.sh <instance-id> [remote-results-dir]"
    echo ""
    echo "Recent instances:"
    if [[ -f "$INSTANCE_REGISTRY" ]]; then
        tail -10 "$INSTANCE_REGISTRY"
    else
        echo "  (no instance registry found)"
    fi
    exit 1
fi

# ── Optional: pull results to S3 before stopping ──
if [[ -n "$REMOTE_RESULTS_DIR" ]]; then
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region "$AWS_REGION")

    EXPERIMENT_NAME=$(aws ec2 describe-tags \
        --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=Experiment" \
        --query 'Tags[0].Value' \
        --output text \
        --region "$AWS_REGION")

    echo "Syncing results to S3 before termination..."
    ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "${EC2_USER}@${PUBLIC_IP}" \
        "aws s3 sync $REMOTE_RESULTS_DIR s3://${S3_BUCKET}/experiments/${EXPERIMENT_NAME}/"
    echo "  ✓ Results saved to s3://$S3_BUCKET/experiments/$EXPERIMENT_NAME/"
fi

# ── Terminate ─────────────────────────────────
echo "Terminating instance $INSTANCE_ID..."
aws ec2 terminate-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$AWS_REGION" \
    --query 'TerminatingInstances[0].CurrentState.Name' \
    --output text

echo "  ✓ Termination initiated. Instance will stop within 1-2 minutes."
echo "  Your results are at: s3://$S3_BUCKET/experiments/"
