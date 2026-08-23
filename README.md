# Nexus Discord Bot

A production-oriented Discord server controller: persistent verification and self-role buttons, restart-safe tickets, slash commands, a small SQLite database, and a health endpoint.

## Why the previous setup stopped

The old command deleted every channel while it was still using its status message, swallowed every resulting exception, then continued to edit a deleted message. It also tried to delete categories twice. This version **never deletes anything** in `/setup`: it detects the existing category (including your partially-created `SECTOR 01`) and adds only missing pieces. It migrates the old category labels to the new visual style.

## Discord configuration

1. In the Discord Developer Portal, enable **Server Members Intent** under *Bot > Privileged Gateway Intents*.
2. Invite the bot with the `bot` and `applications.commands` scopes.
3. Grant it: View Channels, Send Messages, Embed Links, Read Message History, Manage Channels, Manage Roles, Manage Messages, and Manage Webhooks.
4. In the server role list, place the bot's role above `Verified`, `Elite Agent`, and `Guest Node`.

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python bot.py
```

Set `DISCORD_TOKEN` in `.env`; never put it in `bot.py` or push it to GitHub. `.env.example` is safe to commit because it contains only placeholder text. The included `.gitignore` prevents `.env` from being uploaded by Git. Set `DEV_GUILD_ID` during testing for immediate slash-command updates. Remove it for global deployment (global commands can take time to propagate).

## Render deployment

1. Push the **contents** of this folder to a new GitHub repository.
2. On Render choose **New > Blueprint** and connect that repository; `render.yaml` creates a Web Service (not a Background Worker).
3. Enter `DISCORD_TOKEN` in Render's environment-variable screen. Keep it secret.
4. Deploy. Open the server and run `/setup` once as an administrator.

The free Web Service can spin down after inactivity, so it is suitable for testing but not a dependable 24/7 bot host. The bot listens on Render's `PORT` and exposes `/health`; use a paid always-on web service or another always-on host when reliability matters.

## Commands

- `/setup` — safely creates or repairs the layout; it does not delete channels.
- `/clear amount:10` — removes 1–100 recent messages (requires Manage Messages).
- `/status` — health and latency.

The ticket buttons survive Render restarts. A member can have one active ticket at a time; the ticket owner or a channel manager can close it.
