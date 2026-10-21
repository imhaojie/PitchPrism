// Original GameBuddy CourtPanel owns header, material, segmented controls and fitting.
// This adapter replaces only basketball geometry and source data with a football pitch.
import {createCourtPanel} from './shared/court/court-panel.js';
import {svgNode} from './shared/court/court-geometry.js';

export function createFootballPitch({onMode,onSelect,onTheme}) {
  const original=createCourtPanel({onMode,onSelect,onTheme});
  const element=original.element;
  const $=s=>element.querySelector(s);
  const svg=svgNode('svg',{class:'court-svg football-svg',viewBox:'0 0 68 105',role:'img','aria-label':'Football event positions, editorial schematic'});
  svg.innerHTML=`<defs><pattern id="football-grass" width="68" height="10.5" patternUnits="userSpaceOnUse"><rect width="68" height="10.5" fill="#214635"/><rect width="68" height="5.25" fill="#284d3a"/></pattern><marker id="football-arrow" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="4" markerHeight="4" orient="auto"><path d="M1 1 6 4 1 7" fill="none" stroke="#6fe3ff" stroke-width="1.4"/></marker></defs>
    <rect width="68" height="105" fill="url(#football-grass)"/><g class="court-lines"><rect x=".4" y=".4" width="67.2" height="104.2"/><path d="M0 52.5H68M13.84 0V16.5H54.16V0M24.84 0V5.5H43.16V0M13.84 105V88.5H54.16V105M24.84 105V99.5H43.16V105"/><circle cx="34" cy="52.5" r="9.15"/><circle cx="34" cy="11" r=".5"/><circle cx="34" cy="94" r=".5"/><path d="M27.6 16.5A9.15 9.15 0 0 0 40.4 16.5M27.6 88.5A9.15 9.15 0 0 1 40.4 88.5"/></g><g class="football-routes"></g><g class="football-players"></g><circle class="football-ball" r=".8" fill="#fff7d3"/>`;
  $('.court-drawing').replaceChildren(svg);
  $('.court-theme-choice select').innerHTML='<option value="mavericks">Manchester City</option><option value="rockets">Newcastle United</option>';
  element.querySelector('[data-court-mode="fullCourt"]').textContent='全场';
  element.querySelector('[data-court-mode="halfCourt"]').textContent='半场';
  $('.court-legend').innerHTML='<span><i class="dark-team"></i>Manchester City</span><span><i class="white-team"></i>Newcastle</span><span><i class="route-swatch"></i>可选线路</span><span>已审核定格 · 编辑示意</span>';
  let half=0,match=null,selected='all',team='MCI';
  function setTheme(value){team=value==='rockets'?'NEW':'MCI';$('.court-city').textContent=team==='MCI'?'MANCHESTER':'NEWCASTLE';$('.court-team-name').textContent=team==='MCI'?'CITY':'UNITED';$('.court-team-logo').hidden=true;$('.court-team-short').hidden=false;$('.court-team-short').textContent=team;$('.court-team-badge').classList.remove('has-logo');element.querySelectorAll('.court-baseline').forEach(e=>e.textContent='PITCHPRISM / FOOTBALL');}
  function fit(){const zone=$('.court-view-zone');const w=Math.min(zone.clientWidth-2,(zone.clientHeight-12)*68/(105-half*52.5));if(w<=0)return;$('.court-floor-frame').style.width=w+'px';svg.style.height=w*(105-half*52.5)/68+'px';$('.court-floor-frame').style.setProperty('--court-cap-height','7px');}
  function setView(value){half=value;original.setView(value);svg.setAttribute('viewBox',`0 0 68 ${105-half*52.5}`);fit();}
  const project=point=>[point[1]*.68,(100-point[0])*1.05];
  function update(state,time,focus){
    if(!match||!state)return;selected=focus||'all';element.dataset.hasData='true';
    const scene=state.scene;
    const routes=$('.football-routes'),players=$('.football-players');routes.replaceChildren();players.replaceChildren();
    const ball=$('.football-ball');ball.style.display='none';
    let note=$('.football-snapshot-note');if(!note){note=document.createElement('p');note.className='football-snapshot-note';$('.court-legend').before(note);}
    note.textContent=scene?`定格 ${scene.clock} · 原片 ${scene.second.toFixed(2)}s / 非实时追踪`:'播放至 8 秒解锁首个定格示意';
    if(!scene)return;const locations=Object.fromEntries(scene.players.map(p=>[p.id,p.board]));
    for(const e of scene.routes.filter(e=>e.kind==='option'&&(selected==='all'||[e.a,e.b].includes(selected)))){const a=project(locations[e.a]),b=project(locations[e.b]);routes.append(svgNode('path',{d:`M${a}L${b}`,class:'court-route','stroke-dasharray':'1.5 1','marker-end':'url(#football-arrow)'}));}
    for(const p of scene.players){const [x,y]=project(p.board);const marker=svgNode('g',{class:'court-player'+(selected===p.id?' is-focused':''),transform:`translate(${x} ${y})`,'data-team':p.team==='MCI'?'dark':'white',role:'button',tabindex:y<=105-half*52.5?'0':'-1','aria-label':p.team+' '+(p.label||'可见防守角色')});marker.append(svgNode('circle',{r:selected===p.id?2.5:1.9}));const label=svgNode('text',{'text-anchor':'middle','dominant-baseline':'central'});label.textContent=p.id==='carrier'?'●':p.active?'◆':'';marker.append(label);marker.style.opacity=selected==='all'||selected===p.id?'1':'.32';if(match.roster.some(r=>r.id===p.id)){marker.onclick=()=>onSelect(p.id);marker.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(p.id);}};}players.append(marker);}
    const carrier=locations.carrier;if(carrier){const [x,y]=project(carrier);ball.style.display='';ball.setAttribute('cx',x);ball.setAttribute('cy',y);}fit();
  }
  const observer=new ResizeObserver(fit);observer.observe($('.court-view-zone'));setTheme('mavericks');
  return {...original,setView,update,setTheme,setStory(value){match=value;},setStyle(next){original.setStyle({...next,woodColor:'#214635',paintColor:'#173a2b',lineColor:'#dae9db'});fit();},destroy(){observer.disconnect();original.destroy();}};
}
