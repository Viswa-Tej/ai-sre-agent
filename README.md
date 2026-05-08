AI SRE Agent — Built on Kubernetes, Powered by Gemini, Zero Cost

A real Site Reliability Engineering project built entirely in a browser.
No local installs. No paid services. No bullshit.

I built this during my Master's in Cybersecurity at EPITA Paris as a hands-on way to
bridge my DevOps/SRE experience with modern AI tooling. The idea is simple:
Kubernetes already knows when things break (Prometheus fires alerts). Why not
wire that directly to an LLM and get an instant root cause analysis?
The entire thing runs free — GitHub Codespaces for the environment,
k3d for Kubernetes, Gemini's free tier for the AI, GitHub Actions for CI/CD,
and Terraform to demonstrate IaC against a GCP always-free VM.

What This Project Actually Does
When a pod crashes in the cluster, here's what happens automatically:
Pod OOMKills → CrashLoopBackOff
      ↓
Prometheus scrapes the restart counter
      ↓
Custom PrometheusRule fires alert after 1 minute
      ↓
AI SRE Agent polls Prometheus every 60s → sees firing alert
      ↓
Sends alert JSON to Google Gemini 1.5 Flash
      ↓
Gemini returns: root cause + impact + kubectl fix + long-term recommendation
      ↓
Output appears in pod logs (and optionally Slack, if you add it)
That's it. No magic. Just connecting tools that already exist in a way that reduces
the time between "something broke" and "I know why and how to fix it."

Architecture
┌──────────────────────────────────────────────────────────────────┐
│  GitHub Codespaces (4GB RAM, Ubuntu 22.04, browser-based)        │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  k3d Kubernetes Cluster (k3s in Docker)                    │  │
│  │  1 server node + 1 agent node                              │  │
│  │                                                              │  │
│  │  ┌─────────────────┐     ┌───────────────────────┐        │  │
│  │  │  kube-prometheus │     │  kube-state-metrics   │        │  │
│  │  │  -stack (Helm)   │◄────│  node-exporter        │        │  │
│  │  │                  │     │  alertmanager         │        │  │
│  │  │  Prometheus :9090│     └───────────────────────┘        │  │
│  │  │  Grafana    :3000│                                        │  │
│  │  └────────┬─────────┘                                        │  │
│  │           │                                                    │  │
│  │           │  GET /api/v1/alerts (every 60s)                   │  │
│  │           ▼                                                    │  │
│  │  ┌────────────────┐      ┌─────────────────────────┐        │  │
│  │  │  AI SRE Agent  │─────►│  Google Gemini API      │        │  │
│  │  │  (Python pod)  │      │  gemini-1.5-flash        │        │  │
│  │  │                │◄─────│  free tier, 15 req/min   │        │  │
│  │  └────────────────┘      └─────────────────────────┘        │  │
│  │                                                              │  │
│  │  ┌────────────────┐                                         │  │
│  │  │  broken-app    │  ← intentionally OOMKills for demo      │  │
│  │  │  (nginx 10Mi)  │                                         │  │
│  │  └────────────────┘                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

CI/CD:  push to main → GitHub Actions builds image → pushes to GHCR
IaC:    Terraform provisions GCP e2-micro (always-free tier)

Tech Stack
LayerToolWhyDev environmentGitHub CodespacesBrowser-based, 60hr/mo free, Docker pre-installedKubernetesk3d (k3s in Docker)Real upstream k8s, spins up in 30s, runs on 4GBMonitoringkube-prometheus-stackIndustry standard, ships Grafana + rules out of boxAIGoogle Gemini 1.5 FlashFree tier, no card, 15 req/min, 1M tokens/dayCI/CDGitHub ActionsAuto-build on push, free for public reposImage registryGitHub Container RegistryAuto-auth via GITHUB_TOKEN, no separate accountIaCTerraform + GCPDemonstrates cloud provisioning skill, free e2-micro

Repo Structure
ai-sre-agent/
│
├── .github/
│   └── workflows/
│       └── build-agent.yml     # CI: builds + pushes Docker image on every push
│
├── infra/
│   ├── main.tf                 # GCP VM + firewall resource definitions
│   ├── variables.tf            # Input variables with types and defaults
│   ├── outputs.tf              # Prints VM IP + ssh command after apply
│   └── terraform.tfvars        # Your actual values (gitignored — never committed)
│
├── agent/
│   ├── main.py                 # The AI agent itself
│   ├── requirements.txt        # Just "requests" — no OpenAI SDK needed
│   └── Dockerfile              # Slim Python image, non-root user
│
├── k8s/
│   ├── agent-deployment.yaml   # Deploys the AI agent pod
│   ├── broken-app.yaml         # The intentionally broken nginx (failure demo)
│   └── fast-alert.yaml         # Custom PrometheusRule (fires in 1min vs 15min default)
│
├── screenshots/                # Build evidence for README + LinkedIn
│
└── README.md                   # You're reading it

