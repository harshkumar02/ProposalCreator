#!/bin/sh
# Dump the Postgres database to deploy/backups/ and keep the newest $KEEP dumps.
# n8n needs no backup: its workflows and credential are re-provisioned from the
# repo and deploy/.env on every start (only execution history is lost).
#
# Daily at 02:30 (crontab -e):
#   30 2 * * * /path/to/ProposalCreator/deploy/backup.sh >> /path/to/ProposalCreator/deploy/backups/backup.log 2>&1
#
# Restore:
#   gunzip -c backups/<file>.sql.gz | docker compose -f docker-compose.prod.yml exec -T db \
#     psql -U proposalcreator -d proposalcreator
set -eu
cd "$(dirname "$0")"
KEEP="${KEEP:-14}"
mkdir -p backups
umask 077

stamp="$(date +%Y%m%d-%H%M%S)"
file="backups/proposalcreator-$stamp.sql.gz"
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$file.tmp"
mv "$file.tmp" "$file"
echo "$(date -u +%FT%TZ) wrote $file ($(du -h "$file" | cut -f1))"

ls -1t backups/proposalcreator-*.sql.gz | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -f "$old"
done
