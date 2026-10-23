import pathlib,tempfile,subprocess,urllib.request,urllib.error,urllib.parse,http.cookiejar,json,re,time,sqlite3,shutil,hashlib,datetime
root=pathlib.Path(tempfile.mkdtemp(prefix='sysop-test-'));web=root/'domain/public_html/gapacket';private=root/'domain/private/gapacket';web.mkdir(parents=True);private.mkdir(parents=True)
for p in pathlib.Path('.').glob('*.php'):
 s=p.read_text().replace("'secure'=>true","'secure'=>false")
 if p.name=='communication.php':
  a=s.index('function sendConfirmation(');b=s.index('function qrzRecord(',a);s=s[:a]+'''function sendConfirmation($to,$subject,$body,$config){file_put_contents(dirname(__DIR__,2).'/private/gapacket/mail.json',json_encode(['recipient'=>$to,'body'=>$body]));return true;}
'''+s[b:]
 (web/p.name).write_text(s)
(private/'config.php').write_text('<?php return [];')
# Existing application tables are preserved by the migration.
db=sqlite3.connect(private/'stations.sqlite')
db.executescript('CREATE TABLE stations(callsign TEXT PRIMARY KEY,address TEXT,status TEXT,lat REAL,lng REAL,edit_hash TEXT,updated TEXT);CREATE TABLE pending(id TEXT PRIMARY KEY,callsign TEXT,payload TEXT,baseline TEXT,recipient TEXT,expires INTEGER,created INTEGER);')
now=lambda:datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
db.execute('INSERT INTO stations VALUES(?,?,?,?,?,?,?)',('K1ABC','Private street','online',33,-84,'',now()));db.commit()
server=subprocess.Popen(['php','-d','session.save_path='+str(private),'-S','127.0.0.1:19877','-t',str(web.parent)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
base='http://127.0.0.1:19877/gapacket/';op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));csrf=''
def req(path,data=None,client=op,headers=None,form=False):
 headers=dict(headers or {});raw=None
 if data is not None:
  raw=(urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode());headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
 try:
  with client.open(urllib.request.Request(base+path,data=raw,headers=headers)) as r:return r.status,r.read().decode()
 except urllib.error.HTTPError as e:return e.code,e.read().decode()
def admin(a,d=None):
 global csrf
 if d is not None:d={'csrf':csrf,**d}
 code,b=req('sysop-api.php?action='+a,d);v=json.loads(b)
 if 'csrf' in v:csrf=v['csrf']
 return code,v
def telemetry(token,d):
 c,b=req('telemetry.php',d,headers={'Authorization':'Bearer '+token});return c,json.loads(b)
