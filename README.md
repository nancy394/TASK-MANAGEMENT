# TaskFlow — Task Management App (Python · Flask · SQLite · HTML · CSS)

## Modules
- **Authentication** – register, login, logout, hashed passwords
- **Dashboard** – stats, completion progress, upcoming deadlines, activity feed
- **Tasks** – create/edit/delete, status, priority, due dates, search, filters, sorting
- **Checklists (subtasks)** and **Comments** on each task
- **Projects** – colour-coded projects with a Kanban board (To do / In progress / Done)
- **Categories** – organise tasks by category
- **Reports** – charts by status/priority, 7-day completion chart, project table, CSV export
- **Profile** – update account info and change password
- **Activity log** – every action is recorded

## Run
```bash
python -m venv venv
# Windows: venv\Scripts\activate   |  macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 and register an account. The SQLite database (`taskflow.db`) is created automatically.

## Sound notifications
Each message type plays its own sound: saved (two rising notes), task completed (chime), info (ping),
warning (double beep), error (low buzz), focus start, focus end (bell) and break over.
Turn sounds on/off with the bell button in the top bar; change volume and preview sounds on the Focus Timer page.
Sound files are generated automatically in `static/sounds/` on first start.

## Focus timer with recording
Open **Focus Timer** in the sidebar. Choose Focus (25 min), Short break (5) or Long break (15), or type your own minutes.
Link a task, add a note and optionally tick **Record voice note** - your microphone records during the session.
Every session (time, task, note, recording) is saved in SQLite and shown in Session history, where recordings can be played back.
Recordings are stored in the `recordings/` folder. Microphone recording needs http://127.0.0.1 or localhost (or HTTPS).
