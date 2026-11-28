// 빌드 결과를 브라우저로 열어 오류가 없는지 확인한다.
//   node tools/smoke.js            (저장소 루트에서; 임시 웹서버를 직접 띄움)
// 홈 → 과목마다: (모의시험이 있으면 구성 검사·제출) 시작 → 첫 문항 답 고르기 → 해설 표시 확인 (주관식이 있으면 주관식도 한 문항). 그림 누락 문항이 있으면 맨 아래 안내 확인. 콘솔 오류가 있으면 exit 1.
const {chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const root=path.resolve(__dirname,'..');
const srv=http.createServer((q,r)=>{let p=decodeURIComponent(q.url.split('?')[0]);if(p.endsWith('/'))p+='index.html';
 fs.readFile(path.join(root,p),(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':p.endsWith('.html')?'text/html; charset=utf-8':'application/octet-stream'});r.end(d)})}).listen(0);
(async()=>{const port=srv.address().port;const b=await chromium.launch();const pg=await b.newPage();const errs=[];
 pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error'&&!/fonts|favicon|404/.test(m.text()))errs.push(m.text())});
 await pg.goto(`http://localhost:${port}/`);const slugs=await pg.$$eval('.card h2 a',a=>a.map(x=>x.getAttribute('href')));
 for(const s of slugs){await pg.goto(`http://localhost:${port}/${s}`);await pg.click('[data-k="all"]');const hasS=await pg.$('[data-f="s"]');if(hasS)await pg.click('[data-f="mc"]');await pg.click('#start');
  await pg.click('.opt >> nth=0');const ok=await pg.$('.ex');console.log(s,ok?'OK':'해설 없음');if(!ok)errs.push(s+' 해설 표시 실패');
  if(hasS){/* 주관식: 답 입력 → 답 확인 → 정답·채점 버튼 → '맞음'으로 바꾸기 */
   await pg.click('#home');await pg.click('[data-f="s"]');await pg.click('#start');await pg.fill('#sa','테스트 답');await pg.click('#chk');
   const sx=await pg.$('.ex .ans');await pg.click('[data-g="1"]');const on=await pg.$('[data-g="1"].on');
   console.log(s,'주관식',sx&&on?'OK':'실패');if(!(sx&&on))errs.push(s+' 주관식 채점 실패');await pg.click('#home');await pg.click('[data-f="all"]')}
  if(await pg.$('#mock')){/* 모의시험: 계획대로 뽑히는지(20회) → 시작 → 답 고르기 → 마지막 문항에서 제출 → 결과·해설 */
   const bad=await pg.evaluate(()=>{const e=[];for(let t=0;t<20;t++){const q=mockBuild();if(q.length!==D.mock.total)e.push('총 '+q.length);if(new Set(q.map(x=>x.id)).size!==q.length)e.push('중복');
     for(const r of D.mock.profs){const n=q.filter(x=>r.ch.includes(x.ch)).length;if(n!==r.n)e.push(r.prof+' '+n+'/'+r.n)}}return [...new Set(e)]});
   if(bad.length)errs.push(s+' 모의시험 구성 '+bad.join(', '));
   await pg.click('#mock');const sel=await pg.$('.opt');if(sel){await sel.click();if(!(await pg.$('.opt.sel')))errs.push(s+' 모의시험 선택 표시 없음');if(await pg.$('.ex'))errs.push(s+' 모의시험 중 해설 노출')}
   await pg.click('#gd summary');await pg.click('.grid button >> nth=-1');await pg.click('#sub');await pg.click('#cfok');
   const sc=await pg.$('.mock .score');await pg.click('#rv');const ex=await pg.$('.ex');
   console.log(s,'모의시험',bad.length?'구성 오류':'구성 OK',sc&&ex?'제출·해설 OK':'실패');if(!(sc&&ex))errs.push(s+' 모의시험 제출 실패');
   await pg.click('#home');if(await pg.$('#mockre'))errs.push(s+' 제출 후 진행 기록이 남음')}
  const mf=JSON.parse(fs.readFileSync(path.join(root,s,'card.json'))).missing_figs||{};
  if(Object.keys(mf).length&&!(await pg.$('footer.miss')))errs.push(s+' 그림 누락 안내 없음');
  const sm=await pg.$('a.pdf[href="summary.html"]');if(sm){await sm.click();await pg.waitForSelector('#app details');
   const n=await pg.$$eval('#app details',d=>d.length);await pg.$$eval('#app details',d=>d.forEach(x=>x.open=true));await pg.$$eval('#app img',a=>a.forEach(i=>i.loading='eager'));
   await pg.waitForFunction(()=>[...document.querySelectorAll('#app details[open] img')].every(i=>i.complete),null,{timeout:15000});
   const bad=await pg.$$eval('#app details[open] img',a=>a.filter(i=>!i.naturalWidth).map(i=>i.getAttribute('src')));
   const tb=await pg.$$eval('#app .sheet table',t=>t.length);console.log(s,'요약자료',n,'명 · 표',tb,'개',bad.length?'그림 깨짐':'OK');if(!n)errs.push(s+' 요약자료 비어 있음');if(bad.length)errs.push(s+' 요약자료 그림 깨짐 '+bad);
   await pg.goto(`http://localhost:${port}/${s}`);await pg.click('[data-k="all"]');}
  const pdf=await pg.$('a.pdf[download]');if(pdf){const h=await pdf.getAttribute('href');if(!fs.existsSync(path.join(root,s,decodeURIComponent(h))))errs.push(s+' PDF 링크 깨짐')}}
 await b.close();srv.close();if(errs.length){console.log('오류',errs);process.exit(1)}console.log('smoke OK',slugs.length,'과목')})();
