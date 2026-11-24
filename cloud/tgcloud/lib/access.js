// Trust identity only on Telegram updates delivered by tgcloud, never from command arguments.
export const SESSION_MS = 30 * 86400000;
export const BOT_URL = 'https://t.me/JustAI_chatbot';
export const privacyText = {
  en:'This is a private one-to-one bot chat, not end-to-end encrypted chat. Memory is separated by your Telegram account. The bot operator can access cloud storage, and your messages/context are sent to the configured AI provider. Avoid sending passwords or API keys. /forget clears saved notes and recent context; cancel reminders separately. /logout ends this bot session, not your Telegram session. This login does not link Google/ATLAS accounts, verify a paid subscription, or connect a broker.',
  ar:'هيدي محادثة خاصة بينك وبين البوت، مش محادثة مشفّرة من الطرف للطرف. الذاكرة منفصلة حسب حسابك على تلغرام. مشغّل البوت فيه يوصل للتخزين بالسحابة، ورسائلك وسياق الحديث بينبعتوا لمزوّد الذكاء الاصطناعي. ما تبعت كلمات سر أو مفاتيح API. /انسى بيمسح الملاحظات وسياق الحديث؛ المتابعات إلغيها لحالها. /خروج بينهي جلسة البوت، مش جلسة تلغرام. هالدخول ما بيربط حساب Google أو ATLAS، وما بيتحقّق من اشتراك مدفوع أو بيربط وسيط.',
};
export async function requirePrivateLogin({message,command,arabic,api,store,now}) {
  const chatId=message.chat.id;
  const say=(en,ar,reply_markup)=>api.sendMessage({chat_id:chatId,text:arabic?ar:en,...(reply_markup?{reply_markup}:{})});
  if(message.chat.type!=='private'){
    await say('Chat with Just AI privately to log in. No customer conversations or memory are available in groups.',
      'افتح المحادثة الخاصة مع Just AI لتسجّل دخولك. ما في محادثات أو ذاكرة زباين بالمجموعات.',
      {inline_keyboard:[[{text:arabic?'افتح محادثة خاصة':'Open private chat',url:BOT_URL+'?start=login'}]]});
    return false;
  }
  const userId=message.from?.id;
  if(!Number.isSafeInteger(userId)||userId<=0||userId!==chatId||message.from.is_bot){
    await say('Your Telegram identity could not be verified. Open the bot directly and try again.',
      'ما قدرنا نتأكّد من هويتك على تلغرام. افتح البوت مباشرة وجرّب من جديد.');
    return false;
  }
  const owner=String(userId);
  if(command==='/privacy'){
    await api.sendMessage({chat_id:chatId,text:privacyText[arabic?'ar':'en']});return false;
  }
  if(command==='/logout'){
    await store.logout(owner);
    await say('Logged out of this bot. Saved memory and reminders remain; log in and use /forget or /cancel to manage them.',
      'طلعت من جلسة البوت. الذاكرة والمتابعات بعدها محفوظة؛ سجّل دخول واستعمل /انسى أو /الغاء لتديرها.',
      {inline_keyboard:[[{text:arabic?'سجّل دخول بتلغرام':'Log in with Telegram',callback_data:arabic?'justai_login_ar':'justai_login'}]]});
    return false;
  }
  if(command==='/login'){
    await store.login(owner,now,now+SESSION_MS);
    await say('You are logged in privately with your Telegram account for 30 days. Send a message to chat, or use /skills and /trader. /logout ends this bot session.\n\n'+privacyText.en,
      'سجّلت دخولك بالمحادثة الخاصة بحسابك على تلغرام لمدّة ٣٠ يوم. ابعت رسالة لنحكي، أو استعمل /مهارات و /متداول. /خروج بينهي جلسة البوت.\n\n'+privacyText.ar);
    return false;
  }
  const session=await store.session(owner);
  if(session&&session.expires>now)return true;
  await say('Welcome to Just AI. Log in with your Telegram identity to start a private conversation. No password or phone number is requested.\n\n'+privacyText.en,
    'أهلا فيك بـ Just AI. سجّل دخول بهويتك على تلغرام لنبلّش محادثة خاصة. ما منطلب كلمة سر أو رقم تلفون.\n\n'+privacyText.ar,
    {inline_keyboard:[[{text:arabic?'سجّل دخول بتلغرام':'Log in with Telegram',callback_data:arabic?'justai_login_ar':'justai_login'}],
      [{text:arabic?'الخصوصية':'Privacy',callback_data:arabic?'justai_privacy_ar':'justai_privacy'}]]});
  return false;
}
export function createCallbackHandler({api,handleMessage}) {
  return async function(query,ctx={}){
    const commands={justai_login:'/login',justai_login_ar:'/دخول',justai_privacy:'/privacy',justai_privacy_ar:'/خصوصية'};
    const text=commands[query.data];
    if(!query.id)return;
    if(!text){await api.answerCallbackQuery({callback_query_id:query.id});return;}
    if(!ctx.update?.update_id||query.message?.chat?.type!=='private'||query.from?.id!==query.message.chat.id||query.from?.is_bot){
      await api.answerCallbackQuery({callback_query_id:query.id,text:'Open the bot privately and use /login.',show_alert:true});return;
    }
    await api.answerCallbackQuery({callback_query_id:query.id});
    await handleMessage({message_id:query.message.message_id,chat:query.message.chat,from:query.from,text},ctx);
  };
}
