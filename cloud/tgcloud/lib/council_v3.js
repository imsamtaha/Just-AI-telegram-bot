// Read-only research status. Never turns an architecture description into live signals.
const allowedStates=new Set(['UNAVAILABLE','STALE','LOCAL_RESEARCH_REPORT']);
export function summarizeV3(raw,arabic=false){
  const valid=raw&&raw.stage==='RESEARCH_ONLY'&&raw.decision==='ABSTAIN'&&raw.broker_execution_allowed===false&&raw.live_activation_allowed===false&&allowedStates.has(raw.report_state);
  const state=valid?raw.report_state:'UNAVAILABLE';
  const title='ATLAS COUNCIL v3 · EDGE-FIRST';
  const lines=arabic?[
    title,'الوضع: بحث فقط · القرار الافتراضي: امتناع عن التداول',
    'حالة دليل التقييم: '+state,
    'ما في تنفيذ أوامر، تغيير أوزان المجلس، أو تفعيل تداول حقيقي بهالأمر.',
    'التصميم لحاله ما بيثبت أفضلية. لازم نتائج خارج العيّنة بعد السبريد والانزلاق والرسوم، ومقارنة بالخطوط المرجعية.',
    'مراجعتا STC-04 وSTC-09 وتشغيل العامل بعدن بحاجة لإثبات مستقل.',
  ]:[
    title,'Mode: RESEARCH ONLY · Default decision: ABSTAIN',
    'Evaluation evidence: '+state,
    'This command cannot execute orders, change Council weights, or activate live trading.',
    'The design alone is not evidence of edge. Out-of-sample results after spread, slippage and fees must beat aligned baselines.',
    'STC-04/STC-09 reviews and a running worker still require independent verification.',
  ];
  if(valid&&Number.isSafeInteger(raw.sample_count)&&raw.sample_count>0){
    lines.push((arabic?'قرارات تقييم: ':'Evaluation decisions: ')+raw.sample_count);
    for(const scale of ['1.0','1.5','2.0']){
      const c=raw.cost_stress?.[scale];
      if(c&&Number.isFinite(c.mean_net_r)&&Number.isFinite(c.expectancy_lower_r))
        lines.push(`${scale}× costs: mean ${c.mean_net_r.toFixed(4)} R/decision; lower ${c.expectancy_lower_r.toFixed(4)} R/decision`);
    }
    lines.push(arabic?'دليل بحث محلي، مش اعتماد أداء أو أرباح حيّة.':'Local research evidence, not independently attested live performance.');
  }
  return lines.join('\n');
}
export async function councilV3Status(fetch,config,arabic){
  if(!config.edgeV3StatusUrl)return summarizeV3(null,arabic)+'\n'+(arabic?'رابط خدمة تقييم v3 مش مضبوط بهالنسخة بعد.':'No v3 status service URL is configured in this deployment.');
  try{
    const r=await fetch(config.edgeV3StatusUrl,{headers:{Accept:'application/json'}});
    if(!r.ok)return summarizeV3(null,arabic);
    return summarizeV3(await r.json(),arabic);
  }catch{return summarizeV3(null,arabic);}
}
