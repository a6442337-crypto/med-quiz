// 빌드 결과를 브라우저로 열어 오류가 없는지 확인한다.
//   node tools/smoke.js            (저장소 루트에서; 임시 웹서버를 직접 띄움)
// 홈 → 과목마다: 시작 → 첫 문항 답 고르기 → 해설 표시 확인. 콘솔 오류가 있으면 exit 1.
const {chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const root=path.resolve(__dirname,'..');
const srv=http.createServer((q,r)=>{let p=decodeURIComponent(q.url.split('?')[0]);if(p.endsWith('/'))p+='index.html';
 fs.readFile(path.join(root,p),(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':p.endsWith('.html')?'text/html; charset=utf-8':'application/octet-stream'});r.end(d)})}).listen(0);
(async()=>{const port=srv.address().port;const b=await chromium.launch();const pg=await b.newPage();const errs=[];
 pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error'&&!/fonts|favicon|404/.test(m.text()))errs.push(m.text())});
 await pg.goto(`http://localhost:${port}/`);const slugs=await pg.$$eval('.card h2 a',a=>a.map(x=>x.getAttribute('href')));
 for(const s of slugs){await pg.goto(`http://localhost:${port}/${s}`);await pg.click('[data-k="all"]');await pg.click('#start');
  await pg.click('.opt >> nth=0');const ok=await pg.$('.ex');console.log(s,ok?'OK':'해설 없음');if(!ok)errs.push(s+' 해설 표시 실패');
  const pdf=await pg.$('a.pdf');if(pdf){const h=await pdf.getAttribute('href');if(!fs.existsSync(path.join(root,s,decodeURIComponent(h))))errs.push(s+' PDF 링크 깨짐')}}
 await b.close();srv.close();if(errs.length){console.log('오류',errs);process.exit(1)}console.log('smoke OK',slugs.length,'과목')})();
