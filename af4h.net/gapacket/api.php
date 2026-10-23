<?php
declare(strict_types=1);
ini_set('display_errors','0');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Strict','path'=>'/gapacket/']);
session_start();
$_SESSION['csrf'] ??= bin2hex(random_bytes(24));
function reply($data,$code=200){http_response_code($code);echo json_encode($data,JSON_INVALID_UTF8_SUBSTITUTE);exit;}
function fail($message,$code=400){reply(['error'=>$message],$code);}
function remoteXml($params){
 $c=curl_init('https://xmldata.qrz.com/xml/current/');
 curl_setopt_array($c,[CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>http_build_query($params),CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>15,CURLOPT_CONNECTTIMEOUT=>5,CURLOPT_USERAGENT=>'AF4H GAPacket/1.0']);
 $body=curl_exec($c);$status=curl_getinfo($c,CURLINFO_HTTP_CODE);curl_close($c);
 if(!$body||$status!==200)fail('QRZ is unavailable. Please try again later.',502);
 $xml=simplexml_load_string($body,SimpleXMLElement::class,LIBXML_NONET|LIBXML_NOERROR|LIBXML_NOWARNING);
 if(!$xml)fail('QRZ returned an unreadable response.',502);return $xml;
}
try{
 $private=dirname(__DIR__,2).'/private/gapacket';
 if(!is_dir($private))throw new RuntimeException('Storage missing');
 $db=new PDO('sqlite:'.$private.'/stations.sqlite');$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->exec('PRAGMA busy_timeout=5000');
 $db->exec('CREATE TABLE IF NOT EXISTS stations (callsign TEXT PRIMARY KEY,address TEXT NOT NULL,status TEXT NOT NULL,lat REAL NOT NULL,lng REAL NOT NULL,edit_hash TEXT NOT NULL,updated TEXT NOT NULL)');
 $db->exec('CREATE TABLE IF NOT EXISTS limits (ip TEXT PRIMARY KEY,window INTEGER,n INTEGER)');
 $action=$_GET['action']??'list';
 if($action==='list')reply(['csrf'=>$_SESSION['csrf'],'stations'=>$db->query('SELECT callsign,status,lat,lng,updated FROM stations ORDER BY callsign')->fetchAll(PDO::FETCH_ASSOC)]);
 if($_SERVER['REQUEST_METHOD']!=='POST')fail('POST required',405);
 $input=json_decode(file_get_contents('php://input'),true);if(!is_array($input))fail('Invalid request');
 if(!hash_equals($_SESSION['csrf'],(string)($input['csrf']??'')))fail('Refresh the page and try again.',403);
 $ip=hash('sha256',$_SERVER['REMOTE_ADDR']??'unknown');$now=time();
 $db->beginTransaction();$q=$db->prepare('SELECT window,n FROM limits WHERE ip=?');$q->execute([$ip]);$rate=$q->fetch(PDO::FETCH_ASSOC);
 $window=$rate&&(int)$rate['window']>$now-600?(int)$rate['window']:$now;$n=$window===$now?1:(int)$rate['n']+1;
 $q=$db->prepare('INSERT OR REPLACE INTO limits VALUES (?,?,?)');$q->execute([$ip,$window,$n]);$db->exec('DELETE FROM limits WHERE window < '.($now-1200));$db->commit();if($n>40)fail('Too many requests. Please wait ten minutes.',429);
 $call=strtoupper(trim((string)($input['callsign']??'')));
 if(!preg_match('/^(?=.{3,15}$)(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]+(?:\/[A-Z0-9]+)*$/D',$call))fail('Enter a valid callsign.');
 if($action==='lookup'){
  $config=is_file($private.'/config.php')?require $private.'/config.php':[];
  if(empty($config['qrz_username'])||empty($config['qrz_password']))fail('QRZ lookup is awaiting server configuration. You can enter your address and place a pin manually.',503);
  $key=apcu_fetch('gapacket_qrz_session');
  for($i=0;$i<2;$i++){
   if(!$key){$login=remoteXml(['username'=>$config['qrz_username'],'password'=>$config['qrz_password'],'agent'=>'AF4H-GAPacket-1.0']);$key=(string)$login->Session->Key;if(!$key)fail('QRZ login failed. The site owner needs to check the subscription and credentials.',502);apcu_store('gapacket_qrz_session',$key,3600);}
   $x=remoteXml(['s'=>$key,'callsign'=>$call]);$error=(string)$x->Session->Error;
   if($error&&preg_match('/session|timeout/i',$error)){$key=false;apcu_delete('gapacket_qrz_session');continue;}
   if($error)fail('QRZ could not find this callsign or return its address.',404);
   $c=$x->Callsign;$address=implode(', ',array_filter([(string)$c->addr1,(string)$c->addr2,trim((string)$c->state.' '.(string)$c->zip),(string)$c->country]));
   if(!$address)fail('QRZ has no address available for this callsign.',404);
   reply(['address'=>$address,'lat'=>isset($c->lat)?(float)$c->lat:null,'lng'=>isset($c->lon)?(float)$c->lon:null]);
  }fail('QRZ session expired. Please try again.',502);
 }
 $token=(string)($input['token']??'');
 if(strlen($token)>200)fail('Invalid edit key');
 $q=$db->prepare('SELECT edit_hash,address FROM stations WHERE callsign=?');$q->execute([$call]);$existing=$q->fetch(PDO::FETCH_ASSOC);
 if($existing&&!password_verify($token,$existing['edit_hash']))fail('This callsign already has a marker. Enter its private edit key to change it.',403);
 if($action==='mine'){if(!$existing)fail('No saved station found.',404);reply(['address'=>$existing['address']]);}
 if($action==='delete'){if(!$existing)fail('No saved station found.',404);$q=$db->prepare('DELETE FROM stations WHERE callsign=?');$q->execute([$call]);reply(['ok'=>true]);}
 if($action!=='save')fail('Unknown action',404);
 $address=trim((string)($input['address']??''));$status=$input['status']??'';$lat=$input['lat']??null;$lng=$input['lng']??null;
 if(!$address||strlen($address)>500)fail('Enter an address (500 characters maximum).');
 if(!in_array($status,['online','ready','interested'],true))fail('Choose a status.');
 if(!is_numeric($lat)||!is_numeric($lng)||$lat < -90||$lat >90||$lng < -180||$lng >180)fail('Place your pin on the map.');
 if(!$existing)$token=bin2hex(random_bytes(24));
 $db->beginTransaction();$q=$db->prepare('SELECT edit_hash FROM stations WHERE callsign=?');$q->execute([$call]);$current=$q->fetchColumn();
 if($current&&!password_verify($token,$current)){$db->rollBack();fail('This callsign was just registered. An edit key is required.',409);}
 $q=$db->prepare('INSERT OR REPLACE INTO stations VALUES (?,?,?,?,?,?,?)');$q->execute([$call,$address,$status,(float)$lat,(float)$lng,$current?:password_hash($token,PASSWORD_DEFAULT),gmdate('c')]);$db->commit();reply(['ok'=>true,'token'=>$token]);
}catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();error_log('GAPacket: '.$e->getMessage());fail('The server could not complete the request. Please try again.',500);}
