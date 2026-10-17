# DelegatorAI

DelegatorAI is a project coordinator with a FastAPI backend, SQLite persistence,
a React dashboard, Slack messaging, and NVIDIA-hosted GPT-OSS-20B. The
dashboard reads persisted participants, tasks, and activity. The Slack app
handles mapped project channels, threaded task updates, reminders, and
coordinator questions.

## Local setup (Windows PowerShell)

Requires Python 3.11 or newer and Node.js 18 or newer (Node.js 20 or newer is
recommended).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm install
```

Set `LLM_API_KEY` to your NVIDIA API key, and set `SLACK_BOT_TOKEN` and
`SLACK_SIGNING_SECRET` in `.env`. `LLM_BASE_URL` and `LLM_MODEL` default to
NVIDIA's OpenAI-compatible endpoint and GPT-OSS-20B. Set the Slack channel map
after creating the app; an example is included in `.env.example`. Never commit
`.env` or put secrets in `VITE_*` variables.

Initialize an empty local database with safe sample records:

```powershell
python seed.py
```

Seeding uses insert-if-missing behavior. The sample project is `college-app`;
seed participant IDs include `p-kabir`, `p-maya`, `p-anjali`, `p-rohan`, and
`p-leena`.

## Create and configure the Slack app

1. At <https://api.slack.com/apps>, choose **Create New App** and create an app
   for the workspace where your project team works.
2. Open **OAuth & Permissions** and add these bot token scopes:
   - `chat:write` to send messages.
   - `channels:history` to receive public-channel messages in subscribed
     channels.
   - `app_mentions:read` to receive bot mentions.
   - Add `groups:history` only if you will map private channels.
3. Open **Event Subscriptions**, enable events, and set the Request URL to
   `https://YOUR_PUBLIC_HOST/slack/events`. Slack sends a signed URL-verification
   challenge; the backend validates it and returns the challenge.
4. Subscribe to the bot events `app_mention` and `message.channels`. Add
   `message.groups` only for private project channels.
5. Click **Install to Workspace** (or reinstall after changing scopes). Invite
   the bot into each mapped channel. It does not request `chat:write.public`.
6. From **OAuth & Permissions**, copy the **Bot User OAuth Token** (starts with
   `xoxb-`). From **Basic Information → App Credentials**, copy the **Signing
   Secret**. Keep both private.
7. In the workspace, find the bot's Slack member ID (starts with `U` or `W`).
   Configure it as `SLACK_BOT_USER_ID` when known. Find each participant's
   member ID in their Slack profile.
8. Edit `.env` with the app credentials, channel mapping, and admin IDs. The
   mapping is **channel ID to project ID**, for example:

   ```dotenv
   SLACK_PROJECT_CHANNELS={"C0123456789":"college-app"}
   SLACK_ADMIN_USER_IDS=U01234567
   SLACK_BOT_USER_ID=U09876543
   ```

   Copy a channel ID from that channel's details in Slack. Channel IDs must
   correspond exactly to `project_id` values in the task database. Admin Slack
   IDs in `SLACK_ADMIN_USER_IDS` may run the `link`, `create`, and `delegate`
   commands by mentioning the bot in a mapped channel.
9. Link task participants by mentioning the bot with
   `link PARTICIPANT_ID SLACK_USER_ID` in a mapped channel as a configured
   admin, for example `@DelegatorAI link p-kabir U12345678`.
   The linked Slack user must be the task owner to update that task.

If local `.env` edits are made while Uvicorn is running, restart Uvicorn so the
process reloads the new settings.

## Develop locally and test Slack

Start the backend in one PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in another terminal:

```powershell
npm run dev
```

The frontend uses `VITE_API_BASE_URL` or defaults to
`http://127.0.0.1:8000`. The backend allows localhost Vite origins by default;
configure `FRONTEND_ORIGINS` for any other origin.

Slack requires a public HTTPS URL to send events to a local machine. For
development, start a tunnel such as ngrok in another terminal:

```powershell
ngrok http 8000
```

