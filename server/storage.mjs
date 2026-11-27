import { DatabaseSync } from 'node:sqlite';
import { mkdirSync, chmodSync } from 'node:fs';
import { dirname } from 'node:path';
import { createStore } from '../cloud/tgcloud/lib/store.js';
export function openStorage(path){
  if(path!==':memory:')mkdirSync(dirname(path),{recursive:true,mode:0o700});
  const sqlite=new DatabaseSync(path);
  sqlite.exec(`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;
    CREATE TABLE IF NOT EXISTS justai_turns(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT NOT NULL,user_text TEXT NOT NULL,assistant_text TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS justai_notes(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT NOT NULL,content TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS justai_reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT NOT NULL,content TEXT NOT NULL,due INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending');
    CREATE TABLE IF NOT EXISTS justai_locks(owner TEXT PRIMARY KEY,token TEXT NOT NULL,until_time INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS justai_processed(id TEXT PRIMARY KEY,owner TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS justai_sessions(owner TEXT PRIMARY KEY,created INTEGER NOT NULL,expires INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS justai_runtime(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS justai_reminders_due ON justai_reminders(status,due);
    CREATE INDEX IF NOT EXISTS justai_turns_owner ON justai_turns(owner,id);
    CREATE INDEX IF NOT EXISTS justai_notes_owner ON justai_notes(owner,id);`);
  if(!sqlite.prepare('PRAGMA table_info(justai_reminders)').all().some(c=>c.name==='retry_after'))
    sqlite.exec('ALTER TABLE justai_reminders ADD COLUMN retry_after INTEGER NOT NULL DEFAULT 0');
  if(path!==':memory:')chmodSync(path,0o600);
  const db={
    run:async(sql,params={})=>{const r=sqlite.prepare(sql).run(params);return {rowsAffected:Number(r.changes),lastInsertRowid:Number(r.lastInsertRowid)};},
    get:async(sql,params={})=>sqlite.prepare(sql).get(params),all:async(sql,params={})=>sqlite.prepare(sql).all(params),
  };
  const store=createStore(db);
  return {db,store,close:()=>sqlite.close()};
}
