const STATIC_DEMO=false;
let staticData;
async function staticApi(path,options){
  staticData??=await fetch(new URL('./demo-data.json?v=english-v1',import.meta.url)).then(r=>r.json());
  if(path==='/api/health')return {ok:true,service:'PitchPrism',synthetic:false,foundryConfigured:false,foundryVerified:false,provider:'local',mediaReady:true,staticDemo:true};
  if(path==='/api/clip')return staticData.match;
  const body=options?.body?JSON.parse(options.body):{};
  const t=path.startsWith('/api/clip/snapshot')?Number(new URL(path,'https://example.local').searchParams.get('t')):Number(body.second||0);
  const second=Math.max(0,Math.min(staticData.match.durationSeconds,t));
  const index=staticData.states.findLastIndex(s=>s.sourceSecond<=second);
  if(path.startsWith('/api/clip/snapshot'))return {...staticData.states[index],sourceSecond:second};
  if(path==='/api/clip/explain'){if(body.provider==='azure-foundry')throw new Error('This public static demo uses local evidence mode. Azure requires the server deployment.');return {...staticData.stories[`${index}|${body.mode||'casual'}|${body.team||'all'}|${body.player||'all'}`],sourceSecond:second};}
  if(path==='/api/recap')return staticData.recap;
  throw new Error('Unknown static demo operation');
}
export async function api(path,options){if(STATIC_DEMO)return staticApi(path,options);const response=await fetch(path,options);const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);return data;}
