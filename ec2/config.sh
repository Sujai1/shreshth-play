#!/usr/bin/env bash
# ─────────────────────────────────────────────
# ec2/config.sh  —  shared settings for all EC2 scripts
# ─────────────────────────────────────────────

# AWS
export AWS_REGION="us-east-2"
export AWS_DEFAULT_REGION="us-east-2"

# Key pair (the .pem file and its AWS name)
export KEY_NAME="Sujai"                          # must match the key pair name in AWS
export KEY_PATH="$HOME/Desktop/Sujai.pem"

# AMI — AWS Deep Learning OSS Nvidia Driver AMI (Ubuntu 22.04)
# Resolved at launch time to always get the latest
export AMI_OWNER="amazon"
export AMI_FILTER="Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*"

# Default instance type (cheapest GPU spot)
export DEFAULT_INSTANCE_TYPE="g4dn.xlarge"

# SSH username for DLAMI Ubuntu 22.04
export EC2_USER="ubuntu"

# Security group name (created once, reused every launch)
export SG_NAME="rl-training-sg"
export SG_DESC="SSH access for RL training experiments"

# S3 bucket for experiment results
export S3_BUCKET="rl-experiments-sujai"

# Local paths
export LOCAL_CODE_DIR="$HOME/Desktop/shreshth_play"
export INSTANCE_REGISTRY="$HOME/Desktop/shreshth_play/ec2/.instances"
