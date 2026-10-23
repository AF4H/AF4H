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
function sendConfirmation($recipient,$subject,$body,$config){
 $host=$config['smtp_host']??'127.0.0.1';$port=(int)($config['smtp_port']??25);
 $context=stream_context_create(['ssl'=>['verify_peer'=>true,'verify_peer_name'=>true,'peer_name'=>$config['smtp_tls_name']??$host]]);
 $socket=stream_socket_client('tcp://'.$host.':'.$port,$errno,$error,10,STREAM_CLIENT_CONNECT,$context);
 if(!$socket)return false;stream_set_timeout($socket,15);
 $read=function($expected)use($socket){$response='';do{$line=fgets($socket,4096);if($line===false)throw new RuntimeException('SMTP connection closed');$response.=$line;}while(strlen($line)>3&&$line[3]==='-');if(!in_array((int)substr($response,0,3),$expected,true))throw new RuntimeException('SMTP rejected delivery step');return $response;};
 $command=function($line,$expected)use($socket,$read){if(fwrite($socket,$line."\r\n")===false)throw new RuntimeException('SMTP write failed');return $read($expected);};
 try{
  $read([220]);$hello=$command('EHLO af4h.net',[250]);
  if(stripos($hello,'STARTTLS')===false)throw new RuntimeException('SMTP TLS unavailable');
  $command('STARTTLS',[220]);if(!stream_socket_enable_crypto($socket,true,STREAM_CRYPTO_METHOD_TLS_CLIENT))throw new RuntimeException('SMTP TLS failed');
  $command('EHLO af4h.net',[250]);
  if(!empty($config['smtp_username'])){$command('AUTH LOGIN',[334]);$command(base64_encode($config['smtp_username']),[334]);$command(base64_encode($config['smtp_password']??''),[235]);}
  $command('MAIL FROM:<af4h@af4h.net>',[250]);$command('RCPT TO:<'.$recipient.'>',[250,251]);$command('DATA',[354]);
  $text="From: AF4H Packet Map <af4h@af4h.net>\r\nTo: ".$recipient."\r\nSubject: ".$subject."\r\nDate: ".date(DATE_RFC2822)."\r\nMessage-ID: <".bin2hex(random_bytes(16))."@af4h.net>\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n".chunk_split(base64_encode($body),76,"\r\n");
  if(fwrite($socket,$text."\r\n.\r\n")===false)throw new RuntimeException('SMTP write failed');$read([250]);fwrite($socket,"QUIT\r\n");fclose($socket);return true;
 }catch(Throwable $e){fclose($socket);error_log('GAPacket mail: '.$e->getMessage());return false;}
}
function qrzRecord($call,$private){
  $config=is_file($private.'/config.php')?require $private.'/config.php':[];
  if(empty($config['qrz_username'])||empty($config['qrz_password']))fail('QRZ lookup is awaiting server configuration. You can enter your address and place a pin manually.',503);
  $key=apcu_fetch('gapacket_qrz_session');
  for($i=0;$i<2;$i++){
   if(!$key){$login=remoteXml(['username'=>$config['qrz_username'],'password'=>$config['qrz_password'],'agent'=>'AF4H-GAPacket-1.0']);$key=(string)$login->Session->Key;if(!$key)fail('QRZ login failed. The site owner needs to check the subscription and credentials.',502);apcu_store('gapacket_qrz_session',$key,3600);}
   $lookupCall=preg_replace('~/[0-9]+$~','',$call);
   $x=remoteXml(['s'=>$key,'callsign'=>$lookupCall]);$error=(string)$x->Session->Error;
   if($error&&preg_match('/session|timeout/i',$error)){$key=false;apcu_delete('gapacket_qrz_session');continue;}
   if($error)fail('QRZ could not find this callsign or return its address.',404);
   $c=$x->Callsign;$address=implode(', ',array_filter([(string)$c->addr1,(string)$c->addr2,trim((string)$c->state.' '.(string)$c->zip),(string)$c->country]));
   
   return ['address'=>$address,'lat'=>isset($c->lat)?(float)$c->lat:null,'lng'=>isset($c->lon)?(float)$c->lon:null,'email'=>trim((string)$c->email)];
  }fail('QRZ session expired. Please try again.',502);
}
try{
 $private=dirname(__DIR__,2).'/private/gapacket';
 if(!is_dir($private))throw new RuntimeException('Storage missing');
 $db=new PDO('sqlite:'.$private.'/stations.sqlite');$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->exec('PRAGMA busy_timeout=5000');
 $db->exec('CREATE TABLE IF NOT EXISTS stations (callsign TEXT PRIMARY KEY,address TEXT NOT NULL,status TEXT NOT NULL,lat REAL NOT NULL,lng REAL NOT NULL,edit_hash TEXT NOT NULL,updated TEXT NOT NULL)');
 $db->exec('CREATE TABLE IF NOT EXISTS limits (ip TEXT PRIMARY KEY,window INTEGER,n INTEGER)');
 $db->exec('CREATE TABLE IF NOT EXISTS pending (id TEXT PRIMARY KEY, callsign TEXT NOT NULL, payload TEXT NOT NULL, baseline TEXT NOT NULL, recipient TEXT NOT NULL, expires INTEGER NOT NULL, created INTEGER NOT NULL)');
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
 if(!preg_match('~^(?:[KNW][0-9][A-Z]{1,3}|(?:A[A-L]|[KNW][A-Z])[0-9][A-Z]{1,3})(?:/[0-9]{1,2})?$~D',$call))fail('Enter a US callsign: K, N, W, or AA–AL prefix, one digit, and 1–3 suffix letters; optionally add /0 through /99. N0CALL is a placeholder only.');
 if($action==='lookup'){
  $data=qrzRecord($call,$private);unset($data['email']);reply($data);
 }
 $q=$db->prepare('SELECT callsign,status,lat,lng,updated FROM stations WHERE callsign=?');$q->execute([$call]);$existing=$q->fetch(PDO::FETCH_ASSOC);
 if($action==='check')reply(['exists'=>(bool)$existing,'station'=>$existing?:null]);
 if($action!=='save')fail('Unknown action',404);
 $status=$input['status']??'';$remove=$status==='remove';
 if(!in_array($status,['online','ready','interested','remove'],true))fail('Choose a status.');
 if($remove&&!$existing)fail('No station is registered with this exact callsign to remove.',404);
 $address=trim((string)($input['address']??''));$lat=$input['lat']??null;$lng=$input['lng']??null;
 if(!$remove){
  if(!$address||strlen($address)>500)fail('Enter an address (500 characters maximum).');
  if(!is_numeric($lat)||!is_numeric($lng)||!is_finite((float)$lat)||!is_finite((float)$lng)||$lat < -90||$lat >90||$lng < -180||$lng >180)fail('Place your pin on the map.');
 }
 $q=$db->prepare('SELECT * FROM stations WHERE callsign=?');$q->execute([$call]);$before=$q->fetch(PDO::FETCH_ASSOC);
 if($before&&!$remove&&($input['confirm_update']??false)!==true)reply(['error'=>'Callsign already registered. Update?','code'=>'already_registered'],409);
 // Resolve the recipient only from QRZ, never from browser input. Errors do not bypass QRZ.
 $record=qrzRecord($call,$private);$recipient=filter_var($record['email'],FILTER_VALIDATE_EMAIL)?$record['email']:'af4h@af4h.net';
 $fallback=$recipient==='af4h@af4h.net'&&!filter_var($record['email'],FILTER_VALIDATE_EMAIL);
 $payload=json_encode(['callsign'=>$call,'address'=>$address,'status'=>$status,'lat'=>$remove?null:(float)$lat,'lng'=>$remove?null:(float)$lng]);
 $token=bin2hex(random_bytes(32));$id=hash('sha256',$token);$now=time();
 $db->beginTransaction();$db->exec('DELETE FROM pending WHERE expires < '.($now-86400));
 $q=$db->prepare('SELECT COUNT(*) FROM pending WHERE callsign=? AND created>?');$q->execute([$call,$now-3600]);
 if($q->fetchColumn()>=3){$db->rollBack();fail('Confirmation already requested. Check your email, or try again in an hour.',429);}
 $q=$db->prepare('INSERT INTO pending VALUES (?,?,?,?,?,?,?)');
 $q->execute([$id,$call,$payload,hash('sha256',json_encode($before?:null)),$recipient,$now+3600,$now]);$db->commit();
 $operation=$remove?'removal':($before?'update':'addition');
 $link='https://af4h.net/gapacket/confirm.php?token='.$token;
 $body="A TARPN #gapacket station ".$operation." was requested for ".$call.".\n\n";
 $body.=$remove?"This will remove the station from the public map.\n":"Proposed status: ".$status."\nProposed address: ".$address."\nMap coordinates: ".$lat.", ".$lng."\n";
 $body.="\nReview and confirm this exact change:\n".$link."\n\nThe link expires in one hour and can be used once. Opening the link does not approve the change; use the confirmation button on the page.\n\nIf you did not request this, ignore this email. The map remains unchanged.\n";
 if($fallback)$body.="\nAdministrator review: QRZ has no valid email for the base callsign.\n";
 $config=require $private.'/config.php';
 $sent=sendConfirmation($recipient,'Confirm TARPN #gapacket station '.$operation.': '.$call,$body,$config);
 if(!$sent){$q=$db->prepare('DELETE FROM pending WHERE id=?');$q->execute([$id]);fail('The confirmation email could not be sent. No map changes were made. Please try again later.',502);}
 reply(['pending'=>true,'fallback'=>$fallback,'message'=>$fallback?'Confirmation sent to af4h@af4h.net for review because QRZ has no email on file. The map stays unchanged until approved.':'Confirmation sent to the QRZ email on file for your base callsign. The map stays unchanged until approved.']);

}catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();error_log('GAPacket: '.$e->getMessage());fail('The server could not complete the request. Please try again.',500);}

