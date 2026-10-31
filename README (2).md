# Quiz Clash

A no-login, browser-based real-time multiplayer quiz for 2–6 players.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in a browser. For a local multiplayer test, open the URL in two or more browser tabs/devices on the same network (use your computer's LAN IP for other devices).

## Deploy a public link with Render

1. Create a GitHub repository named `quiz-clash`.
2. Upload the contents of this folder to the repository (keep `app/`, `requirements.txt`, and `render.yaml` at the repository root).
3. Sign in to Render and choose **New → Blueprint**.
4. Connect the GitHub repository and deploy the `render.yaml` blueprint.
5. Render will provide an HTTPS public URL. Share it with friends.

No API keys, database, login, or client installation are required for this starter deployment.

## Gameplay

- Host creates a room and shares the five-character code.
- 2–6 players join from the public URL.
- Host starts once at least two players are present.
- Eight randomly selected questions, 15 seconds each.
- Correct answers earn 500 base points plus a speed bonus.
- Live leaderboard and final winner screen.

## Important deployment note

This starter keeps room state in the server's memory. It is suitable for a single server instance and casual sessions. Rooms disappear if the server restarts or redeploys; use one instance (no horizontal autoscaling). For production-scale reliability, add Redis-backed room state, reconnect tokens, rate limiting, and automated tests. The app intentionally has no user accounts.
