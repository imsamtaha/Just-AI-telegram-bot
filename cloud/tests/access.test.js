import test from 'node:test';
import assert from 'node:assert/strict';
import { requirePrivateLogin, createCallbackHandler, SESSION_MS } from '../tgcloud/lib/access.js';
import { createHandler } from '../tgcloud/lib/core.js';

function harness(){
  const messages=[],sessions=new Map(),acks=[],seen=new Set();let clock=0,privateReads=0,aiCalls=0;
  const api={sendMessage:async p=>messages.push(p),sendChatAction:async()=>{},answerCallbackQuery:async p=>acks.push(p)};
  const store={
    session:async o=>sessions.get(o),login:async(o,created,expires)=>sessions.set(o,{owner:o,created,expires}),logout:async o=>sessions.delete(o),
    seen:async i=>seen.has(i),mark:async i=>seen.add(i),lock:async()=>true,unlock:async()=>{},
    context:async()=>{privateReads++;return {history:[],notes:[]};},reminders:async()=>{privateReads++;return [];},turn:async()=>{},
  };
  const handler=createHandler({api,store,config:{provider:'openai',model:'m',apiKey:'test',systemPrompt:'Base'},now:()=>clock,
    fetch:async()=>{aiCalls++;return {ok:true,json:async()=>({output_text:'Hello'})};}});
  let id=0;
  const message=(text,owner=1,type='private',from=owner)=>({message_id:++id,chat:{id:owner,type},from:{id:from},text});
  return {api,store,messages,sessions,acks,handler,message,clock:n=>{clock=n;},privateReads:()=>privateReads,aiCalls:()=>aiCalls,
    gate:async(command,owner=1,arabic=false)=>requirePrivateLogin({message:message(command,owner),command,arabic,api,store,now:clock})};
}
test('unauthenticated AI, tools and memory requests cannot read private data or call AI',async()=>{
  const h=harness();
  for(const text of ['Hello','/memory','/followups','/calc 2+2'])await h.handler(h.message(text));
  assert.equal(h.privateReads(),0);assert.equal(h.aiCalls(),0);
  assert.equal(h.messages.at(-1).reply_markup.inline_keyboard[0][0].callback_data,'justai_login');
});
test('Telegram self login grants own session; no owner from command arguments',async()=>{
  const h=harness();await h.handler(h.message('/login 999'));
  assert.equal(h.sessions.has('1'),true);assert.equal(h.sessions.has('999'),false);
  assert.equal(h.sessions.get('1').expires,SESSION_MS);
  await h.handler(h.message('Hello'));assert.equal(h.aiCalls(),1);
  await h.handler(h.message('Hello',2));assert.equal(h.aiCalls(),1);
});
test('expiry and logout require re-login before private access',async()=>{
  const h=harness();await h.gate('/login');h.clock(SESSION_MS);
  assert.equal(await h.gate('/memory'),false);
  await h.gate('/login');assert.equal(await h.gate('/memory'),true);
  await h.gate('/logout');assert.equal(await h.gate('/memory'),false);assert.equal(h.sessions.size,0);
});
test('groups and mismatched Telegram identities cannot establish sessions',async()=>{
  const h=harness();await h.handler(h.message('/login',-100,'group',1));
  assert.equal(h.sessions.size,0);assert.equal(h.privateReads(),0);
  assert.equal(h.messages.at(-1).reply_markup.inline_keyboard[0][0].url,'https://t.me/JustAI_chatbot?start=login');
  await h.handler(h.message('/login',1,'private',2));assert.equal(h.sessions.size,0);
  const missing=h.message('/login');delete missing.from;await h.handler(missing);assert.equal(h.sessions.size,0);
});
test('Arabic login, logout and privacy flow',async()=>{
  const h=harness();await h.handler(h.message('/مساعدة'));
  assert.match(h.messages.at(-1).text,/سجّل دخول/);
  assert.equal(h.messages.at(-1).reply_markup.inline_keyboard[0][0].callback_data,'justai_login_ar');
  await h.handler(h.message('/دخول'));assert.equal(h.sessions.has('1'),true);
  await h.handler(h.message('/خصوصية'));assert.match(h.messages.at(-1).text,/مش محادثة مشفّرة/);
  await h.handler(h.message('/خروج'));assert.equal(h.sessions.has('1'),false);
});
test('private login button uses callback actor and Telegram update identity',async()=>{
  const h=harness(),callback=createCallbackHandler({api:h.api,handleMessage:h.handler});
  const query={id:'q',data:'justai_login',from:{id:7},message:{message_id:40,chat:{id:7,type:'private'}}};
  await callback(query,{update:{update_id:100}});
  assert.equal(h.sessions.has('7'),true);assert.equal(h.acks[0].callback_query_id,'q');
  await callback(query,{update:{update_id:100}});assert.equal(h.messages.length,1);
});
test('forged, group, contextless and unknown callbacks cannot log in',async()=>{
  const h=harness(),callback=createCallbackHandler({api:h.api,handleMessage:h.handler});
  const q={id:'q',data:'justai_login',from:{id:7},message:{message_id:40,chat:{id:8,type:'private'}}};
  await callback(q,{update:{update_id:100}});
  await callback({...q,message:{message_id:40,chat:{id:7,type:'group'}}},{update:{update_id:101}});
  await callback({...q,message:{message_id:40,chat:{id:7,type:'private'}}});
  await callback({...q,data:'unknown'},{update:{update_id:102}});
  assert.equal(h.sessions.size,0);
});
test('missing session storage fails closed before any AI request',async()=>{
  const h=harness();h.store.session=async()=>{throw new Error('DB offline');};
  await assert.rejects(h.handler(h.message('Hello')),/DB offline/);assert.equal(h.aiCalls(),0);assert.equal(h.privateReads(),0);
});