Prerequisites
Before you start, you need three things:

GitHub account — free, you probably already have one
Google account — for Gemini API key (AI Studio, not GCP billing)
GCP account — only needed if you want the Terraform section; requires a card for
identity verification but e2-micro is genuinely free (always-free tier)

If you cannot add a card to GCP, skip Phase 2 entirely. The Kubernetes + monitoring +
AI agent sections are fully independent of it.

Step-by-Step Build Guide
Phase 0 — Get Your Keys (15 minutes)
Gemini API Key (the important one — no card needed)
bash# 1. Go to https://aistudio.google.com
# 2. Sign in with any Google account
# 3. Click "Get API key" → "Create API key"
# 4. Copy the key — it starts with AIza...
# 5. Save it somewhere temporarily (notepad, NOT in the repo)
The key is free. Google AI Studio is the developer playground product,
separate from the paid Vertex AI. Free tier gives you:

15 requests per minute
1 million tokens per day
gemini-1.5-flash model (fast, good enough for RCA)

That's more than enough. Even if you leave this running for 24 hours straight,
you won't hit the limit.
GCP Project ID (for Terraform only)
bash# 1. Go to console.cloud.google.com
# 2. Top dropdown → New Project
# 3. Name it "ai-sre-agent-vt" → Create
# 4. Note the Project ID — it's the one with the random suffix
#    Example: "ai-sre-agent-vt-294710"
#    (Different from the display name you chose)

Phase 1 — Create the GitHub Repo and Codespace (10 minutes)
Create the repo
bash# On github.com:
# → New repository
# → Name: ai-sre-agent
# → Public (required for free Actions minutes)
# → Do NOT add README, .gitignore, or license yet
# → Create repository
Launch a Codespace
bash# On the empty repo page:
# → Green "Code" button
# → Codespaces tab
# → "Create codespace on main"
# → Wait ~60 seconds
You now have a full Linux terminal in your browser. It has Docker, git, Python,
gh CLI, and kubectl already installed. This is your entire workstation.
Set up the folder structure
bash# Create all the directories we'll need
# -p flag = create parent dirs too, don't error if exists
mkdir -p infra agent k8s scripts screenshots .github/workflows
Write the .gitignore FIRST — before any other file
This is not optional. Terraform state files contain your VM's metadata.
If you ever commit a .tfstate file, rotate your GCP credentials immediately.
bashcat > .gitignore <<'EOF'
# --- TERRAFORM ---
# tfstate files are auto-generated and contain resource metadata.
# They can include credentials in plain text. Never commit these.
*.tfstate
*.tfstate.*

# Terraform working directory — downloaded provider binaries
.terraform/

# Lock file for provider versions — can commit this if you want reproducible builds
# but it's environment-specific, so we're ignoring it here
.terraform.lock.hcl

# tfvars files contain your actual values (project ID, SSH paths, etc.)
# The template is in the repo; your values are not
terraform.tfvars
*.tfvars

# Crash logs from failed Terraform runs
crash.log

# --- SECRETS ---
# Belt and suspenders approach — if something is named like a secret, ignore it
*.pem
.env
.env.*
secrets.txt
*.secret
gcp-key.json
service-account*.json

# --- PYTHON ---
__pycache__/
*.pyc
.pytest_cache/
venv/

# --- EDITOR / OS ---
.vscode/
.idea/
*.swp
.DS_Store
EOF
Initial commit
bash# Always commit .gitignore before anything else
git add .gitignore
git commit -m "chore: initial project structure with gitignore"
git push origin main

Phase 2 — Terraform on Free GCP e2-micro (40 minutes)
This section provisions a tiny GCP VM using Terraform. The VM itself is in GCP's
always-free tier (1 vCPU, 1GB RAM, us-central1). We don't run Kubernetes on it —
it's here to demonstrate the IaC skill. The actual cluster work happens in Codespaces.
Install Terraform in Codespace
bash# Codespaces doesn't ship Terraform by default, so we install it manually
# These commands add HashiCorp's official apt repo and install from there

wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update && sudo apt install -y terraform

# Confirm it worked
terraform version
Authenticate gcloud
bash# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL   # reload shell to pick up gcloud in PATH

# Log in — this opens a URL. Copy it, open in your laptop browser,
# authenticate with your Google account, then paste the code back here
gcloud auth login --no-launch-browser

# Set application default credentials — Terraform reads these automatically
gcloud auth application-default login --no-launch-browser

# Point gcloud at your project
gcloud config set project YOUR_PROJECT_ID

# Enable the APIs we need (Compute = VMs, IAM = service accounts)
gcloud services enable compute.googleapis.com
gcloud services enable iam.googleapis.com
Generate SSH keypair
bash# We need an SSH key so Terraform can inject it into the VM's authorized_keys
# -t rsa = RSA algorithm
# -b 4096 = 4096-bit key strength
# -C = comment (just a label, doesn't affect functionality)
# -f = output file path
# -N "" = no passphrase (needed for automation)
ssh-keygen -t rsa -b 4096 -C "viswa-sre-agent" -f ~/.ssh/id_rsa -N ""

# Verify both files were created
# id_rsa     = private key (stays on your machine, never share this)
# id_rsa.pub = public key (goes into the VM — safe to share)
ls ~/.ssh/id_rsa*
Write infra/main.tf
hcl# infra/main.tf
# This file defines the actual cloud resources we want to create.
# Terraform reads this and figures out what API calls to make.

# terraform {} block pins the provider version.
# Without this, "terraform init" 6 months from now might pull a
# newer Google provider with breaking changes. Pinning = reproducibility.
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"    # ~> means "5.x only", not 6.x
    }
  }
}

# provider "google" tells Terraform which GCP project and region to use.
# It reads credentials from gcloud auth application-default automatically.
# We don't hardcode credentials here — that would be a security incident.
provider "google" {
  project = var.project_id   # reads from variables.tf + terraform.tfvars
  region  = var.region
  zone    = var.zone
}

# Firewall rule: GCP blocks all ingress by default.
# We need to explicitly allow SSH (port 22) so we can connect to the VM.
# In a real prod system you'd restrict source_ranges to your office IP.
# For a portfolio demo, 0.0.0.0/0 (open to internet) is acceptable.
resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh-sre"      # must be unique in the project
  network = "default"            # attach to the default VPC

  allow {
    protocol = "tcp"
    ports    = ["22"]            # SSH only — not 80, not 443, just SSH
  }

  source_ranges = ["0.0.0.0/0"]   # any IP can attempt SSH
  target_tags   = ["sre-demo"]    # only applies to VMs tagged "sre-demo"
}

# The VM itself.
# e2-micro is in GCP's always-free tier:
# → 1 vCPU (shared), 1 GB RAM
# → Must be in us-east1, us-west1, or us-central1
# → Up to 30 GB standard disk
# → Resets monthly — if you keep it running all month, still free
resource "google_compute_instance" "demo_vm" {
  name         = "sre-agent-demo-vm"
  machine_type = "e2-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"  # Ubuntu 22.04 LTS
      size  = 10    # 10 GB disk — small, but enough for an empty VM
      type  = "pd-standard"  # standard HDD, not SSD — cheaper
    }
  }

  network_interface {
    network = "default"
    access_config {}  # this empty block creates an ephemeral public IP
                      # without it, the VM has no internet-reachable IP
  }

  # Inject the SSH public key into the VM's authorized_keys file.
  # GCP handles this via the metadata API during VM boot.
  # The format is "username:public_key_content"
  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.public_key_path)}"
  }

  # Tags link this VM to the firewall rule above.
  # The firewall only applies to VMs with this tag.
  tags = ["sre-demo"]

  service_account {
    scopes = ["cloud-platform"]  # gives the VM access to GCP APIs
                                  # in prod, use a custom SA with least-privilege
  }
}
Write infra/variables.tf
hcl# infra/variables.tf
# Variables make the configuration reusable and environment-agnostic.
# Actual values come from terraform.tfvars (which is gitignored).

variable "project_id" {
  description = "Your GCP project ID — find it in GCP Console top bar"
  type        = string
  # no default — you MUST provide this value in tfvars
}

variable "region" {
  description = "GCP region. Must be us-east1, us-west1, or us-central1 for free tier."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone within the region. a/b/c suffix = different datacenters."
  type        = string
  default     = "us-central1-a"
}

variable "ssh_user" {
  description = "Linux username that will be created on the VM"
  type        = string
  default     = "viswa"
}

