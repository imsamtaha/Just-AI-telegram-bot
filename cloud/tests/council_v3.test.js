import test from 'node:test';
import assert from 'node:assert/strict';
import { summarizeV3,councilV3Status } from '../tgcloud/lib/council_v3.js';
import { parseCommand } from '../tgcloud/lib/arabic.js';
import { editionActions } from '../tgcloud/lib/edition.js';

test('v3 defaults unavailable and never activates trading',async()=>{
 const text=await councilV3Status(()=>{throw new Error('must not fetch');},{},false);
 assert.match(text,/UNAVAILABLE/);assert.match(text,/RESEARCH ONLY/);assert.match(text,/ABSTAIN/);
});
test('untrusted activating backend response is rejected',()=>{
 const text=summarizeV3({stage:'LIVE',decision:'BUY',report_state:'LOCAL_RESEARCH_REPORT',broker_execution_allowed:true,live_activation_allowed:true});
 assert.match(text,/UNAVAILABLE/);assert.ok(!text.includes('BUY'));
});
test('validated projection reports costs as research risk units, not live PnL',async()=>{
 const raw={stage:'RESEARCH_ONLY',decision:'ABSTAIN',broker_execution_allowed:false,live_activation_allowed:false,
  report_state:'LOCAL_RESEARCH_REPORT',sample_count:300,cost_stress:{'1.0':{mean_net_r:.2,expectancy_lower_r:.01}}};
 const text=await councilV3Status(async()=>({ok:true,json:async()=>raw}),{edgeV3StatusUrl:'https://example.test/agent/v3/status'},true);
 assert.match(text,/300/);assert.match(text,/R\/decision/);assert.match(text,/مش اعتماد أداء/);
});
test('Arabic commands and one-tap Council action are registered',()=>{
 assert.equal(parseCommand('/مجلس_٣').command,'/council_v3');assert.equal(editionActions.ed_council,'/council_v3');
});
