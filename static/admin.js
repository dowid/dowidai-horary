(() => {
  const $ = id => document.getElementById(id);
  const count = n => Number(n).toLocaleString('ru-RU');
  const node = (tag, text) => {const el=document.createElement(tag);el.textContent=text;return el;};
  const messages = {'Report not found.':'Разбор удалён или не найден.','Incorrect password.':'Неверный пароль.','Too many sign-in attempts. Wait 15 minutes.':'Слишком много попыток. Подождите 15 минут.','Admin access is not configured.':'Доступ администратора ещё не настроен.','Sign in to view statistics.':'Войдите, чтобы посмотреть статистику.'};
  async function api(path, body) {
    const r=await fetch('/api/admin/'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    const data=await r.json();
    if(!r.ok){const err=Error(messages[data.detail]||'Не удалось загрузить данные. Попробуйте ещё раз.');err.status=r.status;throw err;}
    return data;
  }
  function authenticated(value){$('adminLogin').hidden=value;$('dashboard').hidden=!value;$('logout').hidden=!value;if(!value)$('questionsList').replaceChildren();}
  function fail(e){$('adminError').textContent=e.message;$('adminError').hidden=false;}
  function breakdown(id, rows, labels={}){
    const target=$(id);target.replaceChildren();
    if(!rows.length){target.append(node('p','Пока нет данных'));return;}
    for(const row of rows){const line=node('p','');line.className='admin-breakdown';line.append(node('span',labels[row.label]||row.label),node('strong',count(row.count)));target.append(line);}
  }
  function render(data){
    const t=data.totals;
    const costs=data.costs,money=value=>value==null?'Нет данных':new Intl.NumberFormat('ru-RU',{style:'currency',currency:'USD',minimumFractionDigits:4,maximumFractionDigits:6}).format(value);
    const costValues=[['Все сохранённые разборы',costs.included_reports?costs.estimated_total_usd:null],['Текущий месяц · UTC',costs.included_reports?costs.estimated_month_usd:null],['В среднем на разбор',costs.estimated_average_usd]];
    $('costMetrics').replaceChildren(...costValues.map(([label,value])=>{const card=node('article','');card.className='admin-metric';card.append(node('span',label),node('strong',money(value)));return card;}));
    $('costCoverage').textContent=`Учтено разборов: ${costs.included_reports}. Без данных о токенах или известного тарифа: ${costs.excluded_reports}. Тарифы проверены ${costs.rates_checked}.`;
    $('costModels').replaceChildren(...costs.models.map(row=>{const p=node('p','');p.className='admin-breakdown';p.append(node('span',row.model),node('strong',money(row.estimated_usd)));return p;}));
    const values=[['За 24 часа',t.last_24h],['За 7 дней',t.last_7d],['Всего сохранено',t.reports],['Браузерных архивов',t.browser_archives],['Публичных ссылок',t.shared],['Полезно / не полезно',count(t.helpful)+' / '+count(t.not_helpful)],['Входных токенов',t.input_tokens],['Выходных токенов',t.output_tokens]];
    $('metrics').replaceChildren(...values.map(([label,value])=>{const card=node('article','');card.className='admin-metric';card.append(node('span',label),node('strong',typeof value==='string'?value:count(value)));return card;}));
    $('updated').textContent='Обновлено: '+new Date(data.generated_at*1000).toLocaleString('ru-RU');
    breakdown('languages',data.languages,{ru:'Русский',en:'English'});breakdown('topics',data.topics,{career:'Работа',relationships:'Отношения',home:'Дом и переезд',study:'Учёба',travel:'Путешествия',friendship:'Друзья'});breakdown('models',data.models);
    const q=data.quota;$('quotaText').textContent=`${q.month}: ${count(q.reservations)} из ${q.limit} вызовов · резерв $${(q.reservations*q.reserve_per_call).toFixed(2)} · осталось ${Math.max(0,q.limit-q.reservations)} вызовов`;$('quotaBar').value=q.reservations;
    $('dailyRows').replaceChildren(...data.daily.map(d=>{const tr=node('tr','');tr.append(node('td',d.day),node('td',count(d.reports)));return tr;}));
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 960 230');svg.setAttribute('role','img');svg.setAttribute('aria-label','Сохранённые разборы за последние 30 дней; точные значения в таблице ниже.');
    const max=Math.max(1,...data.daily.map(d=>d.reports));
    data.daily.forEach((d,i)=>{const h=160*d.reports/max,rect=document.createElementNS(ns,'rect');for(const [k,v] of Object.entries({x:10+i*31,y:180-h,width:22,height:Math.max(h,1),rx:3,fill:d.reports?'#397455':'#dde3d8'}))rect.setAttribute(k,v);const title=document.createElementNS(ns,'title');title.textContent=d.day+': '+d.reports;rect.append(title);svg.append(rect);if(i%5===0||i===29){const text=document.createElementNS(ns,'text');text.setAttribute('x',10+i*31);text.setAttribute('y','210');text.setAttribute('font-size','12');text.textContent=d.day.slice(5);svg.append(text);}});
    $('dailyChart').replaceChildren(svg);
  }
  let questionsPage=1;
  async function loadQuestions(page=1){
    $('questionsPrev').disabled=true;$('questionsNext').disabled=true;
    $('questionsStatus').textContent='Загружаем вопросы…';
    try{
      const data=await api('questions?page='+page);questionsPage=data.page;
      $('questionsList').replaceChildren();
      for(const row of data.items){
        const card=node('article','');card.className='admin-question';
        const title=node('h3',row.question);
        const meta=node('p',new Date(row.created).toLocaleString('ru-RU')+' · '+row.city+' · '+row.language.toUpperCase()+' · '+row.model);meta.className='hint';
        const details=node('details',''),summary=node('summary','Посмотреть ответ'),body=node('div','');
        details.append(summary,body);let loaded=false;
        details.addEventListener('toggle',async()=>{
          if(!details.open||loaded)return;loaded=true;body.textContent='Загружаем ответ…';
          try{
            const report=await api('questions/'+encodeURIComponent(row.id)),answer=report.answer;
            body.replaceChildren();
            if(!answer){body.append(node('p','Сохранённый ответ отсутствует.'));return;}
            body.append(node('p',answer.summary||''));
            for(const factor of answer.factors||[])body.append(node('p',factor.text||''));
            if(answer.reflection)body.append(node('p',answer.reflection));
          }catch(e){body.textContent=e.message;loaded=false;if(e.status===401)authenticated(false);}
        });
        card.append(title,meta,details);$('questionsList').append(card);
      }
      $('questionsStatus').textContent=data.items.length?'':'Пока нет сохранённых вопросов.';
      $('questionsPage').textContent='Страница '+page;
      $('questionsPrev').disabled=page===1;$('questionsNext').disabled=!data.has_more;
    }catch(e){$('questionsStatus').textContent=e.message;if(e.status===401)authenticated(false);}
  }
  $('questionsPrev').onclick=()=>loadQuestions(questionsPage-1);
  $('questionsNext').onclick=()=>loadQuestions(questionsPage+1);
  async function load(){
    $('adminError').hidden=true;$('refresh').disabled=true;$('adminStatus').textContent='Загружаем статистику…';
    try{const data=await api('stats');render(data);authenticated(true);await loadQuestions();}
    catch(e){if(e.status===401)authenticated(false);else{authenticated(false);fail(e);}}
    finally{$('refresh').disabled=false;$('adminStatus').textContent='';}
  }
  $('adminLogin').onsubmit=async e=>{e.preventDefault();$('loginButton').disabled=true;$('adminError').hidden=true;try{await api('login',{password:$('password').value});$('password').value='';await load();}catch(e){fail(e);}finally{$('loginButton').disabled=false;}};
  $('logout').onclick=async()=>{try{await api('logout',{});authenticated(false);$('metrics').replaceChildren();$('questionsList').replaceChildren();}catch(e){fail(e);}};
  $('refresh').onclick=load;load();
})();