variable "public_key_path" {
  description = "Path to the SSH public key on your machine (or Codespace)"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}
Write infra/outputs.tf
hcl# infra/outputs.tf
# After "terraform apply" finishes, these values are printed to the terminal.
# They're also stored in tfstate so you can query them later with
# "terraform output -raw vm_external_ip"

output "vm_external_ip" {
  description = "Public IP of the demo VM"
  # This path navigates the resource's nested attributes:
  # network_interface[0] = first NIC
  # access_config[0]     = first external IP config
  # nat_ip               = the actual public IP string
  value = google_compute_instance.demo_vm.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  description = "Ready-to-run SSH command — copy/paste this directly"
  value       = "ssh ${var.ssh_user}@${google_compute_instance.demo_vm.network_interface[0].access_config[0].nat_ip}"
}
Write infra/terraform.tfvars
bash# This file is gitignored — it holds your real values.
# The template shows what keys are needed; your values stay local.

cat > infra/terraform.tfvars <<EOF
project_id      = "$(gcloud config get-value project)"   # auto-fills your current project
ssh_user        = "viswa"
public_key_path = "/home/codespace/.ssh/id_rsa.pub"       # Codespace home dir path
EOF

# Verify it looks right
cat infra/terraform.tfvars
Run Terraform
bashcd infra

# "init" downloads the Google provider plugin into .terraform/
# Must run this before plan or apply
terraform init

# "plan" is a dry run — shows what WILL be created without doing anything
# Always review this before apply. Look for "2 to add, 0 to destroy."
terraform plan

# "apply" actually creates the resources
# -auto-approve skips the yes/no confirmation prompt
terraform apply -auto-approve

# Grab the IP for quick reference
export VM_IP=$(terraform output -raw vm_external_ip)
echo "Your VM is at: $VM_IP"

# Optionally SSH in to prove it's real
ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa viswa@$VM_IP
# Run "hostname" to confirm, then "exit"

cd ..

Phase 3 — k3d Kubernetes Cluster (20 minutes)
What is k3d?
k3d is a wrapper that runs k3s inside Docker containers. k3s is a
production-grade Kubernetes distribution by Rancher (used by SUSE, edge
deployments, embedded systems). It's 100% real Kubernetes — same API, same
kubectl commands — just without the bloat that makes vanilla kubeadm need 8GB RAM.
k3d wraps k3s further so each "node" is a Docker container on your machine.
Spin up a full multi-node cluster in 30 seconds. Perfect for Codespaces.
bash# Install k3d
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
k3d version

# Create the cluster:
# --agents 1      = 1 worker node (the server is the control plane)
# -p "30030:..."  = forward port 30030 from your machine to the server node
#                   this is how we reach Grafana from the Codespace browser
# -p "30090:..."  = same for Prometheus
# --wait          = don't return until all nodes are Ready
k3d cluster create sre-cluster \
  --agents 1 \
  -p "30030:30030@server:0" \
  -p "30090:30090@server:0" \
  --wait

# Verify
kubectl get nodes
# Should show 2 nodes: k3d-sre-cluster-server-0 and k3d-sre-cluster-agent-0
# Both should be "Ready" within 30 seconds
Install Helm
bash# Helm is the package manager for Kubernetes
# Like apt for Ubuntu, or npm for Node — but for K8s apps
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version

Phase 4 — Prometheus + Grafana Monitoring Stack (30 minutes)
bash# Add the official Prometheus community Helm chart repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
# This single Helm chart deploys:
#   - Prometheus          (metrics collection + alerting rules engine)
#   - Alertmanager        (routes alerts to Slack, email, etc.)
#   - Grafana             (dashboards)
#   - node-exporter       (host-level CPU/memory/disk metrics)
#   - kube-state-metrics  (Kubernetes object metrics — pod counts, restarts, etc.)
#
# The "set" flags customize the defaults:
# grafana.service.type=NodePort     = expose Grafana on a static port
# grafana.service.nodePort=30030    = use port 30030 (matches our k3d port-forward)
# ...resources.limits.memory=800Mi  = cap Prometheus at 800MB so we don't OOM the Codespace
#
# --wait = block until all pods are Running before returning

helm install monitoring prometheus-community/kube-prometheus-stack \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30030 \
  --set prometheus.service.type=NodePort \
  --set prometheus.prometheusSpec.service.nodePort=30090 \
  --set prometheus.prometheusSpec.resources.requests.memory=400Mi \
  --set prometheus.prometheusSpec.resources.limits.memory=800Mi \
  --set grafana.resources.requests.memory=128Mi \
  --set grafana.resources.limits.memory=256Mi \
  --wait

