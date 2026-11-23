export function createStore(db) { return {
  async lock(owner, token, now) {
    const result = await db.run(`INSERT INTO justai_locks(owner,token,until_time) VALUES(:o,:t,:n)
      ON CONFLICT(owner) DO UPDATE SET token=:t,until_time=:n WHERE until_time<:now`,
      {':o':owner, ':t':token, ':n':now+300000, ':now':now});
    return result.rowsAffected > 0;
  },
  async unlock(owner, token) { await db.run('DELETE FROM justai_locks WHERE owner=:o AND token=:t', {':o':owner, ':t':token}); },
  async seen(id) { return !!await db.get('SELECT id FROM justai_processed WHERE id=:id', {':id':id}); },
  async mark(id, owner) {
    await db.run('INSERT OR IGNORE INTO justai_processed(id,owner) VALUES(:id,:o)', {':id':id, ':o':owner});
    await db.run(`DELETE FROM justai_processed WHERE owner=:o AND rowid NOT IN
      (SELECT rowid FROM justai_processed WHERE owner=:o ORDER BY rowid DESC LIMIT 100)`, {':o':owner});
  },
  async context(owner) {
    const rows = await db.all('SELECT user_text,assistant_text FROM justai_turns WHERE owner=:o ORDER BY id DESC LIMIT 6', {':o':owner});
    const notes = await db.all('SELECT content FROM justai_notes WHERE owner=:o ORDER BY id', {':o':owner});
    return {history: rows.reverse().flatMap(r => [{role:'user',content:r.user_text},{role:'assistant',content:r.assistant_text}]), notes:notes.map(r=>r.content)};
  },
  async turn(owner, user, assistant) {
    await db.run('INSERT INTO justai_turns(owner,user_text,assistant_text) VALUES(:o,:u,:a)', {':o':owner, ':u':user.slice(0,8000), ':a':assistant.slice(0,8000)});
    await db.run(`DELETE FROM justai_turns WHERE owner=:o AND id NOT IN
      (SELECT id FROM justai_turns WHERE owner=:o ORDER BY id DESC LIMIT 6)`, {':o':owner});
  },
  async note(owner, content) {
    await db.run('INSERT INTO justai_notes(owner,content) VALUES(:o,:c)', {':o':owner, ':c':content});
    await db.run(`DELETE FROM justai_notes WHERE owner=:o AND id NOT IN
      (SELECT id FROM justai_notes WHERE owner=:o ORDER BY id DESC LIMIT 20)`, {':o':owner});
  },
  async forget(owner) {
    await db.run('DELETE FROM justai_turns WHERE owner=:o', {':o':owner});
    await db.run('DELETE FROM justai_notes WHERE owner=:o', {':o':owner});
  },
  async reminders(owner) { return await db.all('SELECT * FROM justai_reminders WHERE owner=:o ORDER BY due LIMIT 50', {':o':owner}); },
  async schedule(owner, content, due) {
    const count = await db.get('SELECT count(*) AS n FROM justai_reminders WHERE owner=:o', {':o':owner});
    if (count.n>=50) throw new Error('limit');
    const r = await db.run('INSERT INTO justai_reminders(owner,content,due,status) VALUES(:o,:c,:d,\'pending\')', {':o':owner, ':c':content, ':d':due});
    return r.lastInsertRowid;
  },
  async cancel(owner, id) { return (await db.run('DELETE FROM justai_reminders WHERE owner=:o AND id=:id', {':o':owner, ':id':id})).rowsAffected>0; },
  async claim(owner, id) { return (await db.run("UPDATE justai_reminders SET status='sending' WHERE owner=:o AND id=:id AND status='pending'", {':o':owner, ':id':id})).rowsAffected>0; },
  async complete(owner, id) { await db.run('DELETE FROM justai_reminders WHERE owner=:o AND id=:id', {':o':owner, ':id':id}); },
  async failed(owner, id) { await db.run("UPDATE justai_reminders SET status='uncertain' WHERE owner=:o AND id=:id", {':o':owner, ':id':id}); },
};
}
