const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const nodes=new Map();
function element(){return {value:'',hidden:true,checked:true,children:[],handlers:{},addEventListener(k,fn){this.handlers[k]=fn},setCustomValidity(){},setAttribute(){},focus(){},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v}}}
const get=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)};
let replies=[],requests=[];
const ctx=vm.createContext({window:{HoraryI18n:{t:s=>s,language:'ru',locale:'ru'},scrollTo(){}},document:{getElementById:get,addEventListener(){},dispatchEvent(){},querySelectorAll(){return []},createElement:element},location:{hash:''},performance:{now:()=>0},setTimeout,clearTimeout,Event:class{},fetch:async(path,opt)=>{if(path==='/api/status')return {ok:true,json:async()=>({ready:true,daily_limit:10})};requests.push(JSON.parse(opt.body));const result=replies.shift();if(result instanceof Error)throw result;return {ok:true,json:async()=>result}}});
vm.runInContext(fs.readFileSync('static/app.js','utf8'),ctx);
(async()=>{
 vm.runInContext("city={id:'test'}",ctx);get('question').value='Will things work out?';
 const submit=()=>get('questionForm').onsubmit({preventDefault(){}});
 replies.push({status:'clarify',message:'Which situation?',continuation:'one'});await submit();
 assert.equal(get('clarification').hidden,false);
 await submit();assert.equal(requests.length,1,'empty reply must not call server');
 get('clarificationAnswer').value='My job';replies.push(new Error('offline'));await submit();
 assert.equal(get('clarificationAnswer').value,'My job');assert.equal(get('clarification').hidden,false);
 replies.push({status:'clarify',message:'Current or new job?',continuation:'two'});await submit();
 assert.equal(requests[2].clarifications.length,1,'retry must not duplicate reply');
 get('clarificationAnswer').value='New job';replies.push({status:'clarify',message:'Which role?',continuation:'three'});await submit();
 assert.equal(requests[3].question,'Will things work out?');assert.equal(requests[3].clarifications.length,2);assert.equal(requests[3].continuation,'two');
 assert.equal(get('question').value,'Will things work out?');
 get('question').handlers.input();assert.equal(get('clarification').hidden,true);
 console.log('Clarification UI: empty reply, retry, history, original question and reset passed');
})().catch(e=>{console.error(e);process.exitCode=1});
