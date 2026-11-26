import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../tgcloud/lib/core.js';
import { createCallbackHandler } from '../tgcloud/lib/access.js';
import { editionActions, editionPanel, marketSnapshot } from '../tgcloud/lib/edition.js';

function harness({logged=true,brokenMarket=false,brokenAI=false}={}){
  const sent=[],requests=[],seen=new Set();let active=logged,aiCalls=0,privateOwner;let id=0;
  const api={sendMessage:async m=>sent.push(m),sendChatAction:async()=>{},answerCallbackQuery:async()=>{}};
  const store={seen:async i=>seen.has(i),mark:async i=>seen.add(i),lock:async()=>true,unlock:async()=>{},
    session:async()=>active?{expires:999999999}:null,login:async()=>{active=true;},logout:async()=>{active=false;},
    reminders:async o=>{privateOwner=o;return [{id:1,status:'pending',due:999999999}]},
    context:async o=>{privateOwner=o;return {notes:['My preference'],history:[]};},turn:async()=>{},
  };
  const fetch=async(url,init)=>{
    requests.push(url);
    if(init?.method==='POST'){
      aiCalls++;if(brokenAI)return {ok:false,status:401};
      const p=JSON.parse(init.body);assert.match(p.input.at(-1).content,/Source: Coinbase/);
      assert.match(p.instructions,/Never invent news/);
      return {ok:true,json:async()=>({output_text:'Observed facts: supplied data only.'})};
    }
    if(brokenMarket)return {ok:false,status:503};
    if(url.endsWith('/ticker'))return {ok:true,json:async()=>({price:'100',time:'1970-01-01T20:00:00Z'})};
    return {ok:true,json:async()=>Array.from({length:21},(_,i)=>[i*3600,1,200,i+80,i+80,1])};
  };
  const handler=createHandler({api,store,fetch,config:{provider:'openai',apiKey:'test',model:'m',systemPrompt:'Base'},now:()=>72001000});
  return {sent,requests,api,handler,aiCalls:()=>aiCalls,privateOwner:()=>privateOwner,
    run:async text=>handler({message_id:++id,from:{id:7,first_name:'Sam'},chat:{id:7,type:'private'},text})};
}
test('bilingual panels have bounded known callbacks and no unsupported actions',()=>{
  for(const ar of [true,false])for(const kind of ['home','studio','workspace']){
    const panel=editionPanel(kind,ar);assert.ok(panel.text);
    for(const row of panel.reply_markup.inline_keyboard)for(const b of row){
      assert.ok(b.callback_data.length<=64);assert.ok(editionActions[b.callback_data]);
    }
  }
});
test('login exposes special edition actions and home is personalized without AI',async()=>{
  const h=harness({logged:false});await h.run('/login');
  assert.match(h.sent.at(-1).text,/SPECIAL EDITION/);assert.ok(h.sent.at(-1).reply_markup);
  await h.run('/home');assert.match(h.sent.at(-1).text,/Welcome, Sam/);assert.equal(h.aiCalls(),0);
});
test('market desk composes real tools and AI briefing is grounded in tool output',async()=>{
  const h=harness();await h.run('/desk BTC-USD 1h');
  assert.match(h.sent.at(-1).text,/MARKET SNAPSHOT/);assert.match(h.sent.at(-1).text,/SMA20/);assert.equal(h.aiCalls(),0);
  await h.run('/brief BTC-USD 1h');assert.equal(h.aiCalls(),1);
  assert.match(h.sent.at(-1).text,/Observed facts: supplied data only/);
});
test('bad or unavailable data never triggers AI and errors preserve valid snapshot',async()=>{
  const h=harness({brokenMarket:true});await h.run('/brief BTC-USD 1h');
  assert.match(h.sent.at(-1).text,/unavailable/);assert.equal(h.aiCalls(),0);
  const good=harness({brokenAI:true});await good.run('/brief BTC-USD 1h');
  assert.match(good.sent.at(-1).text,/MARKET SNAPSHOT/);assert.match(good.sent.at(-1).text,/AI interpretation is unavailable/);
  let called=false;const r=await marketSnapshot('../secret 1h',async()=>{called=true;},0,false);
  assert.equal(r.ok,false);assert.equal(called,false);
});
test('workspace is scoped and blank skill does not spend an AI request',async()=>{
  const h=harness();await h.run('/workspace');assert.equal(h.privateOwner(),'7');assert.match(h.sent.at(-1).text,/Saved notes: 1/);
  await h.run('/writer');assert.match(h.sent.at(-1).text,/followed by your request/);assert.equal(h.aiCalls(),0);
});
test('edition buttons route through the private login gate',async()=>{
  const h=harness({logged:false}),callback=createCallbackHandler({api:h.api,handleMessage:h.handler});
  await callback({id:'q',data:'ed_brief_ar',from:{id:7},message:{message_id:50,chat:{id:7,type:'private'}}},{update:{update_id:200}});
  assert.equal(h.requests.length,0);assert.match(h.sent.at(-1).text,/سجّل دخول/);
});
test('Arabic home and market desk commands work',async()=>{
  const h=harness();await h.run('/الرئيسية');assert.match(h.sent.at(-1).text,/أهلا/);
  await h.run('/مكتب_السوق BTC-USD ١س');assert.match(h.sent.at(-1).text,/لقطة السوق/);
});
