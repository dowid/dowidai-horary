(() => {
  const $ = id => document.getElementById(id);
  const count = n => Number(n).toLocaleString('ru-RU');
  const node = (tag, text) => {const el=document.createElement(tag);el.textContent=text;return el;};
  const messages = {'Incorrect password.':'Неверный пароль.','Too many sign-in attempts. Wait 15 minutes.':'Слишком много попыток. Подождите 15 минут.','Admin access is not configured.':'Доступ администратора ещё не настроен.','Sign in to view statistics.':'Войдите, чтобы посмотреть статистику.'};
  async function api(path, body) {
    const r=await fetch('/api/admin/'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    const data=await r.json();
    if(!r.ok){const err=Error(messages[data.detail]||'Не удалось загрузить данные. Попробуйте ещё раз.');err.status=r.status;throw err;}
    return data;
  }
  function authenticated(value){$('adminLogin').hidden=value;$('dashboard').hidden=!value;$('logout').hidden=!value;}
  function fail(e){$('adminError').textContent=e.message;$('adminError').hidden=false;}
  function breakdown(id, rows, labels={}){
    const target=$(id);target.replaceChildren();
    if(!rows.length){target.append(node('p','Пока нет данных'));return;}
    for(const row of rows){const line=node('p','');line.className='admin-breakdown';line.append(node('span',labels[row.label]||row.label),node('strong',count(row.count)));target.append(line);}
  }
  function render(data){
    const t=data.totals;
    const values=[['За 24 часа',t.last_24h],['За 7 дней',t.last_7d],['Всего сохранено',t.reports],['Браузерных архивов',t.browser_archives],['Публичных ссылок',t.shared],['Полезно / не полезно',count(t.helpful)+' / '+count(t.not_helpful)],['Входных токенов',t.input_tokens],['Выходных токенов',t.output_tokens]];
    $('metrics').replaceChildren(...values.map(([label,value])=>{const card=node('article','');card.className='admin-metric';card.append(node('span',label),node('strong',typeof value==='string'?value:count(value)));return card;}));
    $('updated').textContent='Обновлено: '+new Date(data.generated_at*1000).toLocaleString('ru-RU');
    breakdown('languages',data.languages,{ru:'Русский',en:'English'});breakdown('topics',data.topics,{career:'Работа',relationships:'Отношения'});breakdown('models',data.models);
    const q=data.quota;$('quotaText').textContent=`${q.month}: ${count(q.reservations)} из ${q.limit} вызовов · резерв $${(q.reservations*q.reserve_per_call).toFixed(2)} · осталось ${Math.max(0,q.limit-q.reservations)} вызовов`;$('quotaBar').value=q.reservations;
    $('dailyRows').replaceChildren(...data.daily.map(d=>{const tr=node('tr','');tr.append(node('td',d.day),node('td',count(d.reports)));return tr;}));
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 960 230');svg.setAttribute('role','img');svg.setAttribute('aria-label','Сохранённые разборы за последние 30 дней; точные значения в таблице ниже.');
    const max=Math.max(1,...data.daily.map(d=>d.reports));
    data.daily.forEach((d,i)=>{const h=160*d.reports/max,rect=document.createElementNS(ns,'rect');for(const [k,v] of Object.entries({x:10+i*31,y:180-h,width:22,height:Math.max(h,1),rx:3,fill:d.reports?'#397455':'#dde3d8'}))rect.setAttribute(k,v);const title=document.createElementNS(ns,'title');title.textContent=d.day+': '+d.reports;rect.append(title);svg.append(rect);if(i%5===0||i===29){const text=document.createElementNS(ns,'text');text.setAttribute('x',10+i*31);text.setAttribute('y','210');text.setAttribute('font-size','12');text.textContent=d.day.slice(5);svg.append(text);}});
    $('dailyChart').replaceChildren(svg);
  }
  async function load(){
    $('adminError').hidden=true;$('refresh').disabled=true;$('adminStatus').textContent='Загружаем статистику…';
    try{const data=await api('stats');render(data);authenticated(true);}
    catch(e){if(e.status===401)authenticated(false);else{authenticated(false);fail(e);}}
    finally{$('refresh').disabled=false;$('adminStatus').textContent='';}
  }
  $('adminLogin').onsubmit=async e=>{e.preventDefault();$('loginButton').disabled=true;$('adminError').hidden=true;try{await api('login',{password:$('password').value});$('password').value='';await load();}catch(e){fail(e);}finally{$('loginButton').disabled=false;}};
  $('logout').onclick=async()=>{try{await api('logout',{});authenticated(false);$('metrics').replaceChildren();}catch(e){fail(e);}};
  $('refresh').onclick=load;load();
})();
