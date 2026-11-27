import { setTimeout as sleep } from 'node:timers/promises';
import { createHandler } from '../cloud/tgcloud/lib/core.js';
import { createCallbackHandler } from '../cloud/tgcloud/lib/access.js';
import { openStorage } from './storage.mjs';
import { telegramClient, checkWebhook } from './telegram.mjs';
import { deliverDue } from './reminders.mjs';
import { loadConfig } from './config.mjs';

process.umask(0o077);
const config=loadConfig(),api=telegramClient(config.token);
if(process.argv.includes('--takeover')){
  await checkWebhook(api,true);
  console.log('Webhook disabled without dropping pending updates. Start exactly one VM service now.');
}else{
  await checkWebhook(api); // Never silently disconnect the currently hosted bot.
  const storage=openStorage(process.env.BOT_MEMORY_PATH||'/data/bot.sqlite3');
  const {db,store}=storage;
  await db.run("UPDATE justai_reminders SET status='uncertain' WHERE status='sending'");
  // A single VM/container only. Do not horizontally scale a polling bot.
  const net=(url,options={})=>fetch(url,{...options,signal:AbortSignal.timeout(60000)});
  const handle=createHandler({api,fetch:net,store,config});
  const callback=createCallbackHandler({api,handleMessage:handle});
  const shutdown=new AbortController();let running=true;
  for(const event of ['SIGINT','SIGTERM'])process.on(event,()=>{running=false;shutdown.abort();});
  const wait=async ms=>{try{await sleep(ms,undefined,{signal:shutdown.signal});}catch{}};
  const worker=(async()=>{
    while(running){try{await deliverDue({db,store,api});}catch{console.warn('Reminder worker will retry after a storage/service error.');}await wait(5000);}
  })();
  try{
    const state=await db.get("SELECT value FROM justai_runtime WHERE key='offset'");
    let offset=state?Number(state.value):undefined;
    console.log('JUST AI Special Edition is polling; automatic reminder worker active.');
    while(running){
      try{
        const updates=await api.getUpdates({timeout:30,allowed_updates:['message','callback_query'],...(offset===undefined?{}:{offset})});
        const chats=new Map();
        for(const update of updates){
          const owner=update.message?.chat?.id||update.callback_query?.message?.chat?.id||0;
          if(!chats.has(owner))chats.set(owner,[]);chats.get(owner).push(update);
        }
        const groups=[...chats.values()];
        // Eight chats concurrently, with sequential handling within a chat.
        for(let i=0;i<groups.length;i+=8)await Promise.all(groups.slice(i,i+8).map(async group=>{
          for(const u of group){
            try{if(u.message)await handle(u.message,{update:u});else if(u.callback_query)await callback(u.callback_query,{update:u});}
            catch{console.warn('An update could not be completed.');}
          }
        }));
        if(updates.length){
          offset=Math.max(...updates.map(u=>u.update_id))+1;
          await db.run("INSERT INTO justai_runtime(key,value) VALUES('offset',:v) ON CONFLICT(key) DO UPDATE SET value=:v",{':v':String(offset)});
        }
      }catch(e){
        if(e.code===401||e.code===409){console.error(`Telegram ${e.code}: check token or duplicate bot/webhook. Polling stopped.`);running=false;shutdown.abort();process.exitCode=1;break;}
        console.warn('Telegram polling interrupted; retrying.');await wait(5000);
      }
    }
  }finally{running=false;shutdown.abort();await worker;storage.close();}
}
