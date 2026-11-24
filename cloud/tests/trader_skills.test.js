import test from 'node:test';
import assert from 'node:assert/strict';
import { traderSkills, traderAliases, traderHelp } from '../tgcloud/lib/trader_skills.js';
import { skills, aliases } from '../tgcloud/lib/skills.js';
import { createHandler } from '../tgcloud/lib/core.js';
import { answer } from '../tgcloud/lib/ai.js';

const names=['copycat','news','budget','pelosi','analyst','screener','risk','broker','tax','alerts','rebalance'];
test('all eleven adapted skills are registered without replacing prior modes',()=>{
  assert.equal(Object.keys(traderSkills).length,11);
  for(const key of names){
    assert.equal(traderAliases[`/trader-${key}`],`trader_${key}`);
    assert.equal(aliases[`/trader_${key}`],`trader_${key}`);
    assert.equal(skills[`trader_${key}`].mode,'analysis-only');
    assert.match(skills[`trader_${key}`].instruction,/No background monitoring or live execution/);
    assert.ok(traderHelp().includes(`/trader_${key}`));
  }
  assert.equal(aliases['/risk'],'risk');assert.equal(aliases['/trading'],'trading');
});
test('both AI providers receive skill limits and Lebanese Arabic style',async()=>{
  for(const provider of ['claude','openai']){
    let payload;
    await answer(async(url,init)=>{payload=JSON.parse(init.body);return {ok:true,json:async()=>provider==='claude'?{content:[{type:'text',text:'draft'}]}:{output_text:'draft'}};},
      {provider,apiKey:'test',model:'m',systemPrompt:'Base'},[],[],traderSkills.trader_broker,'Buy it');
    const system=payload.system||payload.instructions;
    assert.match(system,/no brokerage connector/i);assert.match(system,/natural Lebanese Arabic/);
    assert.match(system,/even after a user says yes/i);
  }
});
test('commands route selected mode and supplied data, including group suffixes',async()=>{
  let payload;const sent=[];
  const handler=createHandler({
    api:{sendMessage:async m=>sent.push(m),sendChatAction:async()=>{}},
    store:{seen:async()=>false,lock:async()=>true,unlock:async()=>{},mark:async()=>{}},
    config:{provider:'openai',apiKey:'test',model:'m',systemPrompt:'Base'},
    fetch:async(url,init)=>{payload=JSON.parse(init.body);return {ok:true,json:async()=>({output_text:'Analysis'})};},
  });
  for(const command of ['/trader-risk@JustAI','/trader_risk@JustAI']){
    await handler({message_id:1,chat:{id:-1,type:'group'},text:command+'\nBudget 1000\nCash 100'});
    assert.match(payload.instructions,/Review supplied proposed orders sequentially/);
    assert.equal(payload.input.at(-1).content,'Budget 1000\nCash 100');
  }
  await handler({message_id:2,chat:{id:-1,type:'group'},text:'/trader'});
  assert.match(sent.at(-1).text,/adapted analysis modes/);
});