try:
 for _ in range(30):
  try:admin('me');break
  except Exception:time.sleep(.1)
 assert admin('data')[0]==401;assert admin('station_save',{})[0]==401
 db.execute('INSERT INTO sysops VALUES(?,?,?,?)',('AF4H','owner@example.com','v1',now()));db.commit()
 assert admin('login_request',{'callsign':'AF4H'})[0]==200
 m=json.loads((private/'mail.json').read_text());assert m['recipient']=='owner@example.com';token=re.search('login=([a-f0-9]{64})',m['body']).group(1)
 assert admin('data')[0]==401 # Opening email is not authentication.
 assert admin('login_consume',{'token':token})[0]==200;assert admin('login_consume',{'token':token})[0]==403
 assert admin('data')[0]==200;assert admin('audit')[1]['events'];assert admin('station_save',{'csrf':'bad'})[0]==403
 print('PASS passwordless sign-in: registry email, explicit consume, single use, authentication, CSRF')
 assert admin('sysop_remove',{'callsign':'AF4H'})[0]==400
 assert admin('sysop_save',{'callsign':'W1ABC','email':'other@example.com'})[0]==200
 assert admin('sysop_remove',{'callsign':'W1ABC'})[0]==200
 p={'callsign':'K1ABC/14','address':'Confidential test address','status':'ready','lat':34,'lng':-84}
 assert admin('station_save',p)[0]==200;assert admin('station_save',{**p,'status':'online'})[0]==200
 assert admin('station_remove',{'callsign':p['callsign']})[0]==200
 assert db.execute('SELECT COUNT(*) FROM audit WHERE entity_type="station"').fetchone()[0]==3
 print('PASS sysop station CRUD + audit, sysop management and last-sysop protection')
 d={'id':'manual','a_node':'K1ABC','z_node':'W1ABC','capacity_bps':9600,'frequency_hz':None,'status':'online','last_seen':now()}
 assert admin('link_save',d)[0]==200;assert admin('link_remove',{'id':'manual'})[0]==200
 code,key=admin('key_create',{'name':'test reporter','nodes':'K1ABC','scopes':['links','metrics'],'days':1});assert code==200,(code,key);api_key=key['token'];key_id=key['id']
 assert api_key not in json.dumps(admin('data')[1]);assert 'key_hash' not in json.dumps(admin('data')[1])
 anon=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));assert req('sysop-api.php?action=data',client=anon,headers={'Authorization':'Bearer '+api_key})[0]==401
 assert telemetry('invalid',{})[0]==401
 assert telemetry(api_key,{'metrics':[{'station_id':'W1ABC','observed_at':now(),'throughput_bps':100}]})[0]==403
 sample={'station_id':'K1ABC','observed_at':now(),'throughput_bps':1200,'error_count':2,'retry_count':3,'packet_count':100}
 code,result=telemetry(api_key,{'links':[{**d,'id':'reported'}],'metrics':[sample]});assert code==200,(code,result);assert result['samples_added']==1
 assert telemetry(api_key,{'metrics':[sample]})[1]['samples_added']==0
 c,b=req('history.php?callsign=K1ABC');h=json.loads(b);assert h['metrics']['24h']['average_throughput_bps']==1200;assert h['metrics']['24h']['error_count']==2;assert h['metrics']['24h']['retry_rate_percent']==3
 assert 'Private street' not in b and 'key_hash' not in b
 assert admin('key_revoke',{'id':key_id})[0]==200;assert telemetry(api_key,{'metrics':[sample]})[0]==401
 print('PASS scoped keys: no sysop access, protected secrets, telemetry ingestion, idempotency, metric aggregation and revocation')
 # End-user approval uses the existing email confirmation route and writes the same audit ledger.
 original=dict(zip(['callsign','address','status','lat','lng','edit_hash','updated'],db.execute('SELECT * FROM stations WHERE callsign=?',('K1ABC',)).fetchone()))
 original={k:int(v) if isinstance(v,float) and v.is_integer() else v for k,v in original.items()}
 payload={'callsign':'K1ABC','address':'Private new address','status':'ready','lat':33,'lng':-84};t='a'*64
 baseline=hashlib.sha256(json.dumps(original,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 db.execute('INSERT INTO pending VALUES(?,?,?,?,?,?,?)',(hashlib.sha256(t.encode()).hexdigest(),'K1ABC',json.dumps(payload),baseline,'owner@example.com',int(time.time())+3600,int(time.time())));db.commit()
 c,html=req('confirm.php?token='+t);assert c==200;approval_csrf=re.search('name="csrf" value="([a-f0-9]+)"',html).group(1)
 c,html=req('confirm.php',{'token':t,'csrf':approval_csrf},form=True);assert c==200,(c,html)
 assert db.execute('SELECT actor_type FROM audit WHERE entity_type="station" AND entity_id="K1ABC" ORDER BY id DESC LIMIT 1').fetchone()[0]=='end_user'
 c,h=req('history.php?callsign=K1ABC');assert 'Private new address' not in h;assert json.loads(h)['history'][0]['status']=='ready'
 try:db.execute('DELETE FROM audit');raise AssertionError('Audit deletion permitted')
 except sqlite3.DatabaseError:pass
 db.rollback()
 assert admin('logout',{})[0]==200;assert admin('data')[0]==401
 print('PASS end-user audit, public history redaction, append-only audit and logout')
finally:
 server.terminate();server.wait();db.close();shutil.rmtree(root)
