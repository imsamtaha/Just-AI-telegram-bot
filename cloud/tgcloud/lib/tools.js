export const toolHelp = '/calc (2500*0.02)/5\n/time Asia/Beirut\n/weather Beirut\n/quote BTC-USD\n/technical BTC-USD 1h\n/size 10000 1 100 95\n/rr 100 95 110';
export const toolCommands = new Set(['/calc','/time','/weather','/quote','/technical','/size','/rr']);
export function calculate(text) {
  if (!text || text.length>200) throw new Error('expression');
  const parts = text.match(/(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|\*\*|[()+*/%\-]|\S/gi) || [];
  if (parts.length>50) throw new Error('complexity');
  let i=0;
  const bound = n => {if (!Number.isFinite(n) || Math.abs(n)>1e100) throw new Error('range'); return n;};
  function atom() {
    const token=parts[i++];
    if (token==='(') {const value=sum(); if(parts[i++]!==')') throw new Error('parenthesis'); return value;}
    if (!/^(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(token || '')) throw new Error('number');
    return bound(Number(token));
  }
  function unary() {if(parts[i]==='+'){i++;return unary();} if(parts[i]==='-'){i++;return -unary();} return power();}
  function power() {let value=atom(); if(parts[i]==='**'){i++;const exponent=unary(); if(Math.abs(exponent)>100)throw new Error('exponent'); value=bound(value**exponent);}return value;}
  function product() {let v=unary(); while(['*','/','%'].includes(parts[i])){const op=parts[i++],b=unary();v=bound(op==='*'?v*b:op==='/'?v/b:v%b);}return v;}
  function sum() {let v=product();while(['+','-'].includes(parts[i])){const op=parts[i++],b=product();v=bound(op==='+'?v+b:v-b);}return v;}
  const value=sum();if(i!==parts.length)throw new Error('syntax');return value;
}
function positive(text) { const n=Number(text);if(!text || !Number.isFinite(n)||n<=0||n>1e15)throw new Error('number');return n; }
function pair(text) {if(!/^[A-Z0-9]{2,12}-[A-Z0-9]{2,12}$/.test(text))throw new Error('pair');return text;}
export function indicators(rows, seconds, now) {
  const candles=new Map();
  for(const row of rows){
    const [start,low,high,open,close,volume]=row.map(Number);
    if(![start,low,high,open,close,volume].every(Number.isFinite))throw new Error('candle');
    if(start+seconds>now)continue;
    if(low<=0||low>Math.min(open,close)||high<Math.max(open,close)||volume<0)throw new Error('candle');
    candles.set(start,close);
  }
  const samples=[...candles].sort((a,b)=>a[0]-b[0]).slice(-20);
  if(samples.length<20||samples.some((x,i)=>i&&x[0]-samples[i-1][0]!==seconds))throw new Error('missing candles');
  const prices=samples.map(x=>x[1]);let gain=0,loss=0;
  for(let i=6;i<20;i++){const change=prices[i]-prices[i-1];gain+=Math.max(change,0);loss+=Math.max(-change,0);}
  return {close:prices[19],sma:prices.reduce((a,b)=>a+b)/20,rsi:gain===0&&loss===0?50:loss===0?100:100-100/(1+gain/loss),end:samples[19][0]+seconds};
}
async function get(fetch, url){const r=await fetch(url);if(!r.ok)throw new Error('market unavailable');return await r.json();}
export async function runTool(command, text, fetch, now=Date.now()) {
  try {
    if(command==='/calc')return String(calculate(text));
    if(command==='/time')return new Intl.DateTimeFormat('en-GB',{dateStyle:'full',timeStyle:'long',timeZone:text||'UTC'}).format(new Date(now));
    if(command==='/size'||command==='/rr'){
      const values=text.split(/\s+/).map(positive);
      if(command==='/size'){
        if(values.length!==4)throw new Error('usage');
        const [equity,risk,entry,stop]=values;if(risk>100||entry===stop)throw new Error('usage');
        const budget=equity*risk/100,units=budget/Math.abs(entry-stop);
        return `Direction: ${stop<entry?'long':'short'}\nRisk budget: ${budget.toPrecision(8)}\nUnits: ${units.toPrecision(8)}\nNotional: ${(units*entry).toPrecision(8)}\nLinear instrument; same quote currency for equity and prices. Excludes fees, slippage, gaps, leverage and contract multipliers.`;
      }
      if(values.length!==3)throw new Error('usage');
      const [entry,stop,target]=values;if(!(stop<entry&&entry<target||target<entry&&entry<stop))throw new Error('usage');
      const risk=Math.abs(entry-stop),reward=Math.abs(target-entry);
      return `Reward/risk: ${(reward/risk).toPrecision(8)}R\nBreak-even win rate before costs: ${(100*risk/(risk+reward)).toFixed(2)}%\nAssumes full exits at stop or target; excludes fees and slippage.`;
    }
    if(command==='/weather'){
      if(!text||text.length>120)throw new Error('city');
      const places=await get(fetch,`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(text)}&count=1&language=en&format=json`);
      const p=places.results?.[0];if(!p)return 'City not found.';
      const data=await get(fetch,`https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(p.latitude)}&longitude=${encodeURIComponent(p.longitude)}&current=temperature_2m,apparent_temperature,wind_speed_10m&timezone=auto`);
      const c=data.current,u=data.current_units;
      return `${p.name}, ${p.country}\nTemperature: ${c.temperature_2m} ${u.temperature_2m}\nFeels like: ${c.apparent_temperature} ${u.apparent_temperature}\nWind: ${c.wind_speed_10m} ${u.wind_speed_10m}\nAs of ${c.time} (${data.timezone})\nSource: Open-Meteo, first matching city.`;
    }
    const fields=text.toUpperCase().split(/\s+/),symbol=pair(fields[0]);
    const base=`https://api.exchange.coinbase.com/products/${symbol}`;
    if(command==='/quote'){
      if(fields.length!==1)throw new Error('pair');
      const data=await get(fetch,base+'/ticker'),price=positive(data.price),date=new Date(data.time);
      if(!Number.isFinite(date.getTime()))throw new Error('time');
      return `${symbol}: ${price}\nLast trade: ${date.toISOString()}\n${now-date.getTime()>300000?'STALE: last trade older than five minutes.\n':''}Source: Coinbase Exchange; last trade, not an execution price.`;
    }
    const seconds={'5M':300,'15M':900,'1H':3600,'1D':86400}[fields[1]];
    if(fields.length!==2||!seconds)throw new Error('interval');
    const result=indicators(await get(fetch,base+`/candles?granularity=${seconds}`),seconds,now/1000);
    return `${symbol}\nLast closed price: ${result.close}\nSMA20: ${result.sma.toPrecision(8)}\nRSI14 (simple average, not Wilder): ${result.rsi.toFixed(2)}\nCandle closed: ${new Date(result.end*1000).toISOString()}\n${now/1000-result.end>seconds*2?'STALE DATA\n':''}Source: Coinbase Exchange. Indicators describe data, not buy/sell signals.`;
  } catch {return 'Invalid inputs, insufficient data, or service unavailable. Usage:\n'+toolHelp;}
}