# Check everything is running
kubectl get pods
# You should see ~10 pods, all Running or Completed

# Get the Grafana admin password (auto-generated, stored in a K8s Secret)
kubectl get secret monitoring-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
Access the dashboards
bash# Port-forward Grafana to localhost:3000
# --address 0.0.0.0 makes it accessible from Codespace's browser proxy
kubectl port-forward svc/monitoring-grafana 3000:80 --address 0.0.0.0 &

# Port-forward Prometheus to localhost:9090
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 --address 0.0.0.0 &
In VS Code, click the Ports tab at the bottom → port 3000 → globe icon.

Grafana: username admin, password from above
Prometheus: http://localhost:9090 → Status → Targets


Phase 5 — AI SRE Agent (1.5 hours)
The agent code — agent/main.py
python# agent/main.py
# This is the entire AI agent. It does three things in a loop:
#   1. Ask Prometheus "are there any firing alerts?"
#   2. If yes, send them to Gemini with a system prompt
#   3. Log Gemini's RCA output
#
# The design is intentionally simple. Real SRE agents get complex
# fast — auto-remediation, Slack delivery, PagerDuty integration.
# This is the foundation they're all built on.

import os
import sys
import json
import time
import logging
import requests

# Structured logging — every line has a timestamp and level
# This makes kubectl logs much easier to grep
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("ai-sre-agent")

# === CONFIGURATION ===
# All config comes from environment variables — twelve-factor app principle.
# This means the same Docker image works in dev, staging, and prod.
# You just change the env vars, not the code.

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    # Default assumes the agent is running INSIDE the same k8s cluster.
    # K8s DNS resolves this service name automatically within the cluster.
    "http://monitoring-kube-prometheus-prometheus.default.svc.cluster.local:9090"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")        # injected from K8s Secret
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

# Fail loudly at startup if the API key is missing.
# Much better than running for an hour and failing silently on every LLM call.
if not GEMINI_API_KEY:
    log.error("GEMINI_API_KEY env var not set. Exiting.")
    sys.exit(1)

# Build the Gemini API URL.
# We're calling the REST API directly — no SDK needed, just requests.
# The key goes in the URL as a query param (Google's auth pattern for AI Studio keys).
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def get_alerts():
    """
    Query Prometheus /api/v1/alerts endpoint.
    Returns only FIRING alerts — we don't care about pending or inactive.
    """
    url = f"{PROMETHEUS_URL}/api/v1/alerts"
    try:
        # 10 second timeout — if Prometheus doesn't respond in 10s, something is wrong.
        # Don't hang forever; log the error and return empty.
        res = requests.get(url, timeout=10)
        res.raise_for_status()   # raises exception for 4xx/5xx responses

        data   = res.json()
        alerts = data.get("data", {}).get("alerts", [])

        # Filter to only "firing" state.
        # Prometheus alert states: inactive → pending → firing
        # "pending" means the condition is true but hasn't lasted long enough yet.
        # We only want confirmed, actively firing alerts.
        firing = [a for a in alerts if a.get("state") == "firing"]

        log.info(f"Fetched {len(firing)} firing alerts (out of {len(alerts)} total)")
        return firing

    except requests.exceptions.RequestException as e:
        # Network errors, DNS failures, timeouts all land here.
        # Log and return empty — we'll try again next poll cycle.
        log.error(f"Failed to fetch alerts from Prometheus: {e}")
        return []


