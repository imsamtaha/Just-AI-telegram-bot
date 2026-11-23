import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { createStore } from '../tgcloud/lib/store.js';
function database(){
  const db=new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE justai_locks(owner TEXT PRIMARY KEY, token TEXT NOT NULL,until_time INTEGER NOT NULL);
    CREATE TABLE justai_turns(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT,user_text TEXT,assistant_text TEXT);
    CREATE TABLE justai_notes(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT,content TEXT);
    CREATE TABLE justai_reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT,content TEXT,due INTEGER,status TEXT);
    CREATE TABLE justai_processed(id TEXT PRIMARY KEY,owner TEXT);`);
  return {db,store:createStore({
    run:async(sql,params)=>{const r=db.prepare(sql).run(params);return {rowsAffected:Number(r.changes),lastInsertRowid:Number(r.lastInsertRowid)};},
    all:async(sql,params)=>db.prepare(sql).all(params),get:async(sql,params)=>db.prepare(sql).get(params),
  })};
}
test('real SQLite memory bounds, ordering and isolation',async()=>{
  const {db,store:s}=database();try{
    for(let i=0;i<10;i++)await s.turn('1',`q${i}`,`a${i}`);
    for(let i=0;i<25;i++)await s.note('1',`n${i}`);
    const c=await s.context('1');assert.equal(c.history.length,12);assert.equal(c.history[0].content,'q4');assert.equal(c.notes.length,20);
    assert.deepEqual(await s.context('2'),{history:[],notes:[]});await s.forget('1');assert.deepEqual(await s.context('1'),{history:[],notes:[]});
  }finally{db.close();}
});
test('real SQLite lease exclusion, expiry, and dedup pruning',async()=>{
  const {db,store:s}=database();try{
    assert.equal(await s.lock('1','a',0),true);assert.equal(await s.lock('1','b',1),false);
    await s.unlock('1','b');assert.equal(await s.lock('1','b',2),false);
    assert.equal(await s.lock('1','b',300001),true);await s.unlock('1','b');assert.equal(await s.lock('1','c',300002),true);
    for(let i=0;i<110;i++)await s.mark(String(i),'1');assert.equal(await s.seen('0'),false);assert.equal(await s.seen('109'),true);
  }finally{db.close();}
});
test('real SQLite reminder claims, non-reused IDs, owner cancellation',async()=>{
  const {db,store:s}=database();try{
    const id=await s.schedule('1','hello',60000);assert.equal(await s.cancel('2',id),false);
    assert.equal(await s.claim('1',id),true);assert.equal(await s.claim('1',id),false);
    await s.failed('1',id);assert.equal((await s.reminders('1'))[0].status,'uncertain');
    await s.complete('1',id);const second=await s.schedule('1','again',120000);assert.ok(second>id);
    await s.complete('1',id);assert.equal((await s.reminders('1')).length,1);
  }finally{db.close();}
});
