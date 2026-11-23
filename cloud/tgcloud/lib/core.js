import { skills, aliases } from './skills.js';
import { answer, AIError } from './ai.js';
import { runTool, toolCommands, toolHelp } from './tools.js';
export async function send(api, chatId, text, extra={}) {
  let chunk='';
  for(const c of text){if(chunk.length+c.length>4096){await api.sendMessage({chat_id:chatId,text:chunk,...extra});chunk='';}chunk+=c;}
  if(chunk)await api.sendMessage({chat_id:chatId,text:chunk,...extra});
}
const reminderNotice='Cloud reminders are checked when you next message this bot, not at an unattended scheduled time.';
const help='/skills — AI skills\n/plugins — utilities\n/tradingtools — trading tools\n/remember <fact>\n/memory\n/forget\n/followup 30m <text>\n/followups\n/cancel <id>\n/atlas\nPrivate chats retain six turns and 20 notes in cloud storage; context is sent to your AI provider.\n'+reminderNotice;
export function createHandler({api,store,fetch,config,now=Date.now}) {
  return async function(message,ctx={}){
    if(typeof message.text!=='string'||!message.text.trim()||!message.chat?.id)return;
    const chatId=message.chat.id,owner=String(chatId),text=message.text.trim();
    const event=ctx.update?.update_id ?? message.message_id;
    if(event===undefined)throw new Error('Update or message ID required');
    const id=`${owner}:${event}`,token=id+':'+now();
    if(await store.seen(id))return;
    if(!await store.lock(owner,token,now())){
      await send(api,chatId,'I am still processing your previous message. Please resend this request shortly.');return;
    }
    try {
      if(await store.seen(id))return;
      const [,raw,argument='']=text.match(/^(\S+)(?:\s+([\s\S]*))?$/);
      const command=raw.split('@')[0].toLowerCase();
      const privateChat=message.chat.type==='private';
      if(privateChat){
        for(const r of await store.reminders(owner)){
          if(r.status!=='pending'||r.due>now()||!await store.claim(owner,r.id))continue;
          try {await send(api,chatId,'Follow-up: '+r.content);await store.complete(owner,r.id);}
          catch {await store.failed(owner,r.id);}
        }
      }
      let reply;
      if(['/start','/help','/creative'].includes(command))reply=help;
      else if(command==='/skills')reply=Object.entries(skills).map(([k,v])=>`/${k} — ${v.name}`).join('\n');
      else if(['/plugins','/tradingtools'].includes(command))reply=toolHelp;
      else if(command==='/atlas'){
        await send(api,chatId,'Open the ATLAS dashboard. Its own sign-in requirements apply.',{reply_markup:{inline_keyboard:[[{text:'Open ATLAS dashboard',url:'https://atlas-market.imsamtaha.chatgpt.site'}]]}});
        await store.mark(id,owner);return;
      }
      else if(toolCommands.has(command))reply=await runTool(command,argument,fetch,now());
      else if(['/remember','/memory','/forget','/followup','/followups','/cancel'].includes(command)){
        if(!privateChat)reply='Memory and follow-ups are private-chat features.';
        else if(command==='/remember'){
          if(!argument||argument.length>1000)reply='Usage: /remember <fact up to 1000 characters>';
          else{await store.note(owner,argument);reply='Saved. Use /memory to view or /forget to clear.';}
        }else if(command==='/memory')reply='Saved notes:\n'+((await store.context(owner)).notes.join('\n')||'No saved notes.');
        else if(command==='/forget'){await store.forget(owner);reply='Notes and recent conversation cleared. Follow-ups remain; use /cancel <id>.';}
        else if(command==='/cancel')reply=/^\d{1,15}$/.test(argument)&&await store.cancel(owner,Number(argument))?'Follow-up cancelled.':'Follow-up not found. Usage: /cancel <id>';
        else if(command==='/followups')reply=(await store.reminders(owner)).map(r=>`#${r.id} ${new Date(r.due).toISOString()} — ${r.status} — ${r.content}`).join('\n')||'No follow-ups.';
        else{
          const m=argument.match(/^(\d{1,8})([mhd])\s+(.+)$/s),delay=m?Number(m[1])*{m:60000,h:3600000,d:86400000}[m[2]]:0;
          if(delay<60000||delay>365*86400000||m[3].length>2000)reply='Usage: /followup 30m <text>. Delay 1 minute–365 days; text up to 2000 characters.';
          else if((await store.reminders(owner)).length>=50)reply='Limit: 50 follow-ups. Cancel one first.';
          else{const rid=await store.schedule(owner,m[3],now()+delay);reply=`Saved follow-up #${rid}.\n${reminderNotice}`;}
        }
      }else{
        const context=privateChat?await store.context(owner):{history:[],notes:[]};
        try{await api.sendChatAction({chat_id:chatId,action:'typing'});}catch{}
        try{
          reply=await answer(fetch,config,context.history,context.notes,skills[aliases[command]],(aliases[command]?argument||'Ask for essential missing details.':text).slice(0,8000));
          if(privateChat){try{await store.turn(owner,text,reply);}catch{console.warn('Conversation could not be saved');}}
        }catch(error){
          reply=error instanceof AIError?`AI service returned HTTP ${error.status}. ${error.status===401?'Replace the API key using local cloud configuration.':'Check model, account access, credits and service availability.'}`:'AI service is temporarily unreachable. Try again later.';
        }
      }
      await send(api,chatId,reply);
      await store.mark(id,owner);
    }finally{await store.unlock(owner,token);}
  };
}
