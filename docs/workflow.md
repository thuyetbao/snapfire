# Workflow

## **Overview**

This workflow describes how to provision cloud infrastructure and deploy a distributed application to measure network latency between two virtual machines.

## **Prerequisites**

Refer to the [Headstart](headstart.md) section for installation requirements.

## **Workflow**

### Step 1: Prepare Environment

Manual created GCP project.

### Step 2: Configure GCP Access

Change working directory to `infra` to provision infrastructure:

```bash
cd infra
```

Configure credentials and project context:

```bash
# Set environment variables
export PROJECT_ID="[PROJECT_ID]"
export ACCOUNT_ID="[ACCOUNT_ID]"
export PROJECT_REGION="[PROJECT_REGION]"

# Authenticate and set context
gcloud auth application-default login
gcloud config set project $PROJECT_ID
gcloud config set account $ACCOUNT_ID
gcloud config set compute/zone $PROJECT_REGION
```

### Step 3: Provision Infrastructure (IaC)

Provision **two virtual machines** using Terraform.

```bash
terraform init
terraform apply
```

Once applied, wait for both VMs to finish booting and cloud-init execution.

### Step 4: Verify VM initialization

SSH into each VM and verify cloud-init status:

```bash
sudo cloud-init status
sudo cloud-init status --long
```

If initialization is complete, the following output is expected:

```bash
status: running
extended_status: running
boot_status_code: enabled-by-generator
last_update: Thu, 01 Jan 1970 00:00:26 +0000
detail: DataSourceGCELocal
errors: []
recoverable_errors: {}
```

Check logs if initialization is slow or degraded:

```bash
sudo tail -f /var/log/cloud-init.log
sudo tail -f /var/log/cloud-init-output.log
```

⚠️ Most cloud-init failures are caused by:

- YAML indentation errors

- Typos in `runcmd`

- Missing `#cloud-config` header

### Step 4: Validate application on probe/target instances

For each instance, follow process: Check service status, restart services if needed, inspect logs, validate health endpoint

For `probe` instance

```bash
# Check service status
sudo systemctl status probe-collector.service
sudo systemctl status probe-agent.service

# Restart services if needed
sudo systemctl restart probe-collector.service
sudo systemctl restart probe-agent.service

# Inspect logs
journalctl -f -u probe-collector.service -n 50
journalctl -f -u probe-agent.service -n 50

# Validate health endpoint
curl -v http://$PROBE_EXTERNAL_IP:8888/health
# {
#   "timestamp": "2025-12-30T14:20:00.294Z",
#   "timezone": "UTC"
# }
```

For `target` instance

```bash
# Check service status
sudo systemctl status target-udp-echo.service
sudo systemctl status target-exposer.service

# Restart services if needed
sudo systemctl restart target-exposer.service
sudo systemctl restart target-udp-echo.service

# Inspect logs
journalctl -f -u target-udp-echo.service -n 50
journalctl -f -u target-exposer.service -n 50

# Validate health endpoint
curl -v http://$TARGET_EXTERNAL_IP:9999/_/health
# {
#   "timestamp": "2025-12-30T14:30:00.812Z",
#   "timezone": "UTC"
# }
```

### Step 5: Collect experiment results

Run the experiment for a specified duration (e.g., 1-2 days) and collect latency data via the probe-agent's HTTP endpoint.

After the experiment finishes, write the results and generate a report.

### Step 6: Tear down resources

When the experiment is completed, terminate the instances and clean up resources.

```bash
terraform destroy
```

Logout account:

```bash
gcloud auth application-default logout
gcloud config unset project
gcloud config unset account
gcloud config unset compute/zone
```
