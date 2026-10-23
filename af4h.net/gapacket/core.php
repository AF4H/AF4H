<?php
declare(strict_types=1);
function appDb():PDO{
 $db=new PDO('sqlite:'.dirname(__DIR__,2).'/private/gapacket/stations.sqlite');$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->exec('PRAGMA busy_timeout=5000');appSchema($db);return $db;
}
function appSchema(PDO $db):void{
 $db->exec('CREATE TABLE IF NOT EXISTS sysops(callsign TEXT PRIMARY KEY,email TEXT NOT NULL,version TEXT NOT NULL,created TEXT NOT NULL)');
 $db->exec('CREATE TABLE IF NOT EXISTS login_tokens(hash TEXT PRIMARY KEY,callsign TEXT NOT NULL,version TEXT NOT NULL,expires INTEGER NOT NULL)');
 $db->exec('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,actor_type TEXT NOT NULL,actor TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,action TEXT NOT NULL,before_json TEXT,after_json TEXT)');
 $db->exec('CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,"Audit records cannot be edited"); END');
 $db->exec('CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,"Audit records cannot be deleted"); END');
 $db->exec('CREATE TABLE IF NOT EXISTS telemetry_keys(id TEXT PRIMARY KEY,name TEXT NOT NULL,key_hash TEXT NOT NULL,scopes TEXT NOT NULL,nodes TEXT NOT NULL,created TEXT NOT NULL,expires INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,last_used TEXT)');
 $db->exec('CREATE TABLE IF NOT EXISTS link_owners(link_id TEXT PRIMARY KEY,key_id TEXT NOT NULL)');
 $db->exec('CREATE TABLE IF NOT EXISTS metric_samples(id INTEGER PRIMARY KEY AUTOINCREMENT,key_id TEXT NOT NULL,station_id TEXT NOT NULL,observed_at TEXT NOT NULL,throughput_bps REAL,error_count INTEGER,retry_count INTEGER,packet_count INTEGER,UNIQUE(key_id,station_id,observed_at))');
 $db->exec('CREATE INDEX IF NOT EXISTS metrics_station_time ON metric_samples(station_id,observed_at)');
 $db->exec('CREATE TABLE IF NOT EXISTS app_limits(bucket TEXT PRIMARY KEY,started INTEGER NOT NULL,n INTEGER NOT NULL)');
}
function auditEvent(PDO $db,string $type,string $actor,string $entity,string $id,string $action,$before=null,$after=null):void{
 foreach(['before','after']as $name){if(is_array($$name))foreach(['edit_hash','key_hash']as $field)unset(${$name}[$field]);}
 $q=$db->prepare('INSERT INTO audit(at,actor_type,actor,entity_type,entity_id,action,before_json,after_json) VALUES(?,?,?,?,?,?,?,?)');$q->execute([gmdate('c'),$type,$actor,$entity,$id,$action,$before===null?null:json_encode($before),$after===null?null:json_encode($after)]);
}
function appReply($data,int $status=200):never{http_response_code($status);header('Content-Type: application/json; charset=utf-8');header('Cache-Control: no-store');echo json_encode($data,JSON_INVALID_UTF8_SUBSTITUTE);exit;}
function appFail(string $text,int $status=400):never{appReply(['error'=>$text],$status);}
function baseCall(string $call):string{return preg_replace('~/[0-9]{1,2}$~','',strtoupper(trim($call)));}
function checkCall(string $call):bool{return (bool)preg_match('~^(?:[KNW][0-9][A-Z]{1,3}|(?:A[A-L]|[KNW][A-Z])[0-9][A-Z]{1,3})(?:/[0-9]{1,2})?$~D',$call);}
function appSession():void{if(session_status()!==PHP_SESSION_ACTIVE){session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Lax','path'=>'/gapacket/']);session_start();}$_SESSION['sysop_csrf']??=bin2hex(random_bytes(24));}
function currentSysop(PDO $db):?array{
 if(empty($_SESSION['sysop'])||($_SESSION['sysop_expires']??0)<time())return null;
 $q=$db->prepare('SELECT * FROM sysops WHERE callsign=?');$q->execute([$_SESSION['sysop']]);$r=$q->fetch(PDO::FETCH_ASSOC);
 return $r&&hash_equals($r['version'],(string)($_SESSION['sysop_version']??''))?$r:null;
}
function limitRequests(PDO $db,string $bucket,int $max,int $seconds):void{
 $q=$db->prepare('INSERT INTO app_limits(bucket,started,n) VALUES(?,?,1) ON CONFLICT(bucket) DO UPDATE SET started=CASE WHEN started<=? THEN excluded.started ELSE started END,n=CASE WHEN started<=? THEN 1 ELSE n+1 END');$q->execute([$bucket,time(),time()-$seconds,time()-$seconds]);
 $q=$db->prepare('SELECT n FROM app_limits WHERE bucket=?');$q->execute([$bucket]);if((int)$q->fetchColumn()>$max)appFail('Too many requests. Try again later.',429);
}
function rowById(PDO $db,string $table,string $field,string $id){$q=$db->prepare("SELECT * FROM $table WHERE $field=?");$q->execute([$id]);return $q->fetch(PDO::FETCH_ASSOC)?:null;}
function validateStation(array $d):array{
 $call=strtoupper(trim((string)($d['callsign']??'')));if(!checkCall($call))appFail('Enter a valid US station callsign.');
 $status=$d['status']??'';if(!in_array($status,['online','ready','interested'],true))appFail('Invalid station status.');
 $address=trim((string)($d['address']??''));if(!$address||strlen($address)>500)appFail('Address is required (500 characters maximum).');
 foreach(['lat'=>90,'lng'=>180]as $k=>$max)if(!isset($d[$k])||!is_numeric($d[$k])||!is_finite((float)$d[$k])||abs((float)$d[$k])>$max)appFail('Enter valid latitude and longitude.');
 return ['callsign'=>$call,'address'=>$address,'status'=>$status,'lat'=>(float)$d['lat'],'lng'=>(float)$d['lng']];
}
function validateLink(array $d):array{
 $id=trim((string)($d['id']??''));if(!preg_match('/^[A-Za-z0-9_.:-]{1,100}$/D',$id))appFail('Link ID must use letters, digits, dots, dashes, colons or underscores.');
 $a=strtoupper(trim((string)($d['a_node']??'')));$z=strtoupper(trim((string)($d['z_node']??'')));if(!checkCall($a)||!checkCall($z)||$a===$z)appFail('Enter two distinct valid station IDs.');
 $capacity=filter_var($d['capacity_bps']??null,FILTER_VALIDATE_INT);if($capacity===false||$capacity<300||$capacity>57600)appFail('Capacity must be 300–57,600 bps.');
 $frequency=$d['frequency_hz']??null;if($frequency==='')$frequency=null;
 if($frequency!==null){$frequency=filter_var($frequency,FILTER_VALIDATE_INT);if($frequency===false||$frequency<1||$frequency>1000000000000)appFail('Enter frequency in integer hertz or leave it blank.');}
 $status=$d['status']??'';if(!in_array($status,['online','offline','disabled'],true))appFail('Invalid link status.');
 $seen=strtotime((string)($d['last_seen']??''));if($seen===false||$seen>time()+300)appFail('Enter a valid last-seen timestamp, no more than five minutes ahead.');
 return ['id'=>$id,'a_node'=>$a,'z_node'=>$z,'frequency_hz'=>$frequency,'capacity_bps'=>$capacity,'status'=>$status,'last_seen'=>gmdate('c',$seen)];
}
function saveStationRow(PDO $db,array $d):void{$q=$db->prepare('INSERT INTO stations(callsign,address,status,lat,lng,edit_hash,updated) VALUES(?,?,?,?,?,?,?) ON CONFLICT(callsign) DO UPDATE SET address=excluded.address,status=excluded.status,lat=excluded.lat,lng=excluded.lng,updated=excluded.updated');$q->execute([$d['callsign'],$d['address'],$d['status'],$d['lat'],$d['lng'],'',gmdate('c')]);$q=$db->prepare('DELETE FROM pending WHERE callsign=?');$q->execute([$d['callsign']]);}
function saveLinkRow(PDO $db,array $d,string $source):void{$q=$db->prepare('INSERT INTO node_links VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET a_node=excluded.a_node,z_node=excluded.z_node,frequency_hz=excluded.frequency_hz,capacity_bps=excluded.capacity_bps,status=excluded.status,last_seen=excluded.last_seen,source=excluded.source,updated=excluded.updated');$q->execute([$d['id'],$d['a_node'],$d['z_node'],$d['frequency_hz'],$d['capacity_bps'],$d['status'],$d['last_seen'],$source,gmdate('c')]);}
