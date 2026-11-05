#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
# update_github_firewall.sh
# Updates the GCP firewall rule "default-allow-ssh" source ranges
# with the current GitHub Actions IP ranges from api.github.com/meta
#
# Usage:
#   ./scripts/update_github_firewall.sh [PROJECT_ID] [FIREWALL_RULE_NAME]
#
# Defaults (edit below or pass as args):
#   PROJECT_ID        = $(gcloud config get-value project)
#   FIREWALL_RULE     = default-allow-ssh
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
FIREWALL_RULE="${2:-default-allow-ssh}"
GITHUB_META_URL="https://api.github.com/meta"
MAX_RANGES=256   # GCP hard limit for source ranges per firewall rule

# ── Validate tools ─────────────────────────────────────────────────────
for cmd in curl jq gcloud; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Required tool not found: $cmd"
    exit 1
  fi
done

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID is empty. Pass it as first argument or set gcloud project."
  exit 1
fi

echo "Project:       $PROJECT_ID"
echo "Firewall rule: $FIREWALL_RULE"
echo ""

# ── Fetch GitHub Actions IPs ───────────────────────────────────────────
echo "Fetching GitHub Actions IP ranges from $GITHUB_META_URL..."

GITHUB_ACTIONS_IPS=$(curl -sf "$GITHUB_META_URL" | jq -r '.actions[]' | grep -v ':' | sort -u)
# Note: grep -v ':' filters out IPv6 (GCP firewall supports IPv4 source ranges only)

if [[ -z "$GITHUB_ACTIONS_IPS" ]]; then
  echo "Failed to fetch GitHub Actions IPs or the list is empty."
  exit 1
fi

TOTAL_COUNT=$(echo "$GITHUB_ACTIONS_IPS" | wc -l | tr -d ' ')
echo "Got $TOTAL_COUNT raw IPv4 ranges from GitHub Actions"

# ── Aggregate CIDRs to stay within GCP's 256 source-range limit ────────
# Uses Python's ipaddress.collapse_addresses() to merge overlapping/adjacent
# subnets, then widens prefixes iteratively until we're under the limit.
if python3 -c "import ipaddress" 2>/dev/null; then
  echo "Aggregating CIDRs with Python ipaddress..."
  AGGREGATED_IPS=$(echo "$GITHUB_ACTIONS_IPS" | python3 -c "
import sys, ipaddress

cidrs = [ipaddress.ip_network(line.strip()) for line in sys.stdin if line.strip()]
collapsed = list(ipaddress.collapse_addresses(cidrs))

limit = $MAX_RANGES
while len(collapsed) > limit:
    widened = set()
    for net in collapsed:
        widened.add(net.supernet())
    collapsed = list(ipaddress.collapse_addresses(widened))

for net in sorted(collapsed):
    print(net)
")
else
  echo "Python3 ipaddress not available, taking first $MAX_RANGES ranges..."
  AGGREGATED_IPS=$(echo "$GITHUB_ACTIONS_IPS" | head -n "$MAX_RANGES")
fi

FINAL_COUNT=$(echo "$AGGREGATED_IPS" | wc -l | tr -d ' ')
echo "Aggregated to $FINAL_COUNT ranges (limit: $MAX_RANGES)"

SOURCE_RANGES=$(echo "$AGGREGATED_IPS" | tr '\n' ',' | sed 's/,$//')

# ── Export IPs to txt file (manual fallback) ───────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TXT_OUTPUT="${SCRIPT_DIR}/github_actions_ips.txt"

echo ""
echo "Writing IP ranges to $TXT_OUTPUT..."

{
  echo "# GitHub Actions IP Ranges (IPv4 only)"
  echo "# Source: https://api.github.com/meta"
  echo "# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "# Total ranges: $FINAL_COUNT (aggregated from $TOTAL_COUNT raw CIDRs)"
  echo "# GCP hard limit: $MAX_RANGES source ranges per firewall rule"
  echo "#"
  echo "# ── ONE PER LINE (copy-paste into GCP Console > Firewall > Source IP ranges) ──"
  echo "$AGGREGATED_IPS"
  echo ""
  echo "# ── COMMA-SEPARATED (for: gcloud compute firewall-rules update ... --source-ranges=...) ──"
  echo "$SOURCE_RANGES"
} > "$TXT_OUTPUT"

echo "  ✓ Saved $FINAL_COUNT ranges to: $TXT_OUTPUT"
echo ""

# ── Check if firewall rule exists ──────────────────────────────────────
echo ""
echo "Checking if firewall rule '$FIREWALL_RULE' exists in project '$PROJECT_ID'..."

# Capture output AND exit code separately so we can show the real error
set +e
DESCRIBE_OUTPUT=$(gcloud compute firewall-rules describe "$FIREWALL_RULE" \
  --project="$PROJECT_ID" \
  --format="value(name)" 2>&1)
DESCRIBE_EXIT=$?
set -e

if [[ $DESCRIBE_EXIT -ne 0 ]]; then
  echo ""
  echo "ERROR: Could not describe firewall rule '$FIREWALL_RULE'. Real gcloud error:"
  echo "$DESCRIBE_OUTPUT"
  echo ""
  echo "Listing all firewall rules in project '$PROJECT_ID':"
  gcloud compute firewall-rules list --project="$PROJECT_ID" \
    --format="table(name,network,sourceRanges.list())" 2>&1 || true
  exit 1
fi

CURRENT_RANGES=$(gcloud compute firewall-rules describe "$FIREWALL_RULE" \
  --project="$PROJECT_ID" \
  --format="value(sourceRanges)" 2>/dev/null || echo "")

echo "Current source ranges:"
echo "$CURRENT_RANGES" | tr ';' '\n' | sed 's/^/   /'

# ── Update the firewall rule ───────────────────────────────────────────
echo ""
echo "Updating firewall rule '$FIREWALL_RULE' with $FINAL_COUNT GitHub Actions ranges..."

gcloud compute firewall-rules update "$FIREWALL_RULE" \
  --project="$PROJECT_ID" \
  --source-ranges="$SOURCE_RANGES"

echo ""
echo "Firewall rule '$FIREWALL_RULE' updated successfully!"
echo "   Applied $FINAL_COUNT aggregated ranges (from $TOTAL_COUNT raw GitHub Actions IPs)."
echo ""
echo "Tip: Run this script via cron or Cloud Scheduler to keep ranges up to date."
echo "   GitHub IPs change occasionally -- weekly refresh is recommended."
