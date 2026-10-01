# Nexus Discord Bot

A Discord server controller: role-based layout, verification and clearance
approval, tickets, temporary voice rooms, AutoMod, anti-raid, XP levels,
economy, shop, starboard, suggestions and audit logs. SQLite database and a
`/health` endpoint for hosting.

## Project files

| File | Purpose |
|---|---|
| `bot.py` | Bot, events and slash/prefix commands |
| `layout.py` | **Single source of truth**: roles, hierarchy, categories, channels, who can see / write |
| `views.py` | Persistent buttons, modals and embeds |
| `database.py` | SQLite layer (atomic pay / daily / buy / votes) |
| `render.yaml`, `requirements.txt`, `.env.example`, `.gitignore` | Deployment |

## Role system

Hierarchy (top to bottom): **Admin → Moderator → Support Team → Developer →
Elite Agent → VIP → Streamer / Artist / Musician → Verified → Guest Node →
Veteran / Operative / Recruit** (cosmetic level roles).

| Sector | Who sees it | Who writes |
|---|---|---|
| 00 Gateway | everyone (read only) | staff |
| 01 Clearance, 04 Services | Verified | panels only |
| 02 Terminal, 05 Archive | approved roles + Guest (read only) | approved roles |
| 03 Nodes (voice) | approved roles | approved roles |
| 06 Control + all logs | Admin, Moderator | staff |
| 07 Dev Ops | Developer | Developer |
| 08 Vault | Elite, VIP, creators; each channel has its own role | per channel |

Admin and Moderator always see everything. To change the server, edit the
tables at the top of `layout.py` and run `/setup`.

Level roles (Recruit 5, Operative 10, Veteran 20) are cosmetic and never open
channels. Reaction roles and shop roles cannot hand out staff, Nexus or
moderation-permission roles.

## Discord configuration

1. Developer Portal > Bot > enable **Server Members Intent** and
   **Message Content Intent** (the bot will not start without them).
2. Invite with the `bot` and `applications.commands` scopes. The simplest
   permission is **Administrator** (the bot creates the Admin role and manages
   every channel and role).
3. In Server Settings > Roles, drag the bot's role **above all Nexus roles**.
   Role order, the Moderator approval limits and `/setup` depend on it.

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python bot.py
```

Python 3.11 or newer is required. Set `DISCORD_TOKEN` in `.env`; never push it.
Use `DEV_GUILD_ID` while testing.

## Render deployment

1. Push the contents of this folder to a GitHub repository.
2. Render > **New > Blueprint**, connect the repository (`render.yaml` creates a Web Service).
3. Enter `DISCORD_TOKEN` in the environment variables screen.
4. Deploy, then run `/setup` once as an administrator.
5. UptimeRobot: add an HTTP monitor on `https://YOUR-SERVICE.onrender.com/health`
   every 5 minutes so the free service does not sleep.

**Data persistence:** on the free plan the disk is wiped on every redeploy or
restart, so XP, economy and warnings reset. For permanent data use a paid
instance with a persistent disk and set `DB_PATH=/var/data/nexus.db`.

## Commands

Members: `/rank /leaderboard /balance /daily /pay /work /economyboard /shop /buy /poll /suggest /8ball /coinflip /serverinfo`

Staff: `/warn /warnings /clearwarns /kick /ban /unban /timeout /purge /clear /say /embed /verify /automod /reactionrole /raidon /raidoff /status`

Admin: `/setup` (safe, never deletes), `/shopadmin`, `/reset` (owner only, deletes everything and rebuilds).

Prefix commands use `Sl` (for example `Slsetup`, `Slverify @user`).

## Security notes

- Kick, ban and timeout check role hierarchy for the person using the command.
- AutoMod uses real Discord timeouts (a Muted role cannot work when other roles allow sending).
- Staff are exempt from AutoMod. XP has a 30 second cooldown per member.
- `/pay`, `/daily` and `/buy` are atomic, so they cannot be double-spent.
