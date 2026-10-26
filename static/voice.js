// Adapted from На берегу: public-assistant-voice, assistant-voice-waveform and public-assistant-wav.
(() => {
  const {t,language}=window.HoraryI18n;
  const el = id => document.getElementById(id);
  let active = null;
  const bars = Array.from({length:28}, (_,i) => {
    const bar = document.createElementNS('http://www.w3.org/2000/svg','rect');
    for (const [key,value] of Object.entries({x:i*8+2,y:14.5,width:3,height:3,rx:1.5})) bar.setAttribute(key,value);
    el('voiceWave').append(bar); return bar;
  });
  function state(value, message) {
    el('voiceStatus').textContent = message;
    el('voiceStart').hidden = value !== 'idle';
    el('voiceStop').hidden = value !== 'recording';
    el('voiceCancel').hidden = value === 'idle';
    el('voiceRecording').hidden = value !== 'recording';
    document.dispatchEvent(new CustomEvent('voicebusy',{detail:value !== 'idle'}));
  }
  function release(s) {
    clearInterval(s.timer); cancelAnimationFrame(s.frame);
    s.stream?.getTracks().forEach(t => t.stop());
    s.source?.disconnect(); s.analyser?.disconnect();
    if(s.context && s.context.state !== 'closed') s.context.close().catch(()=>{});
  }
  function cancel() {
    const s = active; active = null;
    if(s) { s.controller.abort(); release(s); if(s.recorder?.state === 'recording') s.recorder.stop(); }
    el('voiceNotice').hidden = true;
    state('idle',t('Микрофон выключен.'));
  }
  async function waveform(s) {
    try {
      await s.context.resume();
      if(active !== s || s.recorder.state !== 'recording') return;
      s.source = s.context.createMediaStreamSource(s.stream);
      s.analyser = s.context.createAnalyser(); s.analyser.fftSize = 1024;
      s.source.connect(s.analyser);
      const samples = new Float32Array(1024), history = new Array(28).fill(0);
      const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      let last = 0, lastSound = 0;
      function draw(now) {
        if(active !== s || s.recorder.state !== 'recording') return;
        if(now-last >= (reduced ? 400 : 80)) {
          last = now; s.analyser.getFloatTimeDomainData(samples);
          const rms = Math.sqrt(samples.reduce((sum,v)=>sum+v*v,0)/samples.length);
          const level = Number.isFinite(rms) ? Math.sqrt(Math.max(0,Math.min(1,(rms-.001)*35))) : 0;
          if(rms > .003) lastSound = now;
          el('voiceSignal').textContent = s.context.state !== 'running' ? t('Запись идёт, но шкала звука недоступна в этом браузере.') : now-lastSound>1800 ? t('Пока тихо — говорите ближе к микрофону') : rms>.003 ? t('Слышим ваш голос') : t('Говорите — шкала реагирует на ваш голос');
          if(reduced) history.fill(level); else {history.shift();history.push(level);}
          bars.forEach((bar,i)=>{const h=3+25*history[i];bar.setAttribute('height',h);bar.setAttribute('y',(32-h)/2);});
        }
        s.frame = requestAnimationFrame(draw);
      }
      s.frame = requestAnimationFrame(draw);
    } catch { if(active === s) el('voiceSignal').textContent = t('Запись идёт, но шкала звука недоступна в этом браузере.'); }
  }
  function wav(samples) {
    const count = Math.min(samples.length,480000), buffer = new ArrayBuffer(44+count*2), v = new DataView(buffer);
    const word=(offset,text)=>[...text].forEach((c,i)=>v.setUint8(offset+i,c.charCodeAt(0)));
    word(0,'RIFF');v.setUint32(4,buffer.byteLength-8,true);word(8,'WAVE');word(12,'fmt ');
    v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);
    v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);word(36,'data');v.setUint32(40,count*2,true);
    for(let i=0;i<count;i++){const s=Math.max(-1,Math.min(1,samples[i]));v.setInt16(44+i*2,Math.round(s*(s<0?32768:32767)),true);}
    return buffer;
  }
  el('voiceStart').onclick=()=>{el('voiceNotice').hidden=!el('voiceNotice').hidden;};
  el('voiceCancel').onclick=cancel;
  el('voiceStop').onclick=()=>{if(active?.recorder?.state==='recording') active.recorder.stop();};
  el('voiceConfirm').onclick=async()=>{
    if(active) return;
    el('voiceNotice').hidden=true;
    const s={controller:new AbortController()}; active=s;
    const current=()=>active===s;
    state('waiting',t('Разрешите доступ к микрофону…'));
    try {
      if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw Error('unsupported');
      const Context=window.AudioContext||window.webkitAudioContext;
      s.context=new Context(); await s.context.resume();
      if(!current()) {release(s);return;}
      s.stream=await navigator.mediaDevices.getUserMedia({audio:true});
      if(!current()){release(s);return;}
      const type=['audio/webm;codecs=opus','audio/mp4','audio/webm','audio/ogg;codecs=opus'].find(t=>MediaRecorder.isTypeSupported(t));
      s.recorder=new MediaRecorder(s.stream,type?{mimeType:type}:undefined);
      const chunks=[]; let bytes=0;
      s.recorder.ondataavailable=e=>{if(e.data.size){bytes+=e.data.size;chunks.push(e.data);if(bytes>8000000 && current()){cancel();el('voiceStatus').textContent=t('Запись слишком большая. Попробуйте короче.');}}};
      s.recorder.onerror=()=>{if(current()){cancel();el('voiceStatus').textContent=t('Ошибка записи. Микрофон выключен; вопрос можно написать.');}};
      s.recorder.onstop=async()=>{
        release(s); if(!current()) return;
        state('loading',t('Микрофон выключен. Распознаём речь…'));
        let message=t('Микрофон выключен.');
        const timeout=setTimeout(()=>s.controller.abort(),45000);
        try {
          const decoder=new Context(); let decoded;
          try{decoded=await decoder.decodeAudioData(await new Blob(chunks,{type:s.recorder.mimeType}).arrayBuffer());}finally{await decoder.close();}
          if(!current()) return;
          const length=Math.min(Math.floor(decoded.duration*16000),480000);
          if(length<1600) throw Error(t('Запись слишком короткая. Попробуйте ещё раз.'));
          const offline=new OfflineAudioContext(1,length,16000), source=offline.createBufferSource();
          source.buffer=decoded;source.connect(offline.destination);source.start();
          const mono=await offline.startRendering(); if(!current()) return;
          const response=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav','x-voice-consent':'true','X-Horary-Language':language},body:wav(mono.getChannelData(0)),signal:s.controller.signal});
          const result=await response.json(); if(!response.ok) throw Error(result.detail||t('Не удалось распознать речь.'));
          if(!current()) return;
          const question=el('question');
          question.value=[question.value.trim(),result.text].filter(Boolean).join(' ');
          question.dispatchEvent(new Event('input'));window.HoraryAnalytics?.track('voice_completed');
          question.focus();
          message=question.value.length>500?t('Текст добавлен полностью. Сократите вопрос до 500 символов перед отправкой.'):t('Готово. Микрофон выключен. Проверьте текст вопроса перед отправкой.');
        } catch(e) {message=e.name==='AbortError'?t('Распознавание не завершилось вовремя. Вопрос можно написать.'):(e.message||t('Не удалось распознать речь. Вопрос можно написать.'));}
        finally{clearTimeout(timeout);if(current()){active=null;state('idle',message);}}
      };
      s.recorder.start(250);const started=Date.now();
      bars.forEach(bar=>{bar.setAttribute('height',3);bar.setAttribute('y',14.5);});
      window.HoraryAnalytics?.track('voice_started');el('voiceSignal').textContent=t('Говорите — шкала реагирует на ваш голос');
      state('recording',t('Записываем · 0 / 30 с'));waveform(s);
      s.timer=setInterval(()=>{const seconds=Math.floor((Date.now()-started)/1000);el('voiceStatus').textContent=t('Записываем · {seconds} / 30 с',{seconds:Math.min(seconds,30)});if(seconds>=30 && s.recorder.state==='recording') s.recorder.stop();},200);
      el('voiceStop').focus();
    }catch{if(current()){cancel();el('voiceStatus').textContent=t('Микрофон недоступен. Разрешите доступ в настройках браузера или напишите вопрос.');}}
  };
  document.addEventListener('horaryview',cancel);
  window.addEventListener('pagehide',cancel);
  document.addEventListener('visibilitychange',()=>{if(document.hidden) cancel();});
})();