test('entry exposes Arabic and English buttons before authentication',async()=>{
  const h=harness();await h.handler(h.message('/start'));
  const buttons=h.messages.at(-1).reply_markup.inline_keyboard.flat();
  assert.ok(buttons.some(b=>b.text==='العربية'&&b.callback_data==='justai_language_ar'));
  assert.ok(buttons.some(b=>b.text==='English'&&b.callback_data==='justai_language_en'));
  assert.match(h.messages.at(-1).text,/تختار العربية/);assert.equal(h.sessions.size,0);
});
test('Arabic language choice localizes entry without granting a session',async()=>{
  const h=harness(),callback=createCallbackHandler({api:h.api,handleMessage:h.handler});
  const q={id:'language',data:'justai_language_ar',from:{id:7},message:{message_id:40,chat:{id:7,type:'private'}}};
  await callback(q,{update:{update_id:101}});
  assert.match(h.messages.at(-1).text,/أهلا فيك/);assert.equal(h.sessions.size,0);
  assert.equal(h.messages.at(-1).reply_markup.inline_keyboard[0][0].callback_data,'justai_login_ar');
  await callback({...q,id:'login',data:'justai_login_ar'},{update:{update_id:102}});
  assert.equal(h.sessions.has('7'),true);assert.match(h.messages.at(-1).text,/سجّلت دخولك/);
});
test('Arabic device starts in Arabic but explicit English switches entry back',async()=>{
  const h=harness(),m=h.message('/start');m.from.language_code='ar-LB';await h.handler(m);
  assert.match(h.messages.at(-1).text,/أهلا فيك/);
  const callback=createCallbackHandler({api:h.api,handleMessage:h.handler});
  await callback({id:'en',data:'justai_language_en',from:{id:1,language_code:'ar'},message:{message_id:40,chat:{id:1,type:'private'}}},{update:{update_id:105}});
  assert.match(h.messages.at(-1).text,/Welcome to Just AI/);
  assert.equal(h.messages.at(-1).reply_markup.inline_keyboard[0][0].callback_data,'justai_login');
  assert.equal(h.sessions.size,0);
});
