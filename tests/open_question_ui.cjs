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
 replies.push(new Error('offline'));await submit();
 assert.equal(requests.length,1);
 assert.equal(requests[0].question,'Will things work out?');
 assert.equal(requests[0].clarifications,undefined);
 assert.equal(requests[0].topic,undefined);
 assert.equal(get('question').value,'Will things work out?');
 assert.equal(get('question').readOnly,false);
 assert.equal(get('submitBtn').disabled,false);
 assert.equal(get('formError').hidden,false);
 console.log('Open-question UI: direct submission, no clarification, draft retained on error');
})().catch(e=>{console.error(e);process.exitCode=1});
