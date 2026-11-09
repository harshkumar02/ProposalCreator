#!/bin/sh
# Provision ProposalCreator's n8n setup on every start, then run n8n.
#
# 1. Imports the "ProposalCreator Workflow Secret" Header Auth credential from
#    N8N_SHARED_SECRET (the same value the backend has), so webhook auth and
#    callbacks work without anyone opening the editor.
# 2. Imports every workflow JSON in $WORKFLOWS_DIR (repo: n8n/workflows/) and
#    publishes it, so upgrading the repo upgrades the workflows.
# Re-importing is idempotent: the fixed ids overwrite the previous version.
set -eu

WORKFLOWS_DIR="${WORKFLOWS_DIR:-/workflows}"

: "${N8N_SHARED_SECRET:?N8N_SHARED_SECRET must be set}"
case "$N8N_SHARED_SECRET" in
  *[!A-Za-z0-9_-]*)
    echo "n8n-init: N8N_SHARED_SECRET may only contain letters, digits, '-' and '_'" >&2
    exit 1
    ;;
esac

cred_file="$(mktemp)"
trap 'rm -f "$cred_file"' EXIT
printf '[{"id":"pcWorkflowSecret","name":"ProposalCreator Workflow Secret","type":"httpHeaderAuth","data":{"name":"X-Workflow-Secret","value":"%s"}}]' \
  "$N8N_SHARED_SECRET" > "$cred_file"

echo "n8n-init: importing credential"
n8n import:credentials --input="$cred_file"
rm -f "$cred_file"

workflow_ids=""
for workflow in "$WORKFLOWS_DIR"/*.json; do
  id="$(node -e 'process.stdout.write(String(require(require("path").resolve(process.argv[1])).id || ""))' "$workflow")"
  if [ -z "$id" ]; then
    echo "n8n-init: $workflow has no id; give it a fixed id so it can be published" >&2
    exit 1
  fi
  workflow_ids="$workflow_ids $id"
done

# Re-importing a published workflow makes n8n try to deactivate it, which the
# headless importer isn't permitted to do — so unpublish first (a no-op on the
# very first start, when the workflow doesn't exist yet).
for id in $workflow_ids; do
  n8n unpublish:workflow --id="$id" >/dev/null 2>&1 || true
done

echo "n8n-init: importing workflows from $WORKFLOWS_DIR"
n8n import:workflow --separate --input="$WORKFLOWS_DIR"

for id in $workflow_ids; do
  echo "n8n-init: publishing $id"
  n8n publish:workflow --id="$id"
done

echo "n8n-init: starting n8n"
exec n8n start
