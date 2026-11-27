export class TelegramError extends Error {
  constructor(code,retryAfter){super(`Telegram HTTP/API ${code}`);this.code=code;this.retryAfter=retryAfter;}
}
export function telegramClient(token,fetcher=fetch){
  return new Proxy({}, {get:(_,method)=>async(params={})=>{
    let response,data;
    try{
      response=await fetcher(`https://api.telegram.org/bot${token}/${method}`,{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(params),
        signal:AbortSignal.timeout(method==='getUpdates'?45000:20000),
      });data=await response.json();
    }catch{throw new TelegramError(0);}
    if(!response.ok||!data.ok)throw new TelegramError(data.error_code||response.status,data.parameters?.retry_after);
    return data.result;
  }});
}
export async function checkWebhook(api,takeover=false){
  const info=await api.getWebhookInfo();
  if(info.url){
    if(!takeover)throw new Error('A webhook is active. Stop the old service and run the explicit takeover command.');
    await api.deleteWebhook({drop_pending_updates:false});
  }
}
