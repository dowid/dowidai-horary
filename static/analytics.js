(() => {
  const config=document.currentScript.dataset;
  const live=config.environment==='production' && ['www.askhorary.app','askhorary.app'].includes(location.hostname);
  const language=document.documentElement.lang==='en'?'en':'ru';
  const eventNames=new Set(['landing_view','question_started','city_selected','reading_submitted','reading_completed','reading_failed','demo_viewed','archive_opened','share_created','shared_reading_viewed','feedback_sent','chart_downloaded','voice_started','voice_completed','voice_failed']);
  const cleanURL=value=>{try{const u=new URL(value,location.origin);return u.origin+u.pathname;}catch{return '';}};
  const referrer=(()=>{try{return new URL(document.referrer).origin+'/';}catch{return '';}})();
  let allowed=false,started=false;
  const key='askhorary.analytics';
  function load(src){const s=document.createElement('script');s.src=src;s.defer=true;document.head.appendChild(s);}
  function track(name,details={}){
    if(!live||!allowed||!eventNames.has(name))return;
    const data={language,app_version:config.version,environment:'production',page_location:cleanURL(location.href),page_referrer:referrer,page_title:document.title};
    if(Number.isFinite(details.duration_ms))data.duration_ms=Math.max(0,Math.round(details.duration_ms));
    if(['network','validation','rate_limit','server','unknown'].includes(details.error_type))data.error_type=details.error_type;
    if(['yes','no'].includes(details.feedback))data.feedback=details.feedback;
    window.gtag('event',name,data);
  }
  window.HoraryAnalytics={track};
  if(!live)return;
  const english=language==='en';
  function start(){
    if(started)return;started=true;allowed=true;
    window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments);};
    window.si=window.si||function(){(window.siq=window.siq||[]).push(arguments);};
    const before=e=>({...e,url:cleanURL(e.url)});
    window.va('beforeSend',before);window.si('beforeSend',before);
    load('/_vercel/insights/script.js');load('/_vercel/speed-insights/script.js');
    window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments);};
    window.gtag('consent','default',{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
    window.gtag('js',new Date());
    window.gtag('config','G-ZH7Z2S8T3L',{send_page_view:false,allow_google_signals:false,allow_ad_personalization_signals:false,page_location:cleanURL(location.href),page_referrer:referrer,page_title:document.title});
    load('https://www.googletagmanager.com/gtag/js?id=G-ZH7Z2S8T3L');
    window.gtag('event','page_view',{page_location:cleanURL(location.href),page_referrer:referrer,page_title:document.title,language,app_version:config.version,environment:'production'});
    if(document.getElementById('questionForm')&&!location.hash.startsWith('#share='))track('landing_view');
  }
  const panel=document.createElement('section');panel.className='analytics-consent';panel.setAttribute('aria-label',english?'Analytics preferences':'Настройки аналитики');
  const message=document.createElement('p');message.textContent=english?'Allow usage and speed analytics (Google Analytics and Vercel)? Your questions, answers and city are never sent. You can change this choice in the footer.':'Разрешить аналитику посещений и скорости (Google Analytics и Vercel)? Вопросы, ответы и город не передаются. Выбор можно изменить внизу страницы.';
  function choose(value){try{localStorage.setItem(key,value);}catch{}panel.hidden=true;if(value==='yes')start();else{allowed=false;if(started)location.reload();}}
  const yes=document.createElement('button');yes.textContent=english?'Allow':'Разрешить';yes.onclick=()=>choose('yes');
  const no=document.createElement('button');no.textContent=english?'Decline':'Отказаться';no.onclick=()=>choose('no');
  const info=document.createElement('a');info.href='https://policies.google.com/technologies/partner-sites';info.target='_blank';info.rel='noopener noreferrer';info.textContent=english?'How Google uses data':'Как Google использует данные';
  panel.append(message,yes,no,info);document.body.append(panel);
  const settings=document.createElement('button');settings.className='text-btn';settings.textContent=english?'Analytics settings':'Настройки аналитики';settings.onclick=()=>{panel.hidden=false;yes.focus();};(document.querySelector('footer')||document.body).append(settings);
  let choice;try{choice=localStorage.getItem(key);}catch{}if(choice){panel.hidden=true;if(choice==='yes')start();}
})();
