#!/usr/bin/env python3
import datetime, json, os, pathlib, subprocess, tempfile
BASE=pathlib.Path('/opt/meshphone-router')
PEERS=BASE/'peers.json'
DISC=BASE/'peers.discovered.json'
STATUS=pathlib.Path('/var/lib/meshphone-router/status.json')
def atomic_json(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='meshphone-',dir=str(path.parent),text=True)
 with os.fdopen(fd,'w') as f: json.dump(data,f,indent=2); f.write('\n')
 os.replace(tmp,path)
def main():
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 status={'ok':False,'updated_at':now,'matched':[],'unmatched':[],'conflicts':[],'error':None}
 try:
  d=subprocess.run([str(BASE/'discover_peers.py'),'--iax-config','/etc/asterisk/iax_custom.conf','--local-office','40423','--output',str(DISC),'--yes'],text=True,capture_output=True,timeout=60)
  if d.returncode: raise RuntimeError('peer discovery failed: '+d.stderr[-1000:])
  discovered=json.load(open(DISC))
  existing=json.load(open(PEERS)) if PEERS.exists() else {'local_office':discovered['local_office'],'peers':{}}
  existing.setdefault('peers',{})
  for office,rec in discovered.get('peers',{}).items():
   old=existing['peers'].get(office)
   if old and old.get('peer') != rec.get('peer'):
    status['conflicts'].append({'office':office,'existing':old.get('peer'),'discovered':rec.get('peer')})
   elif not old:
    existing['peers'][office]=rec
  atomic_json(PEERS,existing)
  route_tmp='/etc/asterisk/meshphone.conf.new'
  r=subprocess.run([str(BASE/'routebuilder.py'),'--config',str(PEERS),'--output',route_tmp],text=True,capture_output=True,timeout=90)
  if r.returncode: raise RuntimeError('route generation failed: '+r.stderr[-1000:])
  os.chown(route_tmp,999,1000); os.chmod(route_tmp,0o644); os.replace(route_tmp,'/etc/asterisk/meshphone.conf')
  reloadr=subprocess.run(['/usr/sbin/asterisk','-rx','dialplan reload'],text=True,capture_output=True,timeout=20)
  if reloadr.returncode: raise RuntimeError('Asterisk reload failed: '+reloadr.stderr[-1000:])
  status.update({'ok':True,'matched':discovered.get('matched',[]),'unmatched':discovered.get('unmatched',[]),'active_peers':existing['peers']})
 except Exception as e:
  status['error']=str(e)
 atomic_json(STATUS,status)
 print(json.dumps(status,indent=2))
 return 0 if status['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
