import { runTool } from './tools.js';
export const EDITION_NAME='JUST AI · ATLAS SPECIAL EDITION';
const destinations={
  council:['/council_v3','/مجلس_٣'],home:['/home','/الرئيسية'],desk:['/desk BTC-USD 1h','/مكتب_السوق BTC-USD 1h'],
  brief:['/brief BTC-USD 1h','/موجز BTC-USD 1h'],trader:['/trader','/متداول'],
  studio:['/studio','/استوديو'],workspace:['/workspace','/مساحتي'],atlas:['/atlas','/اطلس'],
  memory:['/memory','/ذاكرة'],followups:['/followups','/متابعات'],
  help:['/help','/مساعدة'],privacy:['/privacy','/خصوصية'],logout:['/logout','/خروج'],
  writer:['/writer','/كاتب'],designer:['/designer','/مصمم'],translate:['/translate','/ترجم'],plan:['/plan','/خطة'],
};
export const editionActions=Object.freeze(Object.fromEntries(Object.entries(destinations).flatMap(([name,[en,ar]])=>[
  [`ed_${name}`,en],[`ed_${name}_ar`,ar],
])));
function button(name,label,arabic){return {text:label,callback_data:`ed_${name}${arabic?'_ar':''}`};}
export function editionPanel(kind,arabic=false,{name='',notes=0,followups=0,automaticReminders=false}={}){
  const b=(key,en,ar)=>button(key,arabic?ar:en,arabic);
  const languageRow=[button('home','English',false),button('home','العربية',true)];
  let text,rows;
  if(kind==='studio'){
    text=arabic?'استوديو JUST AI\nاختار مهارة، وبعدها ابعت طلبك معها.':'JUST AI STUDIO\nPick a skill, then send it with your brief.';
    rows=[[b('writer','Writing desk','كتابة وتحرير'),b('designer','Design studio','استوديو التصميم')],
      [b('translate','Translation','ترجمة'),b('plan','Plan a project','خطّط مشروع')],
      [b('home','Back to home','الرئيسية')]];
  }else if(kind==='workspace'){
    text=arabic?`مساحتك الخاصة\nالملاحظات المحفوظة: ${notes}\nالمتابعات المعلّقة: ${followups}\nالمتابعات بتنراجع وقت تبعت رسالة جديدة، مش وإنت غايب.`:
      `YOUR PRIVATE WORKSPACE\nSaved notes: ${notes}\nPending follow-ups: ${followups}\nFollow-ups are checked when you next message, not while idle.`;
    if(automaticReminders)text=arabic?`مساحتك الخاصة\nالملاحظات المحفوظة: ${notes}\nالمتابعات المعلّقة: ${followups}\nالتذكير تلقائي والخدمة شغّالة؛ تسجيل الخروج بيوقّفه مؤقتاً.`:`YOUR PRIVATE WORKSPACE\nSaved notes: ${notes}\nPending follow-ups: ${followups}\nAutomatic reminders active while the service runs; logout pauses delivery.`;
    rows=[[b('memory','My notes','ملاحظاتي'),b('followups','My follow-ups','متابعاتي')],
      [b('privacy','Privacy','الخصوصية'),b('logout','Log out','خروج')],[b('home','Back to home','الرئيسية')]];
  }else{
    const greeting=name?(arabic?`أهلا ${name}!`:`Welcome, ${name}!`):(arabic?'أهلا فيك!':'Welcome!');
    text=`${EDITION_NAME}\n\n${greeting}\n`+(arabic?
      'مساحة خاصة للتفكير، الإبداع وتحليل السوق. اختار شو بدّك تعمل هلّق.\nمكتب السوق بيعرض بيانات كريبتو من Coinbase. الموجز الذكي بيستعمل مزوّد AI تبع البوت؛ ما في تنفيذ صفقات.':
      'Your private space to think, create, and understand markets. Choose your next step.\nMarket desk uses Coinbase crypto data. AI briefing uses the bot’s configured AI provider; no orders are executed.');
    rows=[[b('desk','Market desk · BTC','مكتب السوق · BTC'),b('brief','AI briefing · BTC','موجز ذكي · BTC')],
      [b('council','Council v3 · Research','مجلس v3 · بحث')],
      [b('trader','Trading skills','مهارات التداول'),b('studio','Creative studio','استوديو الإبداع')],
      [b('workspace','My workspace','مساحتي'),b('atlas','Tiger Shield','درع النمر')],languageRow,
      [b('help','All commands','كل الأوامر'),b('logout','Log out','خروج')]];
  }
  return {text,reply_markup:{inline_keyboard:rows}};
}
export function briefKeyboard(arabic){return {inline_keyboard:[
  [button('home',arabic?'الرئيسية':'Home',arabic)],
]};}
export async function marketSnapshot(argument,fetch,now,arabic){
  const fields=(argument||'BTC-USD 1h').trim().split(/\s+/);
  if(fields.length===1)fields.push('1h');
  const [rawSymbol,interval]=fields,symbol=rawSymbol.toUpperCase();
  if(fields.length!==2||!/^[A-Z0-9]{2,12}-[A-Z0-9]{2,12}$/.test(symbol)||!['5m','15m','1h','1d'].includes(interval))
    return {ok:false,text:arabic?'مثال: /مكتب_السوق BTC-USD 1h أو /موجز ETH-USD 15m':'Usage: /desk BTC-USD 1h or /brief ETH-USD 15m'};
  const [quote,technical]=await Promise.all([
    runTool('/quote',symbol,fetch,now),runTool('/technical',`${symbol} ${interval}`,fetch,now),
  ]);
  // Only complete, valid tool output may become context for an AI briefing.
  if(!quote.startsWith(symbol+':')||!technical.startsWith(symbol+'\n'))return {ok:false,text:arabic?
    'ما قدرنا نجيب لقطة سوق كاملة. جرّب بعد شوي أو استعمل /سعر و /مؤشرات. ما رح نختلق بيانات أو نطلب تحليل AI ناقص.':
    'A complete market snapshot is unavailable. Try again later or use /quote and /technical. No AI analysis was requested.'};
  return {ok:true,symbol,interval,text:`${EDITION_NAME}\n${arabic?'لقطة السوق':'MARKET SNAPSHOT'} · ${symbol} · ${interval}\n\n${quote}\n\n${technical}\n\n`+
    (arabic?'قبل أي قرار: تأكّد من توقيت البيانات، حدّد الإبطال وحجم المخاطرة، واحسب الرسوم والانزلاق. هيدي لقطة معلومات، مش أمر تداول.':
      'Decision check: verify data timestamps, define invalidation and risk budget, and account for costs/slippage. This is information, not an order.')};
}
export const BRIEF_INSTRUCTION={instruction:
  'Explain only the supplied Coinbase snapshot in a concise market briefing. Use headings: Observed facts, Interpretation, Missing inputs, Next step. '+
  'Distinguish price from last-closed-candle metrics and their timestamps. RSI is simple-average, not Wilder. '+
  'If any supplied data is marked stale, explicitly say so and do not derive an actionable setup. '+
  'Never invent news, volume, support/resistance levels, price targets, buy/sell signals or guarantees. '+
  'Use relevant saved preferences without treating them as market data. Ask for risk inputs instead of inventing position size. No trade execution.'};