def analyze_with_gemini(alerts):
    """
    Send firing alerts to Gemini and get back a structured RCA.
    Returns the RCA as a plain text string.
    """
    if not alerts:
        return "No firing alerts. Cluster healthy."

    # Build a compact summary of each alert.
    # We only send the fields that matter — reduces token usage
    # and avoids sending noise that could confuse the model.
    alert_summary = json.dumps(
        [
            {
                "name":        a.get("labels", {}).get("alertname"),
                "severity":    a.get("labels", {}).get("severity"),
                "namespace":   a.get("labels", {}).get("namespace"),
                "pod":         a.get("labels", {}).get("pod"),
                "summary":     a.get("annotations", {}).get("summary"),
                "description": a.get("annotations", {}).get("description"),
            }
            for a in alerts
        ],
        indent=2,
    )

    # System prompt tells Gemini what role to play and what format to use.
    # "plain text, no markdown" because this output goes to pod logs,
    # not to a web UI that renders markdown.
    system_prompt = (
        "You are a senior Site Reliability Engineer. "
        "Given Prometheus alerts in JSON format, produce: "
        "(1) likely root cause, "
        "(2) impact assessment, "
        "(3) immediate remediation steps with exact kubectl commands, "
        "(4) long-term fix recommendation. "
        "Be concise. Use plain text — no markdown, no asterisks."
    )

    # Gemini REST API request body.
    # "contents" is the conversation — a list of turns.
    # We're doing single-turn (one message, one response).
    # "generationConfig" controls the model's output behavior.
    payload = {
        "contents": [{
            "parts": [{
                "text": f"{system_prompt}\n\nAlerts:\n{alert_summary}"
            }]
        }],
        "generationConfig": {
            "temperature": 0.2,       # low = more deterministic, less creative
                                       # for ops/RCA we want consistent, boring output
            "maxOutputTokens": 600,   # ~450 words — enough for a solid RCA
        }
    }

    try:
        res = requests.post(GEMINI_URL, json=payload, timeout=30)
        res.raise_for_status()

        data = res.json()
        # Navigate the response structure to get the text
        # candidates[0] = first (and usually only) response candidate
        # content.parts[0].text = the actual generated text
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        log.error(f"Gemini API call failed: {e}")
        return f"LLM analysis failed: {e}"


def main():
    log.info("AI SRE Agent starting...")
    log.info(f"Prometheus: {PROMETHEUS_URL}")
    log.info(f"LLM Model:  {GEMINI_MODEL}")
    log.info(f"Poll every: {POLL_INTERVAL}s")

    # Main loop — runs forever until the pod is killed.
    # This is correct for a Kubernetes Deployment.
    # If it crashes, K8s restarts it automatically.
    while True:
        log.info("=" * 60)
        alerts   = get_alerts()

        if alerts:
            analysis = analyze_with_gemini(alerts)
            log.info("AI ANALYSIS:")
            log.info(analysis)
        else:
            log.info("No firing alerts.")

        # Sleep between polls.
        # 60s is fine for a demo. Real SRE tooling would use Alertmanager
        # webhooks for push-based delivery instead of polling.
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
agent/requirements.txt
# agent/requirements.txt
# Only one dependency: requests.
# We're calling the Gemini REST API directly, so we don't need the
# google-generativeai SDK. Fewer dependencies = smaller image = faster builds.

requests==2.32.3
agent/Dockerfile
dockerfile# agent/Dockerfile

# python:3.11-slim is Ubuntu-based but strips out build tools, docs, and locales.
# Result: ~50MB image vs ~350MB for the full python:3.11.
# Smaller image = faster pull = less attack surface.
FROM python:3.11-slim

# WORKDIR creates the directory if it doesn't exist and sets it as the
# current directory for all subsequent commands in this Dockerfile.
WORKDIR /app

# COPY requirements first, then pip install.
# Docker builds in layers — each instruction is a layer.
# If you copy everything first and then pip install, the pip layer
# is invalidated every time you change main.py.
# By copying requirements separately, pip install is only re-run when
# requirements.txt actually changes. Saves 30-60s on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir = don't store the pip download cache in the image
# (another size reduction)

# Now copy the actual application code
COPY main.py .

# Create a non-root user and switch to it.
# Running as root inside a container is a security anti-pattern.
# If the app is compromised, an attacker would have root inside the container.
# With a non-root user, the blast radius is limited.
# -m = create home directory
# -u 1000 = assign specific UID (good practice for consistent permissions)
RUN useradd -m -u 1000 sreagent
USER sreagent

# PYTHONUNBUFFERED=1 forces stdout/stderr to flush immediately.
# Without this, logs might not appear in "kubectl logs" until the buffer fills up.
# That means you could miss log lines when debugging.
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
.github/workflows/build-agent.yml
yaml# .github/workflows/build-agent.yml
# GitHub Actions workflow — auto-builds and pushes the Docker image
# to GitHub Container Registry (GHCR) on every push to main.

name: Build & Push AI SRE Agent

on:
  push:
    branches: [main]
    paths:
      # Only run this workflow when agent code or the workflow itself changes.
      # Prevents unnecessary builds when you only update README or k8s manifests.
      - 'agent/**'
      - '.github/workflows/build-agent.yml'
  workflow_dispatch:
    # Allows you to manually trigger this workflow from the Actions tab.
    # Useful when you want to rebuild without making a code change.

