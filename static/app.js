const track=(name,details)=>window.HoraryAnalytics?.track(name,details);
const {t,language,locale}=window.HoraryI18n;
const $=id=>document.getElementById(id);let city=null,current=null,shared=false,timer,searchVersion=0;
let voiceBusy=false, readingBusy=false, servicePaused=false;
function updateButtons(){ $('submitBtn').disabled=voiceBusy||readingBusy||servicePaused; if($('voiceStart')) $('voiceStart').disabled=readingBusy||servicePaused; if($('voiceConfirm')) $('voiceConfirm').disabled=readingBusy||servicePaused; }
document.addEventListener('voicebusy',e=>{voiceBusy=e.detail;updateButtons()});
const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e};
async function api(path,options={}){const r=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-Horary-Language':language,...options.headers}});let d;try{d=await r.json()}catch{throw Error(t('Сервис временно недоступен. Попробуйте позже.'))}if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:t('Проверьте заполнение формы.'));return d}
function view(id){document.dispatchEvent(new Event('horaryview'));for(const v of ['landing','result','archive'])$(v).hidden=v!==id;window.scrollTo({top:0,behavior:'smooth'})}
function error(message){$('formError').textContent=message;$('formError').hidden=false}
let questionStarted=false;
$('question').addEventListener('input',()=>{if(!questionStarted&&$('question').value.trim()){questionStarted=true;track('question_started');}$('counter').textContent=`${$('question').value.length} / 500`;$('question').setCustomValidity($('question').value.length>500?t('Сократите вопрос до 500 символов.'):'')});
$('city').addEventListener('input',()=>{city=null;clearTimeout(timer);const version=++searchVersion;$('cityList').hidden=true;$('city').setAttribute('aria-expanded','false');timer=setTimeout(async()=>{try{const rows=await api('/api/cities?q='+encodeURIComponent($('city').value));if(version!==searchVersion)return;$('cityList').replaceChildren();for(const c of rows){const b=text('button',`${c.name} · ${c.country}`);b.type='button';b.setAttribute('role','option');b.onclick=()=>{track('city_selected');city=c;$('city').value=`${c.name} · ${c.country}`;$('cityList').hidden=true;$('city').setAttribute('aria-expanded','false')};$('cityList').append(b)}if(!rows.length)$('cityList').append(text('p',t('Город не найден. Попробуйте название латиницей.'),'hint'));$('cityList').hidden=false;$('city').setAttribute('aria-expanded','true')}catch{error(t('Не удалось загрузить города. Попробуйте ещё раз.'))}},250)});
document.addEventListener('click',e=>{if(!e.target.closest('.city-wrap')){$('cityList').hidden=true;$('city').setAttribute('aria-expanded','false')}});
function showTurns(target,turns){target.replaceChildren();for(const turn of turns){target.append(text('p',turn.prompt,'hint'),text('p',turn.answer));}target.hidden=!turns.length;}
$('questionForm').onsubmit=async e=>{
 e.preventDefault();if(voiceBusy||readingBusy||servicePaused)return;$('formError').hidden=true;
 if(!city){error(t('Выберите город из выпадающего списка.'));return}
 track('reading_submitted');const readingStart=performance.now();readingBusy=true;updateButtons();$('question').readOnly=true;$('loading').hidden=false;
 try{const r=await api('/api/readings',{method:'POST',body:JSON.stringify({question:$('question').value,city_id:city.id,consent:$('consent').checked,language})});
 render(r,false);track('reading_completed',{duration_ms:performance.now()-readingStart});
 }catch(e){track('reading_failed',{error_type:'unknown'});error(e.message)}finally{readingBusy=false;updateButtons();$('question').readOnly=false;$('loading').hidden=true;}
};
function render(r,isShared){current=r;shared=isShared;if(isShared)track('shared_reading_viewed');view('result');$('result').focus();$('resultLabel').textContent=r.id==='demo'?t('ПРИМЕР · НЕ ПЕРСОНАЛЬНЫЙ РАЗБОР'):isShared?t('ОПУБЛИКОВАННЫЙ РАЗБОР'):t('ВАШ ПРИВАТНЫЙ РАЗБОР');$('resultQuestion').textContent=r.question;showTurns($('resultClarifications'),r.data.clarifications||[]);$('resultMeta').textContent=`${r.city} · ${new Date(r.data.time).toLocaleString(locale)} (${t('время вашего браузера')})`;$('readingLanguageNote').hidden=(r.data.language||'ru')===language;$('readingLanguageNote').textContent=t('Язык исходного разбора: {language}. Текст сохранён без перевода.',{language:r.data.language||'ru'});$('summary').textContent=r.data.answer.summary;$('reflection').textContent=r.data.answer.reflection;$('factors').replaceChildren();for(const [i,f] of r.data.answer.factors.entries()){const box=text('article','','factor');box.append(text('span',`0${i+1}`,'step'),text('p',f.text),text('small',t('Основание: {fact} · правило {rule}',{fact:f.fact_id,rule:f.rule_id})));$('factors').append(box)}
// SVG is generated exclusively by the server from numeric ephemeris data, never from model/user text.
$('chart').innerHTML=r.svg;renderEvents(r);$('warnings').replaceChildren(...r.data.warnings.map(w=>text('p',w,'warning')));$('method').textContent=r.data.method+(r.data.model?t(' · Модель ИИ: ')+r.data.model:'');$('limits').replaceChildren(...r.data.limitations.map(w=>text('li',w)));$('planetTable').replaceChildren();for(const p of r.data.planets){const tr=document.createElement('tr');for(const val of [p.name,p.sign,p.degree+'°',p.house,p.retrograde?t('Ретроградное'):t('Прямое')])tr.append(text('td',val));$('planetTable').append(tr)}$('aspectList').replaceChildren(text('h3',t('Аспекты в пределах 6°')));for(const a of r.data.aspects){const names=a.a.slice(1)+' '+a.b.slice(1);$('aspectList').append(text('p',`${r.data.planets[+a.a.slice(1)].name} — ${r.data.planets[+a.b.slice(1)].name}: ${a.name}, ${t('орбис')} ${a.orb}°, ${a.applying?t('сходится'):t('расходится')}`))}$('ownerActions').hidden=isShared||r.id==='demo';$('resultMessage').textContent='';}
document.querySelectorAll('.back').forEach(b=>b.onclick=()=>{history.replaceState(null,'',location.pathname);view('landing')});
$('demoBtn').onclick=async()=>{try{render(await api('/api/demo'),false);track('demo_viewed')}catch(e){error(e.message)}};
$('archiveBtn').onclick=async()=>{track('archive_opened');view('archive');$('archiveList').replaceChildren(text('p',t('Загружаем архив…')));try{const rows=await api('/api/archive');$('archiveList').replaceChildren();if(!rows.length)$('archiveList').append(text('p',t('Здесь появятся ваши разборы. Начните с одного вопроса.')));for(const r of rows){const a=text('article','','archive-item');const b=text('button',t('Открыть разбор ↗'));b.onclick=async()=>{try{render(await api('/api/readings/'+r.id),false)}catch(e){$('archiveList').prepend(text('p',e.message,'error'))}};a.append(text('h3',r.question),text('p',`${r.city} · ${new Date(r.created).toLocaleDateString(locale)}`),b);$('archiveList').append(a)}}catch(e){$('archiveList').replaceChildren(text('p',e.message,'error'))}};
$('privacyBtn').onclick=()=>$('privacy').showModal();$('closePrivacy').onclick=()=>$('privacy').close();
async function action(fn){try{await fn()}catch(e){$('resultMessage').textContent=e.message}}
$('shareBtn').onclick=()=>action(async()=>{if(!confirm(t('Ссылка откроет ваш вопрос, ответы на уточнения, город и разбор любому, кому вы её передадите. Создать ссылку?')))return;const {token}=await api(`/api/readings/${current.id}/share`,{method:'POST'});track('share_created');const url=location.origin+'/'+language+'#share='+token;$('resultMessage').replaceChildren(text('span',t('Ссылка создана: ')));const a=text('a',url);a.href=url;$('resultMessage').append(a);try{await navigator.clipboard.writeText(url);$('resultMessage').prepend(text('span',t('Скопировано. ')))}catch{}});
$('revokeBtn').onclick=()=>action(async()=>{await api(`/api/readings/${current.id}/share`,{method:'DELETE'});$('resultMessage').textContent=t('Публичная ссылка отозвана.')});
$('deleteBtn').onclick=()=>action(async()=>{if(!confirm(t('Удалить разбор и его публичную ссылку?')))return;await api('/api/readings/'+current.id,{method:'DELETE'});$('archiveBtn').click()});
for(const [id,value] of [['yesBtn',1],['noBtn',0]])$(id).onclick=()=>action(async()=>{await api(`/api/readings/${current.id}/feedback`,{method:'POST',body:JSON.stringify({value})});track('feedback_sent',{feedback:value?'yes':'no'});$('resultMessage').textContent=t('Спасибо! Отзыв сохранён.')});
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000)}
$('exportBtn').onclick=()=>download(new Blob([JSON.stringify(current,null,2)],{type:'application/json'}),'horary-'+current.id+'.json');
$('pngBtn').onclick=()=>action(async()=>{const img=new Image(),url=URL.createObjectURL(new Blob([current.export_svg||current.svg],{type:'image/svg+xml'}));try{await new Promise((ok,no)=>{img.onload=ok;img.onerror=no;img.src=url});const c=document.createElement('canvas');const ratio=img.naturalHeight/img.naturalWidth;c.width=Math.min(2000,Math.floor(Math.sqrt(14000000/ratio)));c.height=Math.round(c.width*ratio);c.getContext('2d').drawImage(img,0,0,c.width,c.height);c.toBlob(b=>{if(b){download(b,'horary-chart.png');track('chart_downloaded')}},'image/png')}finally{URL.revokeObjectURL(url)}});
if(location.hash.startsWith('#share=')){const token=location.hash.slice(7);api('/api/shared',{method:'POST',body:JSON.stringify({token})}).then(r=>render(r,true)).catch(e=>{view('archive');$('archiveList').replaceChildren(text('p',e.message,'error'))})}
api('/api/status').then(s=>{$('dailyLimitNote').textContent=t('♧ Вопрос приватный · до {limit} попыток за 24 часа',{limit:s.daily_limit});servicePaused=!s.ready;updateButtons();if(s.paused){error(t('Новые ИИ-разборы временно на паузе. Пока можно посмотреть пример и открыть архив.'));$('submitBtn').disabled=true;$('submitBtn').textContent=t('ИИ-разборы скоро вернутся')}}).catch(()=>{});

