const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const code=fs.readFileSync('static/analytics.js','utf8');
function run(environment,choice){
 const scripts=[],nodes=[];
 const element=()=>({dataset:{},append(){},setAttribute(){},focus(){},hidden:false});
 const doc={currentScript:{dataset:{environment,version:'abc123'}},documentElement:{lang:'en'},title:'Ask Horary',referrer:'https://example.com/private?secret=1',head:{appendChild:s=>scripts.push(s.src)},body:{append:n=>nodes.push(n)},createElement:element,querySelector:()=>({append(){}}),getElementById:()=>({})};
 const ctx={document:doc,location:{hostname:'www.askhorary.app',origin:'https://www.askhorary.app',href:'https://www.askhorary.app/en?question=PRIVATE#share=SECRET',hash:'',reload(){}},localStorage:{getItem:()=>choice,setItem(){}},URL,Set,Intl};ctx.window=ctx;vm.runInNewContext(code,ctx);return {ctx,scripts};
}
test('preview and declined users send nothing',()=>{for(const [env,choice] of [['preview','yes'],['production','no'],['production',null]]){const {ctx,scripts}=run(env,choice);ctx.HoraryAnalytics.track('reading_completed');assert.equal(scripts.length,0);assert.equal(ctx.dataLayer,undefined);}});
test('consented events strip private fields and URL fragments',()=>{const {ctx,scripts}=run('production','yes');assert.equal(scripts.length,3);ctx.HoraryAnalytics.track('reading_completed',{question:'PRIVATE',city:'PRIVATE',duration_ms:25});ctx.HoraryAnalytics.track('secret_unknown',{question:'PRIVATE'});const data=JSON.stringify(ctx.dataLayer);assert(!data.includes('PRIVATE'));assert(!data.includes('SECRET'));assert(!data.includes('secret_unknown'));assert(!data.includes('/private'));assert(data.includes('reading_completed'));assert(data.includes('abc123'));});
