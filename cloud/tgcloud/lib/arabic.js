// Arabic commands are typed text aliases; Telegram's command menu requires Latin names.
const commands = [
  ['ابدأ','start','بلّش وشوف المساعدة'],['مساعدة','help','كل الأوامر الأساسية'],
  ['مهارات','skills','مهارات الذكاء الاصطناعي'],['ادوات','plugins','الأدوات والحسابات'],
  ['تداول','tradingtools','أدوات التداول'],['متداول','trader','حزمة مهارات المتداول'],
  ['احفظ','remember','احفظ معلومة: /احفظ بفضّل الجواب المختصر'],
  ['ذاكرة','memory','شوف ملاحظاتك'],['انسى','forget','امسح الملاحظات وسياق الحديث'],
  ['ذكرني','followup','متابعة: /ذكرني ٣٠د راجع الخطة'],
  ['متابعات','followups','شوف المتابعات'],['الغاء','cancel','إلغاء متابعة: /الغاء ١'],
  ['اطلس','atlas','افتح لوحة ATLAS'],
  ['احسب','calc','حساب: /احسب ٢٥٠٠*٠٫٠٢'],['وقت','time','الوقت: /وقت Asia/Beirut'],
  ['طقس','weather','الطقس: /طقس بيروت'],['سعر','quote','سعر كريبتو: /سعر BTC-USD'],
  ['مؤشرات','technical','مؤشرات: /مؤشرات BTC-USD 1h'],
  ['حجم_الصفقة','size','حجم الصفقة: /حجم_الصفقة ١٠٠٠٠ ١ ١٠٠ ٩٥'],
  ['عائد_مخاطرة','rr','العائد للمخاطرة: /عائد_مخاطرة ١٠٠ ٩٥ ١١٠'],
  ['مصمم','designer','توجيه تصميم'],['صانع_محتوى','creator','أفكار محتوى'],
  ['غرافيك','graphic','تصميم غرافيك'],['تعديل_صور','photo','تعليمات تعديل صور'],
  ['كاتب','writer','كتابة وتحرير'],['ترجم','translate','ترجمة للّغة اللي بتطلبها'],
  ['برمجة','coder','مساعدة بالبرمجة'],['خطة','plan','تنظيم خطة'],
  ['علمني','tutor','شرح وتعليم'],['لخص','summarize','تلخيص نص'],
  ['تحليل_تداول','trading','تحليل بيانات تداول بتزوّدنا فيها'],['مخاطر','risk','مراجعة مخاطر'],
  ['محلل_فني','technicalanalyst','تحليل فني للبيانات المرفقة بالنص'],
  ['خطة_تداول','tradeplan','خطة تداول مشروطة'],['يومية','journal','مراجعة يومية التداول'],
  ['اختبار_استراتيجية','backtest','تصميم اختبار تاريخي، مش تشغيله'],
  ['نسخ_محفظة','trader_copycat','تحليل حيازات 13F اللي بتزوّدنا فيها'],
  ['اخبار_المحفظة','trader_news','مراجعة أخبار بتلصق نصّها'],
  ['ميزانية','trader_budget','توزيع ميزانية حسب حدودك'],
  ['افصاحات','trader_pelosi','مراجعة إفصاحات أعضاء الكونغرس'],
  ['ارباح','trader_analyst','تحليل بيانات الأرباح'],
  ['فلترة','trader_screener','فلترة شركات حسب شروطك'],
  ['فحص_المخاطر','trader_risk','مراجعة محادثة، مش فحص آلي مُلزم'],
  ['مسودة_امر','trader_broker','مسودة أمر افتراضي، بلا تنفيذ'],
  ['ضرائب','trader_tax','سيناريوهات ضريبية حسب البيانات والبلد'],
  ['تنبيهات','trader_alerts','تصميم شروط تنبيه، بلا مراقبة تلقائية'],
  ['اعادة_توازن','trader_rebalance','مراجعة انحراف المحفظة'],
];
export function normalizeCommand(text){
  return text.split('@')[0].normalize('NFC').toLowerCase().replace(/[\u064b-\u065f\u0670\u0640]/g,'').replace(/[أإآ]/g,'ا');
}
export const arabicAliases = Object.fromEntries(commands.map(([ar,en])=>[normalizeCommand('/'+ar),'/'+en]));
Object.assign(arabicAliases,{'/تذكر':'/remember','/تذكير':'/followup','/الذاكرة':'/memory','/اوامر':'/help'});
export function parseCommand(raw){
  const normalized=normalizeCommand(raw);
  return {command:arabicAliases[normalized]||normalized,arabic:/[\u0600-\u06ff]/.test(raw.split('@')[0])};
}
export function numbers(text){
  return text.replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-0x660)).replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-0x6f0)).replace(/٫/g,'.').replace(/٬/g,'');
}
export function toolArgument(command,text){
  if(['/calc','/size','/rr','/cancel'].includes(command))return numbers(text);
  if(command==='/technical')return text.replace(/(\S+)\s+(\S+)$/,(_,pair,interval)=>pair+' '+numbers(interval).replace(/د$/,'m').replace(/س$/,'h').replace(/ي$/,'d'));
  if(command==='/followup')return text.replace(/^(\S+)(?=\s)/,delay=>numbers(delay).replace(/د$/,'m').replace(/س$/,'h').replace(/ي$/,'d'));
  return text;
}
export function arabicHelp(group='help'){
  let subset=commands;
  if(group==='trader')subset=commands.filter(([,en])=>en.startsWith('trader_'));
  else if(group==='skills')subset=commands.slice(20);
  else if(group==='tools')subset=commands.slice(13,20);
  else subset=commands.slice(0,20);
  return 'فيك تكتب هالأوامر بالعربي أو تستعمل مقابلها بالإنكليزي:\n'+
    subset.map(([ar,en,desc])=>`/${ar} — /${en}\n${desc}`).join('\n')+
    '\n\nبالتذكير: د=دقيقة، س=ساعة، ي=يوم. المتابعات بتنراجع بس وقت تبعت رسالة جديدة، مش تلقائياً وإنت غايب.'+
    '\nالذاكرة للخاص وبتنحفظ بالسحابة؛ سياق الحديث بينبعت لمزوّد الذكاء الاصطناعي. مهارات المتداول بتحلّل النص اللي بتعطيها ياه، بلا جلب أخبار/ملفات أو تنفيذ صفقات.';
}
export const arabicReminderNotice='المتابعة محفوظة، بس رح نتفقّدها وقت تبعت رسالة جديدة للبوت؛ ما في إرسال تلقائي بموعد محدّد وإنت غايب.';