env:
  REGISTRY: ghcr.io
  # github.repository = "yourusername/ai-sre-agent"
  # So the full image name = "ghcr.io/yourusername/ai-sre-agent/ai-sre-agent"
  IMAGE_NAME: ${{ github.repository }}/ai-sre-agent

jobs:
  build-and-push:
    runs-on: ubuntu-latest   # GitHub's free Ubuntu runner

    permissions:
      contents: read     # read the repo code
      packages: write    # push to GHCR — must be explicitly granted

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4
        # Downloads your repo code into the runner's workspace

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        # Buildx is Docker's extended build system.
        # It enables the build cache (next step) and multi-platform builds.

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}       # ghcr.io
          username: ${{ github.actor }}        # your GitHub username
          password: ${{ secrets.GITHUB_TOKEN }}
          # GITHUB_TOKEN is automatically created for every workflow run.
          # No setup needed — GitHub handles auth to GHCR automatically.

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            # Tag with the short git SHA (first 7 chars of the commit hash)
            # Example: ghcr.io/youruser/ai-sre-agent/ai-sre-agent:a1b2c3d
            # This lets you roll back to any specific commit later.
            type=sha,prefix=,format=short
            # Also tag as "latest" when pushing to the default branch (main)
            # Example: ghcr.io/youruser/ai-sre-agent/ai-sre-agent:latest
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./agent       # build context = the agent/ folder
          push: true             # actually push to registry (not just build locally)
          tags: ${{ steps.meta.outputs.tags }}      # the tags from previous step
          labels: ${{ steps.meta.outputs.labels }}  # adds git metadata as image labels
          cache-from: type=gha   # read build cache from GitHub Actions cache
          cache-to: type=gha,mode=max
          # Write build cache to GHA cache.
          # First build: ~2 minutes. Subsequent builds (if requirements unchanged): ~20 seconds.
After pushing — make GHCR package public
bash# Commit and push everything to trigger the first build
git add agent/ .github/
git commit -m "feat: AI SRE agent with Gemini + GitHub Actions CI"
git push origin main

# Then go to:
# GitHub repo → right sidebar → Packages → ai-sre-agent
# → Package settings → Change visibility → Public
# (Required so the Kubernetes cluster can pull the image without auth)
Deploy to Kubernetes
bash# Create the K8s Secret for the Gemini API key.
# Never put API keys in YAML files. Always use Secrets.
# The Secret stores the value base64-encoded in etcd.
kubectl create secret generic gemini-secret \
  --from-literal=api-key='YOUR_GEMINI_KEY_HERE'

# Get your GitHub username (lowercase — GHCR requires lowercase image names)
GH_USER=$(gh api user --jq .login | tr '[:upper:]' '[:lower:]')

# Write the deployment manifest
cat > k8s/agent-deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-sre-agent
  labels:
    app: ai-sre-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-sre-agent
  template:
    metadata:
      labels:
        app: ai-sre-agent
    spec:
      containers:
        - name: agent
          image: ghcr.io/${GH_USER}/ai-sre-agent/ai-sre-agent:latest
          imagePullPolicy: Always  # always pull latest, never use stale cached image
          env:
            - name: GEMINI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: gemini-secret   # K8s Secret name
                  key: api-key          # key within that Secret
            - name: PROMETHEUS_URL
              value: "http://monitoring-kube-prometheus-prometheus.default.svc.cluster.local:9090"
            - name: POLL_INTERVAL_SECONDS
              value: "60"
            - name: GEMINI_MODEL
              value: "gemini-1.5-flash"
          resources:
            requests:
              cpu: "50m"       # 50 millicores = 5% of 1 CPU core
              memory: "64Mi"   # minimum memory the pod needs
            limits:
              cpu: "200m"      # cap at 20% of 1 CPU core
              memory: "128Mi"  # OOMKill if it exceeds this
EOF

kubectl apply -f k8s/agent-deployment.yaml

# Watch it start
kubectl get pods -l app=ai-sre-agent -w

# Stream the logs
kubectl logs -l app=ai-sre-agent -f

Phase 6 — Failure Simulation
This is the demo. We deploy a broken app, let it crash, wait for the alert
to fire, and watch the AI agent produce a root cause analysis.
Deploy the broken app
bashcat > k8s/broken-app.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: broken-app
  template:
    metadata:
      labels:
        app: broken-app
    spec:
      containers:
        - name: nginx
          image: nginx:alpine
          resources:
            limits:
              memory: "10Mi"   # nginx needs ~20MB minimum. 10Mi = guaranteed OOMKill.
              cpu: "50m"
            requests:
              memory: "10Mi"
              cpu: "50m"
