#!/usr/bin/env python3
"""복원 해설(drive-mcp read_drive_file로 받은 텍스트) → 문항 JSON.

  python3 tools/extract_haeseol.py <출력.json> <파일1.txt> <연도1> [<파일2.txt> <연도2> …]

본 문항 = "답:" 줄 바로 뒤(2줄 안)에 "# 홍길동 교수님" / "# 홍길동p" 표기가 있는 문항.
번호가 1~4씩 증가하는 가장 긴 사슬만 본 문항으로 인정한다(관련 기출의 번호 줄 오인 방지).
본 문항 뒤 "<2021 기출>" 같은 머리글 아래 문항은 그 본 문항의 rel(관련 기출)로 붙는다.
출력: [{year,num,prof,stem[],opts[],imgs[],ans,a(0부터),ex[],rel[{year,num,stem,opts,a,…}]}]
형식이 다른 파일(교수 표기 없는 문제수합 등)은 이 도구로 뽑히지 않는다 → AUTOMATION.md 참고.
"""
import re,json,sys
CIR='①②③④⑤'; ALT={'⓵':'①','⓶':'②','⓷':'③','⓸':'④','⓹':'⑤'}
NUMRE=re.compile(r'^\s*(\d{1,3})\s*$')
ANSRE=re.compile(r'^\s*(?:\[?정답\]?|답)\s*[:：]?\s*(.*)$')
PROFRE=re.compile(r'^#\s*([가-힣]{2,4})\s*(?:교수님|[pP])')
YRE=re.compile(r'<\s*(?:20)?(\d{2})\s*(?:년도?)?\s*(?:-?\s*\dQ)?\s*기출')
def norm_ans(s):
    s=s.strip()
    for c in s:
        if c in CIR: return CIR.index(c)
        if c in '12345': return int(c)-1
    return None
def lines_of(path):
    out=[]
    for l in open(path).read().split('\n'):
        if re.match(r'^# .*\(학과 공유 드라이브\) — \d+/\d+부',l) or not l.strip(): continue
        for a,b in ALT.items(): l=l.replace(a,b)
        out.append(l.rstrip())
    return out
def block(L,k,j):
    """L[k]=번호줄, L[j]=답줄 → stem, opts, imgs"""
    stem,opts,imgs=[],[],[]
    for b in L[k+1:j]:
        b2=b.strip()
        m=re.match(r'^(?:([①②③④⑤])|([1-5])\))\s*(.*)$',b2)
        im=re.match(r'\[그림 #(\d+)\]',b2)
        if im: imgs.append(int(im.group(1)))
        elif m: opts.append(m.group(3).strip())
        elif opts: opts[-1]+=' '+b2
        else: stem.append(b2)
    return stem,opts,imgs
def extract(path,year):
    L=lines_of(path); mains=[]; cur=None; yr=None
    for j,l in enumerate(L):
        ym=YRE.search(l)
        if ym: yr=2000+int(ym.group(1))
        m=ANSRE.match(l)
        if not m: continue
        k=j-1
        while k>0 and not NUMRE.match(L[k]) and j-k<60: k-=1
        if not NUMRE.match(L[k]): continue
        num=int(L[k]); stem,opts,imgs=block(L,k,j)
        prof=None
        for kk in range(j+1,min(j+3,len(L))):
            pm=PROFRE.match(L[kk].strip())
            if pm: prof=pm.group(1); pk=kk; break
        q=dict(num=num,stem=stem,opts=opts,imgs=imgs,ans=m.group(1).strip(),a=norm_ans(m.group(1)))
        if prof:
            ex=[];kk=pk+1
            while kk<len(L) and not re.match(r'^\s*(관련 이론|관련 기출|<)',L[kk]) and not NUMRE.match(L[kk]):
                ex.append(L[kk].strip()); kk+=1
            q.update(year=year,prof=prof,ex=ex,rel=[]); mains.append(q); cur=q; yr=None
        elif cur is not None and yr and yr<year:
            q['year']=yr; cur['rel'].append(q)
    # 번호가 1~4씩 증가하는 가장 긴 사슬만 본 문항으로 인정, 나머지 후보의 관련 기출은 앞 문항에 붙임
    n=len(mains); best=[1]*n; prev=[-1]*n
    for i in range(n):
        for j in range(i):
            if 0<mains[i]['num']-mains[j]['num']<=4 and best[j]+1>best[i]: best[i]=best[j]+1; prev[i]=j
    if not n: return []
    i=max(range(n),key=lambda x:best[x]); keep=set()
    while i>=0: keep.add(i); i=prev[i]
    out=[]
    for i,q in enumerate(mains):
        if i in keep: out.append(q)
        elif out: out[-1]['rel']+=q['rel']
    return out
if __name__=='__main__':
    out=[]
    for p,y in zip(sys.argv[2::2],sys.argv[3::2]): out+=extract(p,int(y))
    json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False,indent=0)
    import collections
    print(collections.Counter((q['year'],len(q['opts'])>=4) for q in out))
    print(collections.Counter(r['year'] for q in out for r in q['rel'] if len(r['opts'])>=4))
