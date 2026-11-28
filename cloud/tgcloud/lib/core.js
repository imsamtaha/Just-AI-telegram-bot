import { councilV3Status } from './council_v3.js';
import { editionPanel, marketSnapshot, BRIEF_INSTRUCTION, briefKeyboard } from './edition.js';
import { requirePrivateLogin } from './access.js';
import { parseCommand, toolArgument, arabicHelp, arabicReminderNotice } from './arabic.js';
import { skills, aliases } from './skills.js';
import { traderHelp } from './trader_skills.js';
import { answer, AIError } from './ai.js';
import { runTool, toolCommands, toolHelp } from './tools.js';
export async function send(api, chatId, text, extra={}) {
  let chunk='';
  for(const c of text){if(chunk.length+c.length>4096){await api.sendMessage({chat_id:chatId,text:chunk});chunk='';}chunk+=c;}
  if(chunk)await api.sendMessage({chat_id:chatId,text:chunk,...extra});
}
const reminderNotice='Cloud reminders are checked when you next message this bot, not at an unattended scheduled time.';
const help='/council_v3 — v3 research status (no live activation)\n/home — ATLAS Special Edition\n/desk BTC-USD 1h — sourced market snapshot\n/brief BTC-USD 1h — AI explanation of snapshot\n/workspace — private workspace\n/studio — creative skills\n/login — log in privately\n/logout — end bot session\n/privacy — data privacy\n/trader — imported trader skill pack\n/skills — AI skills\n/plugins — utilities\n/tradingtools — trading tools\n/remember <fact>\n/memory\n/forget\n/followup 30m <text>\n/followups\n/cancel <id>\n/atlas\nPrivate chats retain six turns and 20 notes in cloud storage; context is sent to your AI provider.\n'+reminderNotice;
export function createHandler({api,store,fetch,config,now=Date.now}) {
  const reminderNoticeText=config.automaticReminders?'Automatic reminders are checked every five seconds while the VM service runs; logged-out/expired sessions pause delivery.':reminderNotice;
  const reminderNoticeArabic=config.automaticReminders?'المتابعة رح تنبعت تلقائياً وقت يحين موعدها والخدمة شغّالة. تسجيل الخروج أو انتهاء الجلسة بيوقّف الإرسال لحدّ ما تسجّل دخول من جديد.':arabicReminderNotice;
  const localizedHelp=(group='help')=>arabicHelp(group,!!config.automaticReminders);
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
      const [,raw,originalArgument='']=text.match(/^(\S+)(?:\s+([\s\S]*))?$/);
      const {command,arabic}=parseCommand(raw);
      const argument=toolArgument(command,originalArgument);
      const local=(en,ar)=>arabic?ar:en;
      if(!await requirePrivateLogin({message,command,arabic,api,store,now:now()})){
        await store.mark(id,owner);return;
      }
      const privateChat=message.chat.type==='private';
      if(privateChat&&!config.automaticReminders){
        for(const r of await store.reminders(owner)){
          if(r.status!=='pending'||r.due>now()||!await store.claim(owner,r.id))continue;
          try {await send(api,chatId,local('Follow-up: ','متابعة: ')+r.content);await store.complete(owner,r.id);}
          catch {await store.failed(owner,r.id);}
        }
      }
      let reply,replyMarkup;
      if(['/start','/home','/edition','/studio','/workspace'].includes(command)){
        const kind=command==='/studio'?'studio':command==='/workspace'?'workspace':'home';
        const counts=kind==='workspace'?{notes:(await store.context(owner)).notes.length,
          followups:(await store.reminders(owner)).filter(r=>r.status==='pending').length}:{};
        const panel=editionPanel(kind,arabic,{...counts,automaticReminders:!!config.automaticReminders,name:typeof message.from.first_name==='string'?message.from.first_name.slice(0,40):''});
        reply=panel.text;replyMarkup=panel.reply_markup;
      }
      else if(['/council_v3','/v3'].includes(command)){
        reply=await councilV3Status(fetch,config,arabic);
      }
      else if(['/desk','/brief'].includes(command)){
        try{await api.sendChatAction({chat_id:chatId,action:'typing'});}catch{}
        const snapshot=await marketSnapshot(argument,fetch,now(),arabic);
        reply=snapshot.text;replyMarkup=briefKeyboard(arabic);
        if(command==='/brief'&&snapshot.ok){
          const context=await store.context(owner);
          try{await api.sendChatAction({chat_id:chatId,action:'typing'});}catch{}
          try{
            const briefing=await answer(fetch,arabic?{...config,systemPrompt:config.systemPrompt+'\nReply in Lebanese Arabic.'}:config,
              [],context.notes,BRIEF_INSTRUCTION,snapshot.text);
            reply=snapshot.text+'\n\n'+briefing;
            try{await store.turn(owner,text,reply);}catch{console.warn('Briefing could not be saved');}
          }catch{
            reply+='\n\n'+(arabic?'تفسير AI مش متاح هلّق. بيانات المصدر فوق بعدها معروضة.':'AI interpretation is unavailable. The sourced snapshot is shown above.');
          }
        }
      }
      else if(aliases[command]&&!argument){
        reply=arabic?'اختَرت '+skills[aliases[command]].name+'. ابعت '+raw+' ومعه طلبك أو النص والبيانات اللي بدّك نحلّلها. رح نسألك بس عن التفاصيل الضرورية.':
          'Selected: '+skills[aliases[command]].name+'. Send '+raw+' followed by your request or source text/data. I will ask only for essential missing details.';
      }
      else if(['/help','/creative'].includes(command))reply=arabic?localizedHelp():help.replace(reminderNotice,reminderNoticeText)+'\n/مساعدة — الأوامر بالعربي';
      else if(command==='/trader')reply=arabic?localizedHelp('trader'):traderHelp();
      else if(command==='/skills')reply=arabic?localizedHelp('skills'):Object.entries(skills).map(([k,v])=>`/${k} — ${v.name}`).join('\n');
      else if(['/plugins','/tradingtools'].includes(command))reply=arabic?localizedHelp('tools'):toolHelp;
      else if(command==='/atlas'){
        await send(api,chatId,local('Open ATLAS Tiger Shield. Its own sign-in requirements apply.','فيك تفتح لوحة ATLAS Tiger Shield من هالزر. تسجيل الدخول والصلاحيات تبعها بيضلّوا مطلوبين.'),{reply_markup:{inline_keyboard:[[{text:local('Open Tiger Shield','افتح درع النمر'),url:config.atlasDashboardUrl||'https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/'}]]}});
        await store.mark(id,owner);return;
      }
      else if(toolCommands.has(command))reply=await runTool(command,argument,fetch,now());
      else if(['/remember','/memory','/forget','/followup','/followups','/cancel'].includes(command)){
        if(!privateChat)reply=local('Memory and follow-ups are private-chat features.','الذاكرة والمتابعات متاحين بالمحادثة الخاصة بس.');
        else if(command==='/remember'){
          if(!argument||argument.length>1000)reply=local('Usage: /remember <fact up to 1000 characters>','اكتب /احفظ وبعدها المعلومة، لحد ١٠٠٠ حرف.');
          else{await store.note(owner,argument);reply=local('Saved. Use /memory to view or /forget to clear.','حفظتها. فيك تشوفها بـ /ذاكرة أو تمسح الذاكرة بـ /انسى.');}
        }else if(command==='/memory')reply=local('Saved notes:\n','الملاحظات المحفوظة:\n')+((await store.context(owner)).notes.join('\n')||local('No saved notes.','بعد ما في ملاحظات محفوظة.'));
        else if(command==='/forget'){await store.forget(owner);reply=local('Notes and recent conversation cleared. Follow-ups remain; use /cancel <id>.','مسحت الملاحظات وسياق الحديث. المتابعات بعدها موجودة؛ للإلغاء استعمل /الغاء ورقم المتابعة.');}
        else if(command==='/cancel')reply=/^\d{1,15}$/.test(argument)&&await store.cancel(owner,Number(argument))?local('Follow-up cancelled.','ألغيت المتابعة.'):local('Follow-up not found. Usage: /cancel <id>','ما لقيت المتابعة. استعمل /الغاء ورقمها.');
        else if(command==='/followups')reply=(await store.reminders(owner)).map(r=>`#${r.id} ${new Date(r.due).toISOString()} — ${r.status} — ${r.content}`).join('\n')||local('No follow-ups.','ما في متابعات.');
        else{
          const m=argument.match(/^(\d{1,8})([mhd])\s+(.+)$/s),delay=m?Number(m[1])*{m:60000,h:3600000,d:86400000}[m[2]]:0;
          if(delay<60000||delay>365*86400000||m[3].length>2000)reply=local('Usage: /followup 30m <text>. Delay 1 minute–365 days; text up to 2000 characters.','مثال: /ذكرني ٣٠د راجع الخطة. المدّة من دقيقة لـ ٣٦٥ يوم، والنص لحد ٢٠٠٠ حرف.');
          else if((await store.reminders(owner)).length>=50)reply=local('Limit: 50 follow-ups. Cancel one first.','الحدّ ٥٠ متابعة. ألغي وحدة بالأوّل.');
          else{const rid=await store.schedule(owner,m[3],now()+delay);reply=arabic?`حفظت المتابعة #${rid}.\n${reminderNoticeArabic}`:`Saved follow-up #${rid}.\n${reminderNoticeText}`;}
        }
      }else{
        const context=privateChat?await store.context(owner):{history:[],notes:[]};
        try{await api.sendChatAction({chat_id:chatId,action:'typing'});}catch{}
        try{
          reply=await answer(fetch,arabic?{...config,systemPrompt:config.systemPrompt+'\nThe user selected an Arabic command: reply in Lebanese Arabic, unless a different translation target or register is explicitly requested.'}:config,context.history,context.notes,skills[aliases[command]],(aliases[command]?argument||'Ask for essential missing details.':text).slice(0,8000));
          if(privateChat){try{await store.turn(owner,text,reply);}catch{console.warn('Conversation could not be saved');}}
        }catch(error){
          reply=error instanceof AIError?`AI service returned HTTP ${error.status}. ${error.status===401?'Replace the API key using local cloud configuration.':'Check model, account access, credits and service availability.'}`:'AI service is temporarily unreachable. Try again later.';
        }
      }
      await send(api,chatId,reply,replyMarkup?{reply_markup:replyMarkup}:{});
      await store.mark(id,owner);
    }finally{await store.unlock(owner,token);}
  };
}
