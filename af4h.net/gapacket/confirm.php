<?php
declare(strict_types=1);
ini_set('display_errors','0');
header('Content-Type: text/html; charset=utf-8');header('Cache-Control: no-store');header('Referrer-Policy: no-referrer');header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Lax','path'=>'/gapacket/']);session_start();
$_SESSION['approval_csrf']??=bin2hex(random_bytes(24));
function esc($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
function page($title,$body,$code=200){http_response_code($code);echo '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'.esc($title).' • TARPN #gapacket</title><style>body{background:#f6f5f0;color:#173e34;font:16px/1.65 system-ui;margin:0;padding:30px}main{max-width:600px;margin:7vh auto;background:white;padding:32px;border:1px solid #d6ddd2;border-radius:10px}h1{line-height:1.2}button{padding:14px 22px;border:0;border-radius:6px;background:#204e3e;color:white;font:600 16px system-ui;cursor:pointer}a{color:#204e3e}dt{font-weight:bold}dd{margin:0 0 14px;overflow-wrap:anywhere}.remove{color:#a32828}</style><main><p>TARPN #gapacket</p><h1>'.esc($title).'</h1>'.$body.'<p><a href="/gapacket/">Return to station map</a></p></main></html>';exit;}
try{
 $token=$_SERVER['REQUEST_METHOD']==='POST'?($_POST['token']??''):($_GET['token']??'');
 if(!is_string($token)||!preg_match('/^[a-f0-9]{64}$/D',$token))page('Invalid confirmation link','<p>Use the complete link from your confirmation email.</p>',400);
 $db=new PDO('sqlite:'.dirname(__DIR__,2).'/private/gapacket/stations.sqlite');$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->exec('PRAGMA busy_timeout=5000');
 $id=hash('sha256',$token);$q=$db->prepare('SELECT * FROM pending WHERE id=?');$q->execute([$id]);$request=$q->fetch(PDO::FETCH_ASSOC);
 if(!$request||$request['expires']<time())page('Link expired or already used','<p>This link is no longer available. Request a new confirmation from the station map.</p>',410);
 $data=json_decode($request['payload'],true,512,JSON_THROW_ON_ERROR);$remove=$data['status']==='remove';
 if($_SERVER['REQUEST_METHOD']==='POST'){
  if(!hash_equals($_SESSION['approval_csrf'],(string)($_POST['csrf']??'')))page('Please reload this page','<p>Your confirmation session expired. Open the email link again.</p>',403);
  $db->beginTransaction();$q=$db->prepare('SELECT * FROM pending WHERE id=?');$q->execute([$id]);$current=$q->fetch(PDO::FETCH_ASSOC);
  if(!$current||$current['expires']<time()){$db->rollBack();page('Link expired or already used','<p>Request a new confirmation from the map.</p>',410);}
  $q=$db->prepare('SELECT * FROM stations WHERE callsign=?');$q->execute([$request['callsign']]);$station=$q->fetch(PDO::FETCH_ASSOC);
  if(!hash_equals($request['baseline'],hash('sha256',json_encode($station?:null)))){$db->rollBack();page('Station changed since this request','<p>A different change has already been approved. Request a fresh confirmation so you can review the current station.</p>',409);}
  if($remove){$q=$db->prepare('DELETE FROM stations WHERE callsign=?');$q->execute([$data['callsign']]);}
  else{$q=$db->prepare('INSERT INTO stations (callsign,address,status,lat,lng,edit_hash,updated) VALUES (?,?,?,?,?,?,?) ON CONFLICT(callsign) DO UPDATE SET address=excluded.address,status=excluded.status,lat=excluded.lat,lng=excluded.lng,updated=excluded.updated');$q->execute([$data['callsign'],$data['address'],$data['status'],$data['lat'],$data['lng'],'',gmdate('c')]);}
  $q=$db->prepare('DELETE FROM pending WHERE callsign=?');$q->execute([$data['callsign']]);$db->commit();
  page($remove?'Station removed':'Station saved','<p>'.esc($data['callsign']).($remove?' has been removed from the map.':' is now updated on the shared map.').'</p>');
 }
 $body='<p>Review the requested '.($remove?'removal':'station details').'. Nothing changes until you confirm.</p><dl><dt>Station</dt><dd>'.esc($data['callsign']).'</dd><dt>Action / status</dt><dd>'.esc($data['status']).'</dd>';
 if(!$remove)$body.='<dt>Address</dt><dd>'.esc($data['address']).'</dd><dt>Map coordinates</dt><dd>'.esc($data['lat']).', '.esc($data['lng']).'</dd>';
 $body.='</dl>'.($remove?'<p class="remove">This will remove this exact station from the public map.</p>':'').'<form method="post" action="confirm.php"><input type="hidden" name="token" value="'.esc($token).'"><input type="hidden" name="csrf" value="'.esc($_SESSION['approval_csrf']).'"><button type="submit">'.($remove?'Confirm removal':'Confirm station change').'</button></form><p>This link expires one hour after the request. If you did not request this change, close this page.</p>';
 page('Confirm '.($remove?'station removal':'station change'),$body);
}catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();error_log('GAPacket approval: '.$e->getMessage());page('Unable to confirm','<p>No change was approved. Please try again later.</p>',500);}
