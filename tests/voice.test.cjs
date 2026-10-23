const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');
function setup(){
 const elements=new Map(),listeners={};let permission,stops=0,frames=[],fetches=0;
 const get=id=>{if(!elements.has(id))elements.set(id,{hidden:false,value:'',textContent:'',children:[],attrs:{},append(x){this.children.push(x)},setAttribute(k,v){this.attrs[k]=v},dispatchEvent(){},focus(){}});return elements.get(id)};
 class Context{constructor(){this.state='running'}async resume(){}async close(){this.state='closed'}createMediaStreamSource(){return {connect(){},disconnect(){}}}createAnalyser(){return {disconnect(){},getFloatTimeDomainData(a){a.fill(.08)}}}}
 class Recorder{static isTypeSupported(){return true}constructor(){this.state='inactive'}start(){this.state='recording'}stop(){this.state='inactive';this.onstop?.()}}
 const document={getElementById:get,createElementNS:()=>({setAttribute(k,v){this[k]=v}}),addEventListener:(k,f)=>listeners[k]=f,dispatchEvent:e=>listeners[e.type]?.(e)};
 const context={document,window:{AudioContext:Context,MediaRecorder:Recorder,addEventListener:(k,f)=>listeners[k]=f},navigator:{mediaDevices:{getUserMedia:()=>new Promise(resolve=>permission=resolve)}},MediaRecorder:Recorder,requestAnimationFrame:f=>{frames.push(f);return frames.length},cancelAnimationFrame(){},matchMedia:()=>({matches:false}),AbortController,CustomEvent:class{constructor(type,init){this.type=type;this.detail=init.detail}},setInterval:()=>1,clearInterval(){},setTimeout,clearTimeout,Date,Float32Array,ArrayBuffer,DataView,fetch:()=>{fetches++}};
 vm.runInNewContext(fs.readFileSync('static/voice.js','utf8'),context);
 return {get,listeners,frames,allow:()=>permission({getTracks:()=>[{stop(){stops++}}]}),stops:()=>stops,fetches:()=>fetches};
}
test('cancelling pending permission closes late stream without recording/upload',async()=>{const s=setup();const start=s.get('voiceConfirm').onclick();await new Promise(setImmediate);s.get('voiceCancel').onclick();s.allow();await start;assert.equal(s.stops(),1);assert.equal(s.fetches(),0);assert.match(s.get('voiceStatus').textContent,/выключен/)});
test('real amplitude changes waves; navigation stops tracks, never uploads',async()=>{const s=setup();const start=s.get('voiceConfirm').onclick();await new Promise(setImmediate);s.allow();await start;assert.match(s.get('voiceStatus').textContent,/Записываем/);assert.equal(s.get('voiceStop').hidden,false);s.frames[0](100);assert.ok(s.get('voiceWave').children[27].height>3);s.listeners.horaryview();assert.equal(s.stops(),2);assert.equal(s.fetches(),0);assert.equal(s.get('voiceWave').hidden,true)});

