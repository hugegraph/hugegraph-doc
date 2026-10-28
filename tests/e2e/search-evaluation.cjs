const {chromium}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),{spawn}=require('node:child_process');
const roots={summary:process.env.RUNNER_TEMP+'/search-summary',content:process.env.RUNNER_TEMP+'/search-content'};
const cases=JSON.parse(fs.readFileSync('../../scripts/fixtures/community_search_queries.json','utf8'));
const report={source:process.env.SOURCE_SHA,environment:{node:process.version,viewport:'1440x900',samples:5,network:'runner loopback; fresh browser context each cold sample; no throttling'},variants:{}};
const servers=[];let browser;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
try{
for(const [variant,port] of [['summary',4173],['content',4176]]){
servers.push(spawn('python3',['serve.py',String(port),'--bind','127.0.0.1','--directory',roots[variant]],{stdio:'ignore'}));
for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:'+port)).ok)break;}catch{}await sleep(250);}
}
browser=await chromium.launch();
const indexes={};
for(const [variant,root] of Object.entries(roots)){
report.variants[variant]={indexes:{},ranking:[],bodyQueries:[],coldFirstSearch:[]};indexes[variant]={};
for(const lang of ['en','cn']){
const name=fs.readdirSync(root).find(n=>n.startsWith('offline-search-index.'+lang+'.')&&n.endsWith('.json'));
if(!name)throw Error('Missing index '+variant+' '+lang);
const raw=fs.readFileSync(path.join(root,name)),rows=JSON.parse(raw);
indexes[variant][lang]=rows;
let samples=[];for(let i=0;i<20;i++){const t=performance.now();JSON.parse(raw.toString());samples.push(performance.now()-t);}
report.variants[variant].indexes[lang]={file:name,rawBytes:raw.length,gzipBytes:zlib.gzipSync(raw).length,entries:rows.length,parseMedianMs:samples.sort((a,b)=>a-b)[10]};
}
}
async function open(variant,lang){
const origin='http://127.0.0.1:'+(variant==='summary'?4173:4176);
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage();
await page.route('**/*',async route=>{
const u=new URL(route.request().url());
if(['https://hugegraph.apache.org','https://hugegraph-oink.staged.apache.org'].includes(u.origin)){
const response=await route.fetch({url:origin+u.pathname+u.search});
await route.fulfill({response,headers:{...response.headers(),'access-control-allow-origin':'*'}});return;
}
if(/\.(png|jpe?g|webp|svg)(\?|$)/i.test(u.pathname)){await route.abort();return;}await route.continue();
});
await page.goto(origin+(lang==='cn'?'/cn/docs/':'/docs/'),{waitUntil:'networkidle'});
return {context,page};
}
async function query(page,q){
const input=page.locator('.td-shell-search__input');
await input.fill(q);
await page.waitForTimeout(650);
return page.locator('#td-shell-search-results .td-shell-search__group').first().locator('[role="option"]').evaluateAll(rows=>rows.slice(0,10).map(r=>({title:r.querySelector('.td-shell-search__item-title')?.textContent.trim(),href:r.getAttribute('href')||r.dataset.tdUrl||null})).filter(r=>r.title));
}
for(const variant of ['summary','content']){
for(const lang of ['en','cn']){
const {page,context}=await open(variant,lang);await page.locator('[data-td-shell-search-open]').first().click();
for(const c of cases.filter(c=>c.expected_ref.startsWith('/cn/')===(lang==='cn'))){
const rows=await query(page,c.query),title=indexes[variant][lang].find(r=>r.ref===c.expected_ref)?.title;
const rank=rows.findIndex(r=>r.title===title||r.title?.startsWith(title+' › '));
report.variants[variant].ranking.push({lang,query:c.query,target:c.expected_ref,rank:rank<0?null:rank+1,top3:rows.slice(0,3)});
}
const candidates=['restserver.connection_max_requests','auth.token_secret','target-trust-store-password','rocksdb.min_write_buffer_number_to_merge','重启后继续有效','全键布隆过滤器','服务端私钥'];
for(const q of candidates){
const targets=indexes.content[lang].filter(r=>r.body?.toLowerCase().includes(q.toLowerCase()));
if(!targets.length)continue;
const rows=await query(page,q);
report.variants[variant].bodyQueries.push({lang,query:q,bodyMatches:targets.length,bodyRefs:targets.map(r=>r.ref),results:rows,matchingRanks:rows.map((r,i)=>targets.some(t=>r.title===t.title||r.title?.startsWith(t.title+' › '))?i+1:null).filter(Boolean)});
}
await context.close();
for(let sample=0;sample<5;sample++){
const {page,context}=await open(variant,lang);
const start=performance.now();
await page.locator('[data-td-shell-search-open]').first().click();
const coldQuery=lang==='cn'?'图计算':'placement driver';
const targetCase=cases.find(c=>c.query.toLowerCase()===coldQuery.toLowerCase()&&c.expected_ref.startsWith('/cn/')===(lang==='cn'));
const targetTitle=indexes[variant][lang].find(r=>r.ref===targetCase.expected_ref).title;
await page.locator('.td-shell-search__input').fill(coldQuery);
await page.waitForFunction(title=>{
const list=document.querySelector('.td-shell-search__list');
if(list?.getAttribute('aria-busy')==='true')return false;
return Array.from(document.querySelectorAll('#td-shell-search-results .td-shell-search__group:first-child [role="option"] .td-shell-search__item-title')).some(r=>r.textContent.trim()===title||r.textContent.trim().startsWith(title+' › '));
},targetTitle,{timeout:15000});
report.variants[variant].coldFirstSearch.push({lang,sample,ms:performance.now()-start});
await context.close();
}
}
}
}finally{if(browser)await browser.close();servers.forEach(s=>s.kill());}
fs.writeFileSync('search-evaluation/results.json',JSON.stringify(report,null,2));
const compact={source:report.source,environment:report.environment,variants:{}};
for(const [variant,r]of Object.entries(report.variants)){
compact.variants[variant]={indexes:r.indexes,ranking:{total:r.ranking.length,top3:r.ranking.filter(x=>x.rank&&x.rank<=3).length,misses:r.ranking.filter(x=>!x.rank||x.rank>3)},bodyQueries:r.bodyQueries.map(x=>({lang:x.lang,query:x.query,bodyMatches:x.bodyMatches,resultCount:x.results.length,matchingRanks:x.matchingRanks})),coldFirstSearch:['en','cn'].map(lang=>{const a=r.coldFirstSearch.filter(x=>x.lang===lang).map(x=>x.ms).sort((a,b)=>a-b);return{lang,samplesMs:a,medianMs:a[2]};})};
}
console.log('SEARCH_EVALUATION_BEGIN');console.log(JSON.stringify(compact));console.log('SEARCH_EVALUATION_END');
})().catch(e=>{console.error(e);process.exitCode=1;});
