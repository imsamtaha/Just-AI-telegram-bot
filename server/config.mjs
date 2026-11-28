export function loadConfig(env=process.env){
  const provider=(env.AI_PROVIDER||'openai').trim().toLowerCase();
  if(!['claude','openai'].includes(provider))throw new Error('AI_PROVIDER must be openai or claude');
  const prefix=provider==='claude'?'ANTHROPIC':'OPENAI';
  for(const name of ['TELEGRAM_BOT_TOKEN',`${prefix}_API_KEY`,`${prefix}_MODEL`])
    if(!env[name]?.trim()||/YOUR_|replace_me/.test(env[name]))throw new Error(`Set ${name} in the private VM environment file`);
  let edgeV3StatusUrl;
  if(env.ATLAS_EDGE_V3_STATUS_URL){
    try{const u=new URL(env.ATLAS_EDGE_V3_STATUS_URL);if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash)throw new Error();edgeV3StatusUrl=u.href;}catch{throw new Error('Invalid ATLAS_EDGE_V3_STATUS_URL: use HTTPS without credentials/query/fragment');}
  }
  return {provider,edgeV3StatusUrl,apiKey:env[`${prefix}_API_KEY`].trim(),model:env[`${prefix}_MODEL`].trim(),
    token:env.TELEGRAM_BOT_TOKEN.trim(),automaticReminders:true,
    systemPrompt:env.BOT_SYSTEM_PROMPT||"You are Just AI. Reply in the user's language. Use supplied facts; never invent prices, actions or executions.",
    atlasDashboardUrl:env.ATLAS_DASHBOARD_URL||'https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/'};
}