Copy the temporary HTTPS forwarding address from ngrok, append `/slack/events`,
and enter that complete address as the Slack app's **Event Subscriptions**
Request URL. The temporary address changes when the tunnel restarts; update the
Slack Request URL then. Do not treat a development tunnel as a production URL.
For deployment, use a stable HTTPS host and durable storage.

For production, configure the same secrets and channel mapping as deployment
environment variables (not a committed file), serve the API through HTTPS,
disable Uvicorn reload mode, and monitor the `slack_events` table for records
that reach `failed`. Keep SQLite on persistent storage and run a single
application instance for this SQLite-backed worker. A local tunnel is for
development only.

These are message commands, not registered Slack Slash Commands. In a mapped
channel, mention the bot to invoke one. For example:

- `@DelegatorAI help` or `@DelegatorAI start` for commands and setup guidance.
- `@DelegatorAI tasks` to list your tasks in that project.
- `@DelegatorAI task TASK_ID` to see one of your assigned tasks.
- `@DelegatorAI report TASK_ID your update` to have the AI interpret and record progress,
  blockers, or a clarification request.
- Reply in a task's Slack thread to report progress. Only its linked owner can
  change that task; ambiguous replies do not mark it complete.
- Mention `@DelegatorAI` with a project question for a read-only summary.
- `@DelegatorAI create title | participant_id | YYYY-MM-DD | completion criteria` as a
  configured admin to create and assign a task to a linked participant.
- `@DelegatorAI delegate a natural-language task request` as a configured admin to ask the
  configured NVIDIA model to propose the title, criteria, due date, and a linked owner using
  current project workload. The server validates the proposal before creating
  the task; invalid proposals do not change project state.

Task creation/assignment via `create` and `delegate` is an explicit admin action. The
coordinator chat summarizes context but does not claim to take actions. For
security, the Slack signature is checked against the raw request body and
timestamp, event IDs are persisted before acknowledging Slack, and bot messages
are ignored. Replies are posted in threads and use stable Slack message IDs on
retries. Events that repeatedly fail are retained with a failed status for
inspection in SQLite.

## Dashboard API and persistence

The sign-in page is a UI demo; authentication is not connected. The workspace
uses the backend for task and participant data:

- `GET /participants`, `GET /tasks`
- `POST /tasks`, `PATCH /tasks/{id}`
- `GET /tasks/{id}/history`
- `POST /tasks/{id}/follow-up` sends a real Slack message in the mapped project
  channel and persists it only after Slack accepts it.
- `POST /assistant/chat` answers questions using current task context.

SQLite stores project tasks, task audit history, accepted Slack events, and
Slack conversation records. Keep the database on durable storage for
production; do not use an ephemeral database or share a local SQLite file
between multiple app instances. Existing Telegram and Google Chat history
columns/tables are retained during this migration and are not used by the Slack
worker.

## Troubleshooting

- **Slack shows “Your URL didn't respond with the value of the challenge”**:
  ensure the Request URL ends in `/slack/events`, the backend is reachable, and
  `SLACK_SIGNING_SECRET` is the signing secret for that same app.
- **401 / invalid signature**: restart Uvicorn after changing `.env`, verify the
  signing secret, and ensure a proxy or tunnel does not modify the raw request
  body. Slack timestamps outside the five-minute replay window are rejected.
- **No message or task update**: check that the event channel ID maps to the
  intended project, the bot is a member of the channel, event subscriptions and
  scopes match public/private channel use, and each task owner has a linked
  Slack user ID.
- **`not_in_channel`**: invite the bot to the mapped channel. Do not grant
  `chat:write.public` as a workaround.
- **429 / rate limited**: the worker honors Slack's `Retry-After` value and
  retries the persisted event. Repeated failures remain in the
  `slack_events` table.
- **AI response unavailable**: check `LLM_API_KEY`, `LLM_BASE_URL`, and
  `LLM_MODEL`. Missing configuration and provider errors are surfaced rather
  than replaced with a simulated answer.
- **Dashboard has no participants/tasks**: run `python seed.py`; it preserves
  existing records.

## Verification

```powershell
python -m pytest -q
npm run build
```

Tests mock the Slack Web API and NVIDIA-backed provider; they do not require
credentials or a real Slack workspace. Passing tests do not verify live Slack
delivery or provider credentials.
