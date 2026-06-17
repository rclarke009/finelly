> **Active development.** Core RAG and document ingest flows are working.
> Finance-tools integration and production hardening are in progress.
> See [overview.md](overview.md) for current capabilities.

# Ledgerly

Private cash and document assistant — track CDs and obligations, ingest financial PDFs, ask questions over your own data.

## Quick links

- [Overview & architecture](overview.md)
- [Install (portable / Docker)](install-instructions.md)
- [Developer setup & testing](setup_and_testing.md)
- [Product principles & privacy](FINANCIAL-ASSISTANT.md)
- [User guide](static/help.html)

## Quick start

```bash
docker compose up -d
```

Then open **http://localhost:8000/**

## Upgrading from an older install

If you installed Ledgerly when Docker Postgres used the old `finelly` credentials, back up first, then reset the database volume:

```bash
# Back up with old credentials (only if the old stack still runs):
docker compose exec -T postgres pg_dump -U finelly -d finelly -Fc -f /tmp/ledgerly-backup.dump
docker compose cp postgres:/tmp/ledgerly-backup.dump ./ledgerly-backup.dump

# Reset volume and start fresh with ledgerly credentials:
docker compose down -v
docker compose up -d

# Optional restore into the new database:
docker compose cp ./ledgerly-backup.dump postgres:/tmp/ledgerly-restore.dump
docker compose exec -T postgres pg_restore -U ledgerly -d ledgerly --clean --if-exists /tmp/ledgerly-restore.dump
```

See [install-instructions.md](install-instructions.md) for portable Windows backup steps.
