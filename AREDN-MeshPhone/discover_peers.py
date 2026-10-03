#!/usr/bin/env python3
import argparse, configparser, html.parser, json, os, re, socket, urllib.request
class Table(html.parser.HTMLParser):
 def __init__(self): super().__init__(); self.rows=[]; self.r=None; self.c=False; self.buf=[]
 def handle_starttag(self,t,a):
  if t=='tr': self.r=[]
  elif self.r is not None and t in ('td','th'): self.c=True; self.buf=[]
 def handle_data(self,d):
  if self.r is not None and self.c: self.buf.append(d)
 def handle_endtag(self,t):
  if t in ('td','th') and self.r is not None and self.c: self.r.append(' '.join(''.join(self.buf).split())); self.c=False
  elif t=='tr' and self.r is not None:
   if self.r: self.rows.append(self.r)
   self.r=None
def clean(v): return re.sub(r'\\s+',' ',v).strip()
def parse_iax(path):
 sections={}; section=None
 for raw in open(path,errors='replace'):
  line=raw.split(';',1)[0].strip()
  if not line: continue
  m=re.match(r'^\\[([^]]+)\\]$',line)
  if m: section=m.group(1).strip(); sections[section]={}; continue
  if section and '=' in line:
   k,v=line.split('=',1); sections[section][k.strip().lower()]=v.strip()
 return sections
def pbx_rows(url):
 p=Table(); p.feed(urllib.request.urlopen(url,timeout=20).read().decode('utf-8','replace')); return p.rows[1:]
def norm(v): return re.sub(r'[^a-z0-9]','',v.lower())
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--iax-config',default='/etc/asterisk/iax_custom.conf'); ap.add_argument('--pbx-list',default='http://n2mh-web.local.mesh/mpadmin/meshphone_pbx_list.php'); ap.add_argument('--local-office',required=True); ap.add_argument('--output'); ap.add_argument('--yes',action='store_true'); args=ap.parse_args()
 rows=pbx_rows(args.pbx_list); pbx=[]
 for r in rows:
  if len(r)<9: continue
  office=clean(r[0]); host=clean(r[8]); ip=clean(r[2]);
  if office and re.fullmatch(r'\\d+',office): pbx.append({'office':office,'host':host,'ip':ip,'location':clean(r[3])})
 peers=[]
 for name,opt in parse_iax(args.iax_config).items():
  host=opt.get('host',''); typ=opt.get('type','');
  if not host or host.lower() in ('dynamic','') or name.lower() in ('general','system'): continue
  peers.append({'peer':name,'host':host,'username':opt.get('username',''),'type':typ})
 result={'local_office':str(args.local_office),'peers':{}}
 print('MeshPhone peer discovery'); print('Local office:',args.local_office); print('IAX peers found:',len(peers)); print()
 unmatched=[]
 for peer in peers:
  candidates=[]; hostnorm=norm(peer['host']); peernorm=norm(peer['peer'])
  try: reverse=socket.gethostbyaddr(peer['host'])[0]; revnorm=norm(reverse)
  except Exception: reverse=''; revnorm=''
  for row in pbx:
   score=0
   if peer['host']==row['ip'] and row['ip']: score=100
   if hostnorm and hostnorm==norm(row['host']): score=max(score,95)
   if peernorm and peernorm in norm(row['host']): score=max(score,80)
   if peernorm and peernorm in revnorm: score=max(score,75)
   if score: candidates.append((score,row))
  candidates.sort(key=lambda x:x[0],reverse=True)
  if candidates and (len(candidates)==1 or candidates[0][0]>candidates[1][0]):
   score,row=candidates[0]; result['peers'][row['office']]={'peer':peer['peer'],'enabled':True}; print('MATCHED',peer['peer'],'host=',peer['host'],'office=',row['office'],'pbx=',row['host'] or row['location'],'confidence=',('high' if score>=95 else 'medium'))
  else:
   unmatched.append(peer); print('UNMATCHED',peer['peer'],'host=',peer['host'],'reason=no unique PBX match')
 print(); print('UNMATCHED COUNT:',len(unmatched))
 if args.output:
  if not args.yes:
   try: answer=input('Write peers.json? [y/N] ').strip().lower()
   except EOFError: answer='n'
   if answer not in ('y','yes'): print('Not written'); return 2
  os.makedirs(os.path.dirname(args.output) or '.',exist_ok=True)
  with open(args.output,'w') as f: json.dump(result,f,indent=2); f.write('\\n')
  print('Wrote',args.output)
 return 0
if __name__=='__main__': raise SystemExit(main())
