import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler, send } from '../tgcloud/lib/core.js';
import { answer, AIError } from '../tgcloud/lib/ai.js';
import { calculate, runTool, indicators } from '../tgcloud/lib/tools.js';

function harness(){
  const sent=[],actions=[],contexts=new Map(),reminders=[],seen=new Set();let held=false,id=0;
  const get=o=>{if(!contexts.has(o))contexts.set(o,{notes:[],history:[]});return contexts.get(o);};
  const store={
    session:async()=>({expires:Number.MAX_SAFE_INTEGER}),login:async()=>{},logout:async()=>{},
    seen:async id=>seen.has(id),mark:async id=>seen.add(id),lock:async()=>{if(held)return false;held=true;return true;},unlock:async()=>{held=false;},
    context:async o=>get(o),note:async(o,n)=>get(o).notes.push(n),forget:async o=>contexts.delete(o),
    turn:async(o,u,a)=>get(o).history.push({role:'user',content:u},{role:'assistant',content:a}),
    reminders:async o=>reminders.filter(r=>r.owner===o),
    schedule:async(o,c,d)=>{reminders.push({id:++id,owner:o,content:c,due:d,status:'pending'});return id;},
    cancel:async(o,i)=>{const n=reminders.findIndex(r=>r.owner===o&&r.id===i);if(n<0)return false;reminders.splice(n,1);return true;},
    claim:async(o,i)=>{const r=reminders.find(r=>r.owner===o&&r.id===i);if(r.status!=='pending')return false;r.status='sending';return true;},
    complete:async(o,i)=>store.cancel(o,i),failed:async(o,i)=>{reminders.find(r=>r.owner===o&&r.id===i).status='uncertain';},
  };
  let request,clock=0;
  const api={sendMessage:async m=>sent.push(m),sendChatAction:async a=>actions.push(a)};
  const config={provider:'claude',apiKey:'test-only',model:'test-model',systemPrompt:'Base'};
  const fetch=async(url,init)=>{request=JSON.parse(init.body);return {ok:true,json:async()=>({content:[{type:'text',text:'AI reply'}]})};};
  const handler=createHandler({api,store,fetch,config,now:()=>clock});
  let messageId=0;
  const message=(text,owner=1,type='private',mid=++messageId)=>handler({message_id:mid,from:{id:owner},chat:{id:owner,type},text});
  return {sent,actions,store,contexts,reminders,config,fetch,message,api,setClock:n=>{clock=n;},request:()=>request};
}
test('bounded arithmetic without eval',()=>{
  assert.equal(calculate('(2500*.02)/5'),10);assert.equal(calculate('-2**2'),-4);
  for(const input of ['globalThis.process.exit()','1/0','9**99999','[1]','1e300'])assert.throws(()=>calculate(input));
});
test('deterministic long and short risk tools',async()=>{
  assert.match(await runTool('/size','10000 1 100 95'),/Units: 20/);
  assert.match(await runTool('/rr','100 105 90'),/2\.0000000R/);
  assert.match(await runTool('/rr','100 95 90'),/Invalid/);
});
test('closed candle indicator calculations',()=>{
  const rows=Array.from({length:21},(_,i)=>[i*3600,1,100,i+1,i+1,1]);
  assert.deepEqual(indicators(rows,3600,72001),{close:20,sma:10.5,rsi:100,end:72000});
  assert.throws(()=>indicators(rows.slice(2),3600,72001));
});
test('memory scopes, skills, and clearing',async()=>{
  const h=harness();await h.message('/remember Arabic');await h.message('Hello');await h.message('Again');
  assert.deepEqual(h.request().messages.slice(0,2),[{role:'user',content:'Hello'},{role:'assistant',content:'AI reply'}]);
  assert.match(h.request().system,/Arabic/);
  await h.message('/memory',2);assert.match(h.sent.at(-1).text,/No saved/);
  await h.message('/memory',1,'group');assert.match(h.sent.at(-1).text,/privately/);
  await h.message('/forget');assert.equal(h.contexts.has('1'),false);
});
test('utility commands work without AI',async()=>{
  const h=harness();await h.message('/calc@JustAI 2+2');assert.equal(h.sent.at(-1).text,'4');assert.equal(h.request(),undefined);
});
test('reminders explicitly deferred until next message and scoped',async()=>{
  const h=harness();await h.message('/followup 1m Review plan');assert.match(h.sent.at(-1).text,/next message/);
  h.setClock(60001);await h.message('/help',2);assert.equal(h.reminders.length,1);
  await h.message('/help');assert.ok(h.sent.some(m=>m.text==='Follow-up: Review plan'));assert.equal(h.reminders.length,0);
});
test('validation, cancellation, and update deduplication',async()=>{
  const h=harness();await h.message('/followup tomorrow x');assert.equal(h.reminders.length,0);
  await h.message('/followup 2h test',1,'private',55);await h.message('/followup 2h test',1,'private',55);assert.equal(h.reminders.length,1);
  await h.message('/cancel 1',2);assert.equal(h.reminders.length,1);
  await h.message('/cancel 1');assert.equal(h.reminders.length,0);
});
test('long messages split without broken emoji',async()=>{
  const sent=[];const text='😀'.repeat(3000);await send({sendMessage:async m=>sent.push(m.text)},1,text);
  assert.equal(sent.join(''),text);assert.ok(sent.every(t=>t.length<=4096));
});
test('AI HTTP errors expose status without key or response body',async()=>{
  await assert.rejects(answer(async()=>({ok:false,status:401}),{provider:'claude',apiKey:'secret',model:'m',systemPrompt:''},[],[],null,'hi'),e=>e instanceof AIError&&e.status===401&&!e.message.includes('secret'));
});
test('OpenAI and Claude request payloads',async()=>{
  for(const provider of ['openai','claude']){
    let request;const text=await answer(async(url,init)=>{request=JSON.parse(init.body);return {ok:true,json:async()=>provider==='claude'?{content:[{type:'text',text:'hello'}]}:{output:[{content:[{type:'output_text',text:'hello'}]}]}};},
      {provider,apiKey:'test',model:'m',systemPrompt:'Base'},[{role:'user',content:'before'},{role:'assistant',content:'answer'}],[],null,'now');
    assert.equal(text,'hello');assert.equal((request.messages||request.input).length,3);
  }
});
test('persistence error preserves AI answer',async()=>{
  const h=harness();h.store.turn=async()=>{throw new Error('DB');};await h.message('Hello');assert.equal(h.sent.at(-1).text,'AI reply');
});
test('concurrent request receives busy response',async()=>{
  const h=harness();await h.store.lock();await h.message('Hello');assert.match(h.sent.at(-1).text,/still processing/);assert.equal(h.request(),undefined);
});
test('market request URL and stale label',async()=>{
  let url;const text=await runTool('/quote','BTC-USD',async u=>{url=u;return {ok:true,json:async()=>({price:'100',time:'2020-01-01T00:00:00Z'})};});
  assert.equal(url,'https://api.exchange.coinbase.com/products/BTC-USD/ticker');assert.match(text,/STALE/);
});
