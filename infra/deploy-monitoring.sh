#!/bin/bash
# Deploys infra/monitoring.bicep (Log Analytics + alert rules) to the existing
# greenroom-rg resource group. NOT wired into CI — run manually once, review
# the plan, and only then apply.
#
# Prerequisites:
#   1. az login
#   2. Copy infra/monitoring.parameters.example.json -> infra/monitoring.parameters.json
#      and fill in environmentId (find it with:
#        az containerapp env list --resource-group greenroom-rg -o table)
#      and alertEmail.
#   3. IMPORTANT: metric names in monitoring.bicep (Requests/RestartCount/
#      UsageNanoCores with their exact dimensions) should be confirmed against
#      your actual Container Apps resource before the real deploy — run:
#        az monitor metrics list-definitions \
#          --resource <container-app-resource-id> -o table
#      and adjust monitoring.bicep if any metric name has changed or doesn't
#      match what's listed.
#
# Usage:
#   chmod +x infra/deploy-monitoring.sh
#   ./infra/deploy-monitoring.sh            # what-if (dry run, default)
#   ./infra/deploy-monitoring.sh --apply    # actually create the resources

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCE_GROUP="greenroom-rg"
PARAMS_FILE="$SCRIPT_DIR/monitoring.parameters.json"

if [ ! -f "$PARAMS_FILE" ]; then
  echo "ERROR: $PARAMS_FILE not found."
  echo "  Copy infra/monitoring.parameters.example.json -> infra/monitoring.parameters.json and fill it in."
  exit 1
fi

if [ "${1:-}" = "--apply" ]; then
  echo "==> Deploying monitoring resources to $RESOURCE_GROUP..."
  az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$SCRIPT_DIR/monitoring.bicep" \
    --parameters "@$PARAMS_FILE"
else
  echo "==> Dry run (what-if) — pass --apply to actually create resources"
  az deployment group what-if \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$SCRIPT_DIR/monitoring.bicep" \
    --parameters "@$PARAMS_FILE"
fi