EOF

kubectl apply -f k8s/broken-app.yaml

# Watch what happens
kubectl get pods -l app=broken-app -w
# You'll see: Pending → Running → OOMKilled → CrashLoopBackOff
# Each restart backs off longer: 10s → 20s → 40s → 80s → 160s → 300s
Add the fast alert rule
bashcat > k8s/fast-alert.yaml <<'EOF'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: fast-crashloop-alert
  labels:
    # This label MUST match the kube-prometheus-stack installation name.
    # Without it, Prometheus won't discover this rule.
    release: monitoring
spec:
  groups:
    - name: fast-alerts
      rules:
        - alert: PodCrashLoopingFast
          # rate() calculates the per-second rate of change over 2 minutes
          # kube_pod_container_status_restarts_total tracks cumulative restarts
          # rate > 0 means "at least one restart in the last 2 minutes"
          expr: rate(kube_pod_container_status_restarts_total[2m]) > 0
          for: 1m   # must be true for 1 continuous minute before firing
                     # prevents false positives from single transient restarts
          labels:
            severity: warning
          annotations:
            summary: "Pod {{ $labels.pod }} is crash-looping"
            description: "Pod {{ $labels.pod }} in {{ $labels.namespace }} restarting for 1+ minute."
EOF

kubectl apply -f k8s/fast-alert.yaml
After 1-2 minutes, check Prometheus UI → Alerts. You'll see
PodCrashLoopingFast in FIRING state.
Then watch the agent logs — within the next poll cycle (up to 60s)
you'll see Gemini's full RCA printed.

Phase 7 — Commit Everything
bash# Final sanity check — verify no secrets are staged
git status
# MUST NOT show: *.tfstate, terraform.tfvars, .env, *.pem

git add .
git commit -m "feat: complete AI SRE agent with failure simulation and monitoring"
git push origin main

Common Errors and Fixes
Agent pod shows ImagePullBackOff
The GHCR image is still private. Go to GitHub repo → Packages → the image →
Package settings → Change visibility → Public. Then kubectl rollout restart deploy/ai-sre-agent.
Gemini returns 403
Wrong API key, or you used a Vertex AI key instead of an AI Studio key.
Delete and recreate the secret:
bashkubectl delete secret gemini-secret
kubectl create secret generic gemini-secret --from-literal=api-key='NEW_KEY'
kubectl rollout restart deploy/ai-sre-agent
Prometheus pods OOMKilled
k3d is out of memory. Either the Codespace is running other heavy processes,
or the memory limits in the Helm install command are too high for your machine.
Try reducing prometheus.prometheusSpec.resources.limits.memory to 600Mi.
terraform apply fails with "could not find default credentials"
Re-run gcloud auth application-default login --no-launch-browser.
The credentials token might have expired if you took a break.
Custom PrometheusRule not picked up
The release: monitoring label must match. Verify with:
kubectl get prometheusrules --show-labels
and check it matches kubectl get prometheus -o yaml | grep ruleSelector.

Cleanup
bash# Destroy the GCP VM (always do this — even free resources are good to clean up)
cd infra && terraform destroy -auto-approve && cd ..

# Delete the k3d cluster (frees up the Codespace RAM)
k3d cluster delete sre-cluster

# Stop (don't delete) the Codespace to preserve your work:
# GitHub → your avatar → Your codespaces → ... → Stop codespace

What I'd Add Next
A few things I left out intentionally to keep this buildable in 2 days:
Slack integration — route RCA output to a Slack channel via webhook.
The agent already has the analysis; it's just a requests.post() call away.
Auto-remediation with guardrails — for crash loops caused by resource limits,
the fix (increase memory) is deterministic. You could have the agent kubectl patch
the deployment automatically, with a dry-run first and a hard cap on what it's
allowed to touch.
Alertmanager webhook — replace the 60-second polling loop with a push model.
Alertmanager fires a webhook the moment an alert transitions to firing.
Latency goes from "up to 60 seconds" to "under 1 second."
ArgoCD for GitOps — deploy the agent itself via ArgoCD so every change to
k8s/agent-deployment.yaml in git automatically syncs to the cluster.

Author
Viswa Teja Payam
MSc Cybersecurity — EPITA Paris
3+ years DevOps/SRE experience
LinkedIn | payamviswateja11@gmail.com
