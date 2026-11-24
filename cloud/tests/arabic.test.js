import test from 'node:test';
import assert from 'node:assert/strict';
import { arabicAliases, parseCommand, toolArgument, arabicHelp } from '../tgcloud/lib/arabic.js';
import { createHandler } from '../tgcloud/lib/core.js';
import { aliases } from '../tgcloud/lib/skills.js';
import { toolCommands } from '../tgcloud/lib/tools.js';

test('Arabic aliases cover valid core commands, tools and skills',()=>{
  const core=new Set(['/start','/help','/skills','/plugins','/tradingtools','/trader','/remember','/memory','/forget','/followup','/followups','/cancel','/atlas']);
  for(const canonical of Object.values(arabicAliases))assert.ok(core.has(canonical)||toolCommands.has(canonical)||aliases[canonical],canonical);
  assert.equal(Object.values(arabicAliases).filter(c=>c.startsWith('/trader_')).length,11);
  assert.match(arabicHelp('trader'),/مسودة_امر/);
});
test('Arabic normalization, accents, hamza and group suffixes',()=>{
  assert.equal(parseCommand('/إلغاء@JustAI').command,'/cancel');
  assert.equal(parseCommand('/اِحْسَب').command,'/calc');
  assert.equal(parseCommand('/أطلس').command,'/atlas');
  assert.deepEqual(parseCommand('/memory@JustAI'),{command:'/memory',arabic:false});
});
test('numeric input normalization leaves prose and notes untouched',()=>{
  assert.equal(toolArgument('/calc','٢٥٠٠*٠٫٠٢'),'2500*0.02');
  assert.equal(toolArgument('/size','۱۰٬۰۰۰ ۱ ۱۰۰ ۹۵'),'10000 1 100 95');
  assert.equal(toolArgument('/followup','٣٠د تذكّر ١٢٣\nالسطر التاني'),'30m تذكّر ١٢٣\nالسطر التاني');
  assert.equal(toolArgument('/technical','BTC-USD ١س'),'BTC-USD 1h');
  assert.equal(toolArgument('/remember','رقمي ١٢٣'),'رقمي ١٢٣');
});
function app(){
  const sent=[],notes=[],scheduled=[];let payload;
  const handler=createHandler({
    api:{sendMessage:async m=>sent.push(m),sendChatAction:async()=>{}},
    store:{seen:async()=>false,lock:async()=>true,unlock:async()=>{},mark:async()=>{},reminders:async()=>[],
      context:async()=>({notes,history:[]}),note:async(o,n)=>notes.push(n),schedule:async(o,text,due)=>{scheduled.push({text,due});return 1;},turn:async()=>{}},
    fetch:async(url,init)=>{payload=JSON.parse(init.body);return {ok:true,json:async()=>({output_text:'أكيد'})};},
    config:{provider:'openai',model:'m',apiKey:'test',systemPrompt:'Base'},now:()=>0,
  });
  return {sent,notes,scheduled,payload:()=>payload,run:async text=>handler({message_id:1,chat:{id:1,type:'private'},text})};
}
test('Arabic memory, localized help, and tools bypass AI',async()=>{
  const h=app();await h.run('/احفظ رقمي ١٢٣');assert.equal(h.notes[0],'رقمي ١٢٣');
  await h.run('/ذاكرة');assert.match(h.sent.at(-1).text,/الملاحظات المحفوظة/);
  await h.run('/احسب ٢٥٠٠*٠٫٠٢');assert.equal(h.sent.at(-1).text,'50');
  assert.equal(h.payload(),undefined);
  await h.run('/مساعدة');assert.match(h.sent.at(-1).text,/ذكرني/);
});
test('Arabic follow-up duration does not modify reminder content',async()=>{
  const h=app();await h.run('/ذكرني ٣٠د راجع ١٢٣');
  assert.deepEqual(h.scheduled,[{text:'راجع ١٢٣',due:1800000}]);
  assert.match(h.sent.at(-1).text,/ما في إرسال تلقائي/);
});
test('Arabic skill selects matching mode and requests Lebanese replies',async()=>{
  const h=app();await h.run('/ميزانية@JustAI budget 1000');
  assert.match(h.payload().instructions,/Subtract the cash reserve/);
  assert.match(h.payload().instructions,/selected an Arabic command: reply in Lebanese Arabic/);
  assert.equal(h.payload().input.at(-1).content,'budget 1000');
});