$('expandChartBtn').onclick=()=>{$('largeChart').innerHTML=current.export_svg||current.svg;$('chartDialog').showModal()};
$('closeChartBtn').onclick=()=>$('chartDialog').close();
$('dialogPngBtn').onclick=()=>$('pngBtn').click();
$('svgBtn').onclick=()=>download(new Blob([current.export_svg||current.svg],{type:'image/svg+xml'}),'horary-chart.svg');

function renderEvents(r){
  $('degreeScale').innerHTML=r.scale_svg||'';
  const events=r.data.events;
  $('eventsSelection').textContent=events?events.selection:t('Таблицы пока недоступны.');
  const zodiac=['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓'];
  for(const key of ['past','future']){
    const target=$(key+'Events');target.replaceChildren();
    for(const e of events?.[key]||[]){
      const minute=Math.round((e.longitude%360)*60)%21600;
      const pos=e.kind==='ingress'?'→ '+zodiac[e.sign]:`${Math.floor(minute%1800/60)}° ${zodiac[Math.floor(minute/1800)]} ${String(minute%60).padStart(2,'0')}′`;
      const date=new Intl.DateTimeFormat(locale,{timeZone:'UTC',year:'2-digit',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(e.time));
      const tr=document.createElement('tr');
      for(const v of [date,e.label,pos,(e.days>=0?'+':'')+e.days.toFixed(2)])tr.append(text('td',v));
      target.append(tr);
    }
    if(events?.missing?.[key]) $('eventsSelection').textContent+=' '+t('{side} карты: {count} событий не найдено в пределах поиска.',{side:key==='past'?t('До'):t('После'),count:events.missing[key]});
  }
}

const topicExamples={"relationships": "Например: как посмотреть на перспективу отношений с моим партнёром?", "career": "Например: как посмотреть на перспективы моей новой работы?", "home": "Например: как посмотреть на обустройство моего нового дома?", "study": "Например: как посмотреть на моё обучение в университете?", "travel": "Например: как посмотреть на мою предстоящую поездку за границу?", "friendship": "Например: как посмотреть на общение с моим близким другом?"};
document.querySelectorAll('.example-topic').forEach(button=>button.addEventListener('click',()=>{ if($('question').value.trim()){$('question').placeholder=t(topicExamples[button.dataset.topic]);}else{$('question').value=t(topicExamples[button.dataset.topic]).replace(/^(Например: |For example: )/,'');$('question').dispatchEvent(new Event('input'));} $('question').focus(); }));
