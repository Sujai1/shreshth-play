# EC2 Workflow Guide: Local Claude Code + Remote GPU Training

## Overview

```
Your Mac (Claude Code)
    │
    │  SSH (via Bash tool)
    ▼
EC2 GPU Instance
  - runs training
  - saves results to disk or S3
    │
    │  rsync / S3
    ▼
Your Mac
  - analysis notebooks
  - reward comparison scripts
```

Claude Code on your Mac uses its Bash tool to SSH directly into EC2 and run commands there. You never leave your local session — you just type to Claude and it executes things on the remote machine.

---

## Step 1: Prerequisites (one-time AWS setup)

You need three things set up before anything else works:

### 1a. An AWS account with billing enabled
Go to https://console.aws.amazon.com. You need a credit card attached.

### 1b. AWS CLI installed locally
```bash
brew install awscli        # on your Mac
aws configure              # walks you through 4 prompts
```
The 4 prompts ask for:
- `AWS Access Key ID` — create this in IAM → Users → Security Credentials
- `AWS Secret Access Key` — shown once when you create the key, save it
- `Default region` — use `us-east-1` (cheapest, most availability) or `us-west-2`
- `Default output format` — type `json`

### 1c. An EC2 key pair (for SSH)
```bash
aws ec2 create-key-pair --key-name rl-training --query 'KeyMaterial' \
  --output text > ~/.ssh/rl-training.pem
chmod 400 ~/.ssh/rl-training.pem
```
This `.pem` file is your SSH password. Never share it, never lose it.

---

## Step 2: Choosing the right instance + AMI

### The AMI (what OS/software comes pre-installed)
Use the **AWS Deep Learning AMI (DLAMI)**. It comes with NVIDIA drivers + CUDA already installed, PyTorch and conda environments pre-configured — no manual GPU driver setup needed.

Find the latest DLAMI ID for your region:
```bash
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=Deep Learning OSS Nvidia Driver AMI (Ubuntu 22.04)*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text
```

### The instance type (what hardware you get)

| Instance       | GPUs          | GPU RAM | On-demand/hr | Spot/hr | Good for                          |
|----------------|---------------|---------|--------------|---------|-----------------------------------|
| g4dn.xlarge    | 1x T4 (16GB)  | 16GB    | ~$0.53       | ~$0.16  | Small models, testing reward fns  |
| g4dn.2xlarge   | 1x T4 (16GB)  | 32GB    | ~$0.75       | ~$0.23  | Comfortable single-GPU training   |
| g5.xlarge      | 1x A10G (24GB)| 24GB    | ~$1.01       | ~$0.30  | Better for 7B models              |
| p3.2xlarge     | 1x V100 (16GB)| 16GB    | ~$3.06       | ~$0.92  | Serious training                  |

For testing reward functions on small/mid models (Qwen-0.5B to 7B): start with `g4dn.xlarge` on **spot pricing**.

### Spot vs On-Demand
- **On-demand**: guaranteed, can stop/start anytime, full price
- **Spot**: uses spare AWS capacity, 60-90% cheaper, but AWS can terminate with 2-minute warning
- For experiments under a few hours: use spot. For overnight training: use on-demand or add checkpoint saving.

---

## Step 3: The launch script (what you'll have)

A shell script `ec2/launch.sh` that does this in one command:
```bash
./ec2/launch.sh g4dn.xlarge
```

It will:
1. Look up the latest DLAMI ID
2. Request a spot instance of the given type
3. Poll until the instance is running
4. Print the SSH command and add the host to `~/.ssh/config`
5. Wait until SSH is actually accepting connections

And `./ec2/stop.sh <instance-id>` to terminate it when done.

---

## Step 4: How Claude Code talks to the EC2 instance

### Model A (recommended): Claude Code stays local, SSH-tunnels commands

Your local Claude Code session runs commands like:
```bash
ssh ec2-user@<IP> "cd ~/rl_env && python -m rl_env.train --reward_config accuracy_format"
```
or streams logs:
```bash
ssh ec2-user@<IP> "tail -f ~/rl_env/outputs/train.log"
```
This works today with zero extra setup.

### Model B: Install Claude Code ON the EC2 instance

SSH into the instance, install Claude Code there, and connect to that remote Claude session from your laptop via SSH tunnel. More powerful (Claude can directly read/write files on EC2) but more setup. Worth doing once you're comfortable with Model A.

---

## Step 5: Transferring results back

**Push code from local to EC2:**
```bash
rsync -avz --exclude '__pycache__' ./rl_env/ ec2-user@<IP>:~/rl_env/
```

**Pull results from EC2 to local:**
```bash
rsync -avz ec2-user@<IP>:~/rl_env/outputs/ ./results/
```

**For large checkpoints/datasets — use S3:**
```bash
# On EC2: upload
aws s3 sync ./outputs/ s3://your-bucket/experiments/run-001/

# On Mac: download
aws s3 sync s3://your-bucket/experiments/run-001/ ./results/run-001/
```
S3 is persistent even after the instance terminates — protects you from losing spot instance data.

---

## Step 6: The full experiment loop

```
1. Launch:    ./ec2/launch.sh g4dn.xlarge
2. Push code: rsync ./rl_env/ ec2-user@IP:~/rl_env/
3. Train:     ssh ec2-user@IP "python -m rl_env.train --reward_config accuracy_format"
              (Claude Code does this via Bash tool)
4. Pull data: rsync ec2-user@IP:~/outputs/ ./results/
5. Analyze:   python analysis/plot_rewards.py ./results/
6. Stop:      ./ec2/stop.sh <instance-id>
```

Steps 2–5 can all be done from inside a single Claude Code session on your Mac.

---

## What you need before we build the scripts

1. **AWS credentials** — create an IAM user with `AmazonEC2FullAccess` + `AmazonS3FullAccess` policies, generate an access key, then run `aws configure`.
2. **Spot quota check** — run the following to confirm `g4dn.xlarge` is available in your region:
   ```bash
   aws ec2 describe-instance-type-offerings \
     --location-type availability-zone \
     --filters Name=instance-type,Values=g4dn.xlarge
   ```
   New AWS accounts sometimes need to request a quota increase for GPU instances.
3. **An S3 bucket name** — either use one you have or we'll create `rl-experiments-<yourname>`.
