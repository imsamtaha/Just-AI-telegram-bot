import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { openStorage } from '../storage.mjs';
import { deliverDue } from '../reminders.mjs';
import { telegramClient,checkWebhook } from '../telegram.mjs';
import { loadConfig } from '../config.mjs';
import { createHandler } from '../../cloud/tgcloud/lib/core.js';

function setup(){const state=openStorage(':memory:');const sent=[];return {...state,sent,api:{sendMessage:async m=>sent.push(m)}};}
test('automatic reminder delivers without any new user message',async()=>{
 const h=setup();try{await h.store.login('1',0,10000);await h.store.schedule('1','review',100);
 await deliverDue({...h,now:()=>101});assert.equal(h.sent[0].text,'Follow-up / متابعة:\nreview');assert.equal((await h.store.reminders('1')).length,0);
 await deliverDue({...h,now:()=>102});assert.equal(h.sent.length,1);}finally{h.close();}
});
test('SQLite persists overdue reminders and sessions after restart',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'justai-runtime-')),path=join(dir,'bot.sqlite3');let h=openStorage(path);
 try{await h.store.login('1',0,10000);await h.store.schedule('1','restart',100);h.close();h=openStorage(path);
 const sent=[];await deliverDue({...h,api:{sendMessage:async m=>sent.push(m)},now:()=>1000});assert.equal(sent.length,1);
 }finally{h.close();rmSync(dir,{recursive:true,force:true});}
});
test('logout and expiry pause delivery until session renewed',async()=>{
 const h=setup();try{await h.store.login('1',0,50);await h.store.schedule('1','pause',10);await deliverDue({...h,now:()=>100});assert.equal(h.sent.length,0);
 await h.store.login('1',100,1000);await h.store.logout('1');await deliverDue({...h,now:()=>101});assert.equal(h.sent.length,0);
 await h.store.login('1',102,1000);await deliverDue({...h,now:()=>103});assert.equal(h.sent.length,1);}finally{h.close();}
});
test('concurrent ticks and cancelled reminders do not duplicate sends',async()=>{
 const h=setup();try{await h.store.login('1',0,10000);await h.store.schedule('1','once',10);
 await Promise.all([deliverDue({...h,now:()=>100}),deliverDue({...h,now:()=>100})]);assert.equal(h.sent.length,1);
 const id=await h.store.schedule('1','cancelled',10);const original=h.store.claim;
 h.store.claim=async(o,i)=>{await h.store.cancel(o,i);return original(o,i);};await deliverDue({...h,now:()=>101});assert.equal(h.sent.length,1);
 assert.equal((await h.store.reminders('1')).length,0);}finally{h.close();}
});
test('known Telegram rate limit retries after delay; uncertain failures do not auto-resend',async()=>{
 const h=setup();try{await h.store.login('1',0,1000000);await h.store.schedule('1','retry',10);let attempts=0;
 const api={sendMessage:async()=>{if(++attempts===1)throw {code:429,retryAfter:10};}};
 await deliverDue({...h,api,now:()=>100,log:()=>{}});await deliverDue({...h,api,now:()=>101});assert.equal(attempts,1);
 await deliverDue({...h,api,now:()=>10100});assert.equal(attempts,2);
 await h.store.schedule('1','uncertain',10);await deliverDue({...h,api:{sendMessage:async()=>{throw {code:0};}},now:()=>10200,log:()=>{}});
 assert.equal((await h.store.reminders('1'))[0].status,'uncertain');await deliverDue({...h,now:()=>10300});assert.equal(h.sent.length,0);
 }finally{h.close();}
});
test('post-send database error leaves claimed status instead of duplicating next tick',async()=>{
 const h=setup();try{await h.store.login('1',0,10000);await h.store.schedule('1','db fail',1);h.store.complete=async()=>{throw new Error('DB');};
 await assert.rejects(deliverDue({...h,now:()=>10}),/DB/);assert.equal(h.sent.length,1);await deliverDue({...h,now:()=>11});assert.equal(h.sent.length,1);
 assert.equal((await h.store.reminders('1'))[0].status,'sending');}finally{h.close();}
});
test('active webhook is preserved unless explicit takeover is requested',async()=>{
 const calls=[];const api={getWebhookInfo:async()=>({url:'https://cloud.telegram.org/example'}),deleteWebhook:async p=>calls.push(p)};
 await assert.rejects(checkWebhook(api),/active/);assert.equal(calls.length,0);
 await checkWebhook(api,true);assert.deepEqual(calls,[{drop_pending_updates:false}]);
});
test('Telegram HTTP errors never expose the bot token in their message',async()=>{
 const api=telegramClient('private-token',async()=>({ok:false,status:401,json:async()=>({ok:false,error_code:401})}));
 await assert.rejects(api.getMe(),e=>e.code===401&&!String(e).includes('private-token'));
});
test('configuration uses credentials only from private environment',()=>{
 assert.throws(()=>loadConfig({}),/TELEGRAM_BOT_TOKEN/);
 const c=loadConfig({AI_PROVIDER:'openai',TELEGRAM_BOT_TOKEN:'test-token',OPENAI_API_KEY:'test-key',OPENAI_MODEL:'m'});
 assert.equal(c.automaticReminders,true);assert.equal(c.model,'m');
});
test('native mode confirms automatic reminders and leaves delivery to worker',async()=>{
 const h=setup();try{const sent=[];await h.store.login('1',0,10000000);
 const handler=createHandler({store:h.store,api:{sendMessage:async m=>sent.push(m)},fetch:async()=>{throw new Error('not expected');},
 config:{automaticReminders:true},now:()=>100});
 await handler({message_id:1,from:{id:1},chat:{id:1,type:'private'},text:'/followup 1m test'});
 assert.match(sent.at(-1).text,/Automatic reminders/);
 await handler({message_id:2,from:{id:1},chat:{id:1,type:'private'},text:'/ذكرني ١د تجربة'});
 assert.match(sent.at(-1).text,/تلقائياً/);
 }finally{h.close();}
});
