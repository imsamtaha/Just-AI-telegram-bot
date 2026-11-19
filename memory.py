"""Durable, bounded private-chat memory and restart-safe reminders."""
import sqlite3
import time
from pathlib import Path


class Memory:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value INTEGER);
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, owner TEXT, role TEXT, content TEXT);
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, owner TEXT, content TEXT);
        CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY, owner TEXT, chat_id INTEGER,
          content TEXT, due REAL, attempts INTEGER DEFAULT 0, status TEXT DEFAULT 'pending');
        ''')
        if str(path) != ':memory:':
            Path(path).chmod(0o600)

    def history(self, owner):
        return [dict(r) for r in self.db.execute(
            'SELECT role,content FROM history WHERE owner=? ORDER BY id', (owner,))]

    def remember_turn(self, owner, user, answer):
        with self.db:
            self.db.executemany('INSERT INTO history(owner,role,content) VALUES(?,?,?)',
                                [(owner, 'user', user[:8000]), (owner, 'assistant', answer[:8000])])
            self.db.execute('DELETE FROM history WHERE owner=? AND id NOT IN '
                            '(SELECT id FROM history WHERE owner=? ORDER BY id DESC LIMIT 12)', (owner, owner))

    def notes(self, owner):
        return [r[0] for r in self.db.execute('SELECT content FROM notes WHERE owner=? ORDER BY id', (owner,))]

    def save_note(self, owner, content):
        with self.db:
            self.db.execute('INSERT INTO notes(owner,content) VALUES(?,?)', (owner, content[:1000]))
            self.db.execute('DELETE FROM notes WHERE owner=? AND id NOT IN '
                            '(SELECT id FROM notes WHERE owner=? ORDER BY id DESC LIMIT 20)', (owner, owner))

    def forget(self, owner):
        with self.db:
            self.db.execute('DELETE FROM history WHERE owner=?', (owner,))
            self.db.execute('DELETE FROM notes WHERE owner=?', (owner,))

    def schedule(self, owner, chat_id, text, due):
        if len(self.pending(owner)) >= 50:
            raise ValueError('You already have 50 pending follow-ups. Cancel one first.')
        with self.db:
            return self.db.execute('INSERT INTO reminders(owner,chat_id,content,due) VALUES(?,?,?,?)',
                                   (owner, chat_id, text[:2000], due)).lastrowid

    def pending(self, owner):
        return self.db.execute("SELECT * FROM reminders WHERE owner=? AND status='pending' ORDER BY due", (owner,)).fetchall()

    def followups(self, owner):
        return self.db.execute("SELECT * FROM reminders WHERE owner=? ORDER BY due", (owner,)).fetchall()

    def cancel(self, owner, reminder_id):
        with self.db:
            return self.db.execute("DELETE FROM reminders WHERE owner=? AND id=?",
                                   (owner, reminder_id)).rowcount > 0

    def due(self, now=None):
        return self.db.execute("SELECT * FROM reminders WHERE status='pending' AND due<=? ORDER BY due LIMIT 50",
                               (time.time() if now is None else now,)).fetchall()

    def delivered(self, reminder_id):
        with self.db:
            self.db.execute('DELETE FROM reminders WHERE id=?', (reminder_id,))

    def retry(self, reminder_id, now=None):
        with self.db:
            self.db.execute("UPDATE reminders SET attempts=attempts+1, due=?, "
                            "status=CASE WHEN attempts>=4 THEN 'failed' ELSE 'pending' END WHERE id=?",
                            ((time.time() if now is None else now) + 60, reminder_id))

    def offset(self):
        row = self.db.execute("SELECT value FROM state WHERE key='offset'").fetchone()
        return row[0] if row else None

    def set_offset(self, offset):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO state(key,value) VALUES('offset',?)", (offset,))

    def close(self):
        self.db.close()
