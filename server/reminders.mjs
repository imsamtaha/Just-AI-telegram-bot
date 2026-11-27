export async function deliverDue({db,store,api,now=Date.now,log=console.warn}){
  const due=await db.all("SELECT id,owner,content FROM justai_reminders WHERE status='pending' AND due<=:n AND retry_after<=:n ORDER BY due LIMIT 50",{':n':now()});
  for(const r of due){
    const token=`reminder:${r.id}:${now()}`;
    if(!await store.lock(r.owner,token,now()))continue;
    try{
      const session=await store.session(r.owner);
      if(!session||session.expires<=now()||!await store.claim(r.owner,r.id))continue;
      try{
        await api.sendMessage({chat_id:Number(r.owner),text:'Follow-up / متابعة:\n'+r.content});
      }catch(e){
        if(e.code===429){
          const delay=Math.min(3600,Math.max(5,Number(e.retryAfter)||60))*1000;
          await db.run("UPDATE justai_reminders SET status='pending',retry_after=:n WHERE id=:id",{':n':now()+delay,':id':r.id});
        }else if(e.code===400||e.code===403){
          await db.run("UPDATE justai_reminders SET status='failed' WHERE id=:id",{':id':r.id});
        }else await store.failed(r.owner,r.id); // Ambiguous send: do not risk an automatic duplicate.
        log('Reminder delivery not confirmed; inspect its status with /followups.');
        continue;
      }
      // If this write fails, status remains sending; startup marks it uncertain.
      await store.complete(r.owner,r.id);
    }finally{await store.unlock(r.owner,token);}
  }
}
