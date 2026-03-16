# Remote log (Option B): Supabase table + Edge Function

Verbiage can send sanitized error reports (no PII) to a Supabase Edge Function, which inserts into `remote_log_events`. You view events in the Supabase dashboard.

## Prerequisites

- Install the [Supabase CLI](https://supabase.com/docs/guides/cli) (e.g. `brew install supabase/tap/supabase` on macOS).
- Log in once: `supabase login`.

## 1. Create the table

In Supabase: **SQL Editor** → New query → paste and run the migration:

- [supabase/migrations/20250311000000_remote_log_events.sql](migrations/20250311000000_remote_log_events.sql)

## 2. Deploy the Edge Function

From the **Verbiage** project root (the directory that contains this `supabase/` folder):

```bash
cd /path/to/verbiage
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy ingest-remote-log
```

Use your project ref from the Supabase dashboard URL: `https://app.supabase.com/project/YOUR_PROJECT_REF`. You may be prompted for the database password when linking.

Optional: set a shared secret so only your Verbiage instances can POST:

```bash
supabase secrets set REMOTE_LOG_SECRET=your-random-secret
```

Set the same value in Verbiage’s `.env` as `REMOTE_LOG_SECRET`.

## 3. Configure Verbiage

In Verbiage’s `.env`:

- `REMOTE_LOG_URL=https://YOUR_PROJECT_REF.supabase.co/functions/v1/ingest-remote-log`
- `REMOTE_LOG_SECRET=` (same as in Supabase secrets, or leave empty to disable auth)
- `REMOTE_LOG_INSTANCE_ID=` (optional; e.g. a UUID to identify “his” instance)

Restart Verbiage. Errors that hit the exception handlers will be sent to the Edge Function and stored in `remote_log_events`.
