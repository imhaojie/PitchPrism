import {createPlayerControls} from './shared/media/player-controls.js';
import {fitContain} from './shared/stage/layout.js';
import {sourceToOutputTime,outputToSourceTime,readPreferences,savePreferences} from './shared/adapters/catalog.js';

const $=selector=>document.querySelector(selector), $$=selector=>[...document.querySelectorAll(selector)];
const video=$('#match-video'), canvas=$('#tactics'), context=canvas.getContext('2d');
const esc=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const storage={getItem:()=>localStorage.getItem('pitchprism.preferences.v1'),setItem:(_key,value)=>localStorage.setItem('pitchprism.preferences.v1',value)};
let preference;try{preference=readPreferences(storage);}catch{preference={familiarity:'beginner',purpose:'enjoy',player:'all'};}
let mode=preference.familiarity==='familiar'?'analyst':'casual', team='all', player='all', variant='enhanced', tactical=false;
let match, storyMap, state, story, health, snapshotSequence=0, storySequence=0, lastSource=-1, noticeTimer, explaining=false;
const controls=createPlayerControls({video,stage:$('#stage'),locale:'en',onError:notice});
$('#controls-host').append(controls.element);
const clock=second=>`${Math.floor(second/60)}:${String(Math.floor(second%60)).padStart(2,'0')}`;
const sourceTime=()=>variant==='enhanced'?outputToSourceTime(storyMap,video.currentTime):video.currentTime;
const playerName=id=>match?.roster.find(p=>p.id===id)?.name||id;
const shortName=id=>playerName(id).split(' ').at(-1);
const STATIC_DEMO=false;
let staticData;
async function staticApi(path,options){
  staticData??=await fetch(new URL('./demo-data.json',import.meta.url)).then(r=>r.json());
  if(path==='/api/health')return {ok:true,service:'PitchPrism',synthetic:true,foundryConfigured:false,foundryVerified:false,provider:'local',mediaReady:true,staticDemo:true};
  if(path==='/api/match')return staticData.match;
  const body=options?.body?JSON.parse(options.body):{};
  const t=path.startsWith('/api/snapshot')?Number(new URL(path,'https://example.local').searchParams.get('t')):Number(body.second||0);
  const second=Math.max(0,Math.min(48,t));
  const index=staticData.states.findLastIndex(s=>s.sourceSecond<=second);
  if(path.startsWith('/api/snapshot'))return {...staticData.states[index],sourceSecond:second,clockSeconds:staticData.match.clockStartSeconds+Math.floor(second)};
  if(path==='/api/explain'){if(body.provider==='azure-foundry')throw new Error('This public static demo uses local evidence mode. Azure requires the server deployment.');return {...staticData.stories[`${index}|${body.mode||'casual'}|${body.team||'all'}|${body.player||'all'}`],sourceSecond:second};}
  if(path==='/api/recap')return staticData.recap;
  throw new Error('Unknown static demo operation');
}
async function api(path,options){if(STATIC_DEMO)return staticApi(path,options);const response=await fetch(path,options);const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);return data;}
function notice(message){$('#notice').textContent=message;$('#notice').hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('#notice').hidden=true,5500);}
function persist(){try{savePreferences({familiarity:mode==='analyst'?'familiar':'beginner',purpose:mode==='analyst'?'analyze':'enjoy',player},storage);localStorage.setItem('pitchprism.focus.v1',JSON.stringify({team,player}));}catch{/* Browsing in private mode still works. */}}
function eventMatches(event){return (team==='all'||event.team===team)&&(player==='all'||[event.playerId,event.recipientId].includes(player));}
function paintStats(){
  const a=state.stats.NBR,b=state.stats.RIV;
  $('#score').innerHTML=`${a.goals} <span>–</span> ${b.goals}`;
  $('#clock').textContent=clock(state.clockSeconds);
  const rows=[['Completed passes',a.completedPasses,b.completedPasses,''],['Pass accuracy',a.passAccuracy,b.passAccuracy,'%'],['Shots',a.shots,b.shots,''],['Scenario xG',a.xg,b.xg,'']];
  $('#stat-table').innerHTML=rows.map(([label,home,away,unit])=>{
    const format=v=>v===null?'—':label==='Scenario xG'?v.toFixed(2):v+unit;
    const share=(home||0)+(away||0)>0?Math.max(5,Math.min(95,(home||0)/((home||0)+(away||0))*100)):50;
    return `<div class="stat-cell"><div class="stat-title">${label}</div><div class="stat-values"><span>${format(home)}</span><span>${format(away)}</span></div><div class="stat-bar"><span style="flex:${share}"></span><span style="flex:${100-share}"></span></div></div>`;
  }).join('');
  const fact=state.facts[0];
  $('#fact-label').textContent=mode==='analyst'?'LATEST PASS · DERIVED DISTANCE':'THE BALL JUST TRAVELLED';
  $('#fact-value').textContent=fact?fact.value.toFixed(1):'—';
  $('#fact-note').textContent=mode==='analyst'?'105 × 68 m pitch · Euclidean distance':'Derived from synthetic event coordinates';
  $('#event-count').textContent=`${state.events.length} EVENTS`;
  const events=state.events.slice(-4).reverse();
  $('#events').innerHTML=events.map(e=>`<li class="${eventMatches(e)?'':'dim'}"><time>${clock(match.clockStartSeconds+e.second)}</time><span class="trail-dot"></span><div><strong>${esc(shortName(e.playerId))}${e.recipientId?' → '+esc(shortName(e.recipientId)):''}</strong><small>${esc(e.type.toUpperCase())} · ${esc(e.outcome.toUpperCase())} · ${esc(e.id)}</small></div></li>`).join('');
  const chapters=$$('.chapter');const active=chapters.filter(c=>+c.dataset.second<=state.sourceSecond).at(-1);
  chapters.forEach(c=>{c.classList.toggle('active',c===active);c.setAttribute('aria-current',c===active?'true':'false');});
  $('#focus-tag').hidden=player==='all'&&team==='all';
  $('#focus-tag').textContent=player!=='all'?`FOLLOWING ${playerName(player).toUpperCase()}`:`FOLLOWING ${match.teams.find(t=>t.id===team)?.name.toUpperCase()}`;
}
function paintStory(result){
  story=result;
  $('#story-title').textContent=result.headline;$('#story-copy').textContent=result.explanation;
  $('#citation-count').textContent=`${result.evidenceIds.length} source event${result.evidenceIds.length===1?'':'s'}`;
  $('#story-clock').textContent=clock(match.clockStartSeconds+result.sourceSecond);
  $('#story-kind').textContent=result.provider==='azure-foundry'?'FOUNDRY · VALIDATED':'LOCAL EVIDENCE MODE';
  $('#provider-badge').textContent=result.provider==='azure-foundry'?'FOUNDRY':'LOCAL';
}
async function localExplain(){
  if(!state||explaining)return;
  const sequence=++storySequence;
  try{const result=await api('/api/explain',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({second:state.sourceSecond,mode,team,player,provider:'local'})});if(sequence===storySequence)paintStory(result);}catch(error){notice(error.message);}
}
async function refresh(force=false){
  if(!match)return;const second=sourceTime();if(second===null)return;
  if(!force&&Math.abs(second-lastSource)<.45)return;lastSource=second;
  const sequence=++snapshotSequence;
  try{const value=await api('/api/snapshot?t='+encodeURIComponent(second));if(sequence!==snapshotSequence)return;state=value;paintStats();if(!explaining)await localExplain();drawTactics();}catch(error){notice(error.message);}
}
function seekSource(second){if(!storyMap)return;video.currentTime=variant==='enhanced'?sourceToOutputTime(storyMap,second):second;video.pause();refresh(true);}
function setAudience(value){mode=value;$$('[data-mode]').forEach(button=>{const active=button.dataset.mode===mode;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});persist();if(state){paintStats();localExplain();}}
function setView(value){tactical=value;canvas.hidden=!value;$('#match-view').classList.toggle('active',!value);$('#tactical-view').classList.toggle('active',value);$('#match-view').setAttribute('aria-pressed',String(!value));$('#tactical-view').setAttribute('aria-pressed',String(value));$('#scene-note').textContent=value?'EDITORIAL EVENT MAP · SYNTHETIC POSITIONS · NOT OPTICAL TRACKING':'ORIGINAL SYNTHETIC SIMULATION · EDITORIAL OVERLAYS';drawTactics();}
async function switchVideo(next){
  if(variant===next)return;const second=sourceTime(),wasPlaying=!video.paused;variant=next;
  $$('.media-switch button').forEach(b=>{const active=b.id===`${next}-version`;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  video.src=new URL(`./media/${next}.mp4`,import.meta.url).href;video.addEventListener('loadedmetadata',()=>{video.currentTime=next==='enhanced'?sourceToOutputTime(storyMap,second):second;if(wasPlaying)video.play().catch(error=>notice(error.message));refresh(true);},{once:true});video.load();
}

function drawTactics(){
  if(!tactical||!match||!state)return;
  const ratio=Math.min(devicePixelRatio||1,2),width=canvas.clientWidth,height=canvas.clientHeight;
  if(width<160||height<180)return;
  if(canvas.width!==Math.round(width*ratio)||canvas.height!==Math.round(height*ratio)){canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);}
  context.setTransform(ratio,0,0,ratio,0,0);context.clearRect(0,0,width,height);
  const fit=fitContain(width-76,height-162,105/68),left=(width-fit.width)/2,top=89;
  const point=([x,y])=>[left+x/100*fit.width,top+y/100*fit.height];
  const path=points=>{context.beginPath();points.forEach((p,i)=>{const [x,y]=point(p);i?context.lineTo(x,y):context.moveTo(x,y);});context.stroke();};
  context.fillStyle='#1b392f';context.fillRect(left,top,fit.width,fit.height);
  for(let i=0;i<10;i++){context.fillStyle=i%2?'#214236':'#1d3d32';context.fillRect(left+i*fit.width/10,top,fit.width/10,fit.height);}
  context.strokeStyle='#6f897155';context.lineWidth=1;path([[0,0],[100,0],[100,100],[0,100],[0,0]]);path([[50,0],[50,100]]);
  for(const [x,sign]of[[0,1],[100,-1]]){path([[x,20],[x+16*sign,20],[x+16*sign,80],[x,80]]);path([[x,36],[x+5*sign,36],[x+5*sign,64],[x,64]]);}
  context.beginPath();context.ellipse(left+fit.width/2,top+fit.height/2,fit.width*9.15/105,fit.height*9.15/68,0,0,Math.PI*2);context.stroke();
  const positions=Object.fromEntries(match.roster.map(p=>[p.id,[...p.position]]));
  for(const event of state.events){positions[event.playerId]=event.start;if(event.recipientId&&event.outcome==='complete')positions[event.recipientId]=event.end;}
  const passes=state.events.filter(e=>e.type==='pass'&&state.sourceSecond-e.second<11&&eventMatches(e));
  for(const pass of passes){const [ax,ay]=point(pass.start),[bx,by]=point(pass.end);context.strokeStyle=pass.team==='NBR'?'#d8f790':'#b2adfc';context.lineWidth=2;context.setLineDash(pass.outcome==='complete'?[]:[5,5]);path([pass.start,pass.end]);context.setLineDash([]);const angle=Math.atan2(by-ay,bx-ax);context.beginPath();context.moveTo(bx,by);context.lineTo(bx-9*Math.cos(angle-.4),by-9*Math.sin(angle-.4));context.moveTo(bx,by);context.lineTo(bx-9*Math.cos(angle+.4),by-9*Math.sin(angle+.4));context.stroke();}
  for(const p of match.roster){const [x,y]=point(positions[p.id]),focused=player===p.id,dim=(player!=='all'&&!focused)||(team!=='all'&&p.team!==team);context.globalAlpha=dim?.25:1;context.fillStyle=p.team==='NBR'?'#d8f790':'#b2adfc';context.shadowColor=context.fillStyle;context.shadowBlur=focused?16:0;context.beginPath();context.arc(x,y,focused?9:6,0,Math.PI*2);context.fill();context.shadowBlur=0;context.fillStyle='#132b23';context.font='600 7px DM';context.textAlign='center';context.fillText(String(p.number),x,y+2.5);if(focused||mode==='analyst'){context.fillStyle='#d9e5ca';context.font='8px DM';context.fillText(p.name.split(' ').at(-1).toUpperCase(),x,y-12);}context.globalAlpha=1;}
  context.textAlign='left';context.fillStyle='#adbf9b';context.font='9px DM';context.fillText('NORTHBRIDGE ATTACK →',left,top+fit.height+22);context.textAlign='right';context.fillStyle='#b0a7cd';context.fillText('← RIVERSIDE ATTACK',left+fit.width,top+fit.height+22);
}

function openDialog(eyebrow,html){$('#dialog-eyebrow').textContent=eyebrow;$('#dialog-body').innerHTML=html;$('#details').showModal();}
$('#details-close').onclick=()=>$('#details').close();$('#details').addEventListener('click',event=>{if(event.target===$('#details')){const r=$('#details').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)$('#details').close();}});
$('#evidence-open').onclick=()=>{const ids=story?.evidenceIds||[];const events=match.events.filter(e=>ids.includes(e.id));openDialog('EVIDENCE / '+clock(match.clockStartSeconds+(story?.sourceSecond||0)),`<h2>Every insight has a source.</h2><p>These exact synthetic events support the displayed story. Coordinates are normalized percentages on a scenario pitch. Shot xG is a supplied scenario input. Prose is editorial or model interpretation, never an official match fact.</p><pre>${esc(JSON.stringify(events,null,2))}</pre>${story?.trace?`<h3>Foundry tool trace</h3><pre>${esc(JSON.stringify(story.trace,null,2))}</pre>`:''}`);};
$('#sources-open').onclick=()=>openDialog('DATA & TRANSPARENCY',`<h2>Real clarity. Fictional football.</h2><p>Northbridge AFC and Riverside United are fictional. All players, events, coordinates, shot xG inputs and the rendered video were created for this demo. No Premier League footage, official match feed, optical tracking, or trained xG model is used.</p><p>Pass accuracy = completed / attempted passes. Pass distance uses Euclidean geometry on a synthetic 105 × 68 metre pitch. Missing xG is shown as a dash. All live statistics cover only the played excerpt.</p><p>Enhanced video adds editorial paths, labels, pauses and replay. The original source clock is retained using GameBuddy's dual-timeline mapping. Frozen and replayed moments do not reveal future events.</p><p>Azure Foundry stories require a successful real API response and tool validation. Local evidence mode uses deterministic editorial templates and is labelled LOCAL. Validation checks references and numbers; it cannot prove every tactical interpretation.</p><p><a href="https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md" target="_blank" rel="noopener">Hackathon rules ↗</a></p>`);
$('#about-open').onclick=()=>openDialog('ABOUT PITCHPRISM',`<h2>Every angle tells a story.</h2><p>An AI-powered football companion that turns match data into visual stories and personalized insights.</p><p>PitchPrism adapts open-source GameBuddy components: the video player, source/output timeline, viewing preferences, evidence-first agent workflow and numeric guardrails. Its synthetic football scenario, analytics, event map, English fan/analyst experiences and Azure Foundry adapter are new.</p><p>GameBuddy's NBA × AWS award applies to the original basketball project. This new adaptation has no award or eligibility claim. New-work eligibility needs organizer confirmation.</p>`);
$('#recap-open').onclick=async()=>{try{const recap=await api('/api/recap');openDialog('FULL SYNTHETIC EXCERPT RECAP',`<h2>${esc(recap.story.headline)}</h2><p>${esc(recap.story.explanation)}</p><p>This explicitly requested recap covers the entire fictional excerpt and can include events ahead of the player's current position.</p><pre>${esc(JSON.stringify(recap.stats,null,2))}</pre>`);}catch(error){notice(error.message);}};
$$('[data-mode]').forEach(button=>button.onclick=()=>setAudience(button.dataset.mode));
$('#team').onchange=event=>{team=event.target.value;if(player!=='all'&&team!=='all'&&match.roster.find(p=>p.id===player)?.team!==team){player='all';$('#player').value='all';}persist();paintStats();drawTactics();localExplain();};
$('#player').onchange=event=>{player=event.target.value;if(player!=='all'&&team!=='all'){team=match.roster.find(p=>p.id===player).team;$('#team').value=team;}persist();paintStats();drawTactics();localExplain();};
$('#match-view').onclick=()=>setView(false);$('#tactical-view').onclick=()=>setView(true);
$('#source-version').onclick=()=>switchVideo('source');$('#enhanced-version').onclick=()=>switchVideo('enhanced');
$$('.chapter').forEach(button=>button.onclick=()=>seekSource(+button.dataset.second));
$('#explain').onclick=async()=>{
  if(!state||explaining)return;video.pause();explaining=true;++storySequence;const anchor=state.sourceSecond,requestedMode=mode,requestedTeam=team,requestedPlayer=player;
  const button=$('#explain');button.disabled=true;const previous=button.innerHTML;button.textContent=health.foundryConfigured?'Reading events → checking evidence…':'Reading the source events…';
  try{const result=await api('/api/explain',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({second:anchor,mode,team,player,provider:health.foundryConfigured?'azure-foundry':'local'})});if(Math.abs(sourceTime()-anchor)>.5||mode!==requestedMode||team!==requestedTeam||player!==requestedPlayer){notice('The view changed during generation. Request an explanation for the new moment.');return;}paintStory(result);if(result.provider==='azure-foundry'){$('#provider-note').textContent=`Real Foundry response · ${result.tokens} tokens · source references validated`;notice('Foundry explanation validated. Open source events to inspect the tool trace.');}else notice('Evidence-based local explanation. Foundry needs an Azure deployment.');}
  catch(error){notice(error.message);$('#provider-note').textContent='Cloud explanation failed. Local mode remains available; no cloud success was recorded.';}
  finally{explaining=false;button.disabled=false;button.innerHTML=previous;}
};
video.addEventListener('timeupdate',()=>{const segment=storyMap?.production.timeline.find(s=>video.currentTime>=s.outputStart&&video.currentTime<s.outputEnd);$('#replay-indicator').hidden=variant!=='enhanced'||segment?.kind!=='replay';refresh();});
video.addEventListener('seeked',()=>refresh(true));video.addEventListener('error',()=>{$('#media-error').hidden=false;notice('Media unavailable; switch to Tactical or install release media.');});video.addEventListener('loadeddata',()=>$('#media-error').hidden=true);
new ResizeObserver(drawTactics).observe($('#stage'));
document.addEventListener('keydown',event=>{if($('#details').open||['INPUT','SELECT','TEXTAREA','BUTTON'].includes(document.activeElement.tagName))return;if(event.code==='Space'){event.preventDefault();video.paused?video.play().catch(error=>notice(error.message)):video.pause();}if(event.key==='ArrowRight'){event.preventDefault();seekSource(Math.min(48,sourceTime()+5));}if(event.key==='ArrowLeft'){event.preventDefault();seekSource(Math.max(0,sourceTime()-5));}});

async function init(){
  [match,health]=await Promise.all([api('/api/match'),api('/api/health')]);
  storyMap={...match,enhancedAvailable:true};
  $('#player').innerHTML='<option value="all">The whole pitch</option>'+match.roster.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
  try{const saved=JSON.parse(localStorage.getItem('pitchprism.focus.v1'));if(['all','NBR','RIV'].includes(saved?.team))team=saved.team;if(match.roster.some(p=>p.id===saved?.player))player=saved.player;}catch{}
  $('#team').value=team;$('#player').value=player;setAudience(mode);
  if(health.foundryConfigured){$('#provider-note').textContent='Azure Foundry configured. Explain a moment to verify the live model.';$('#provider-badge').textContent='READY';}
  video.addEventListener('loadedmetadata',()=>{video.currentTime=sourceToOutputTime(storyMap,20);refresh(true);},{once:true});video.src=new URL('./media/enhanced.mp4',import.meta.url).href;video.load();
  if(!health.mediaReady){setView(true);state=await api('/api/snapshot?t=20');paintStats();await localExplain();drawTactics();}
}
init().catch(error=>notice(error.message));
