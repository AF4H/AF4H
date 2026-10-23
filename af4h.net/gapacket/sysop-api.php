<?php
declare(strict_types=1);
ini_set('display_errors','0');header('Cache-Control: no-store');header('X-Content-Type-Options: nosniff');
require __DIR__.'/core.php';require __DIR__.'/communication.php';require __DIR__.'/link-data.php';
appSession();
try{
 $db=appDb();ensureLinkSchema($db);$action=$_GET['action']??'me';$who=currentSysop($db);
 if($action==='me')appReply(['sysop'=>$who?['callsign'=>$who['callsign'],'email'=>$who['email']]:null,'csrf'=>$_SESSION['sysop_csrf']]);
 if($_SERVER['REQUEST_METHOD']==='GET'){
  if(!$who)appFail('Sysop login required.',401);
  if($action==='data'){
   $stations=$db->query('SELECT callsign,address,status,lat,lng,updated FROM stations ORDER BY callsign')->fetchAll(PDO::FETCH_ASSOC);
   $keys=$db->query('SELECT id,name,scopes,nodes,created,expires,revoked,last_used FROM telemetry_keys ORDER BY created DESC')->fetchAll(PDO::FETCH_ASSOC);
   $sysops=$db->query('SELECT callsign,email,created FROM sysops ORDER BY callsign')->fetchAll(PDO::FETCH_ASSOC);
   appReply(['stations'=>$stations,'links'=>publicLinkData($db,time()),'sysops'=>$sysops,'keys'=>$keys]);
  }
  if($action==='audit'){
   $cursor=max(0,(int)($_GET['before']??0));$q=$db->prepare('SELECT * FROM audit WHERE id<? ORDER BY id DESC LIMIT 100');$q->bindValue(1,$cursor?:PHP_INT_MAX,PDO::PARAM_INT);$q->execute();$rows=$q->fetchAll(PDO::FETCH_ASSOC);appReply(['events'=>$rows,'next_before'=>count($rows)===100?(int)end($rows)['id']:null]);
  }appFail('Unknown action.',404);
 }
 if($_SERVER['REQUEST_METHOD']!=='POST')appFail('POST required.',405);
 if((int)($_SERVER['CONTENT_LENGTH']??0)>64000)appFail('Request too large.',413);
 $input=json_decode(file_get_contents('php://input'),true);if(!is_array($input))appFail('Invalid JSON.');
 if(!hash_equals($_SESSION['sysop_csrf'],(string)($input['csrf']??'')))appFail('Refresh this page and try again.',403);
 if($action==='login_request'){
  $call=baseCall((string)($input['callsign']??''));if(!checkCall($call))appFail('Enter a valid US sysop callsign.');
  limitRequests($db,'login-ip:'.hash('sha256',$_SERVER['REMOTE_ADDR']??''),8,900);limitRequests($db,'login-call:'.$call,3,900);
  $sysop=rowById($db,'sysops','callsign',$call);
  if($sysop){
   $token=bin2hex(random_bytes(32));$q=$db->prepare('INSERT INTO login_tokens VALUES(?,?,?,?)');$q->execute([hash('sha256',$token),$call,$sysop['version'],time()+900]);
   $config=require dirname(__DIR__,2).'/private/gapacket/config.php';
   $body="A sysop login was requested for ".$call." on the AF4H station map.\n\nOpen this link and select Sign in:\nhttps://af4h.net/gapacket/sysop.php#login=".$token."\n\nThis link expires in 15 minutes and can be used once. Do not forward it. If this was not you, ignore this email.\n";
   if(!sendConfirmation($sysop['email'],'AF4H sysop sign-in link: '.$call,$body,$config)){ $q=$db->prepare('DELETE FROM login_tokens WHERE hash=?');$q->execute([hash('sha256',$token)]);error_log('Sysop login mail failed');}
  }
  appReply(['message'=>'If this callsign is registered as a sysop, a sign-in link has been sent to its email on file.']);
 }
 if($action==='login_consume'){
  $token=(string)($input['token']??'');if(!preg_match('/^[a-f0-9]{64}$/D',$token))appFail('Invalid login link.',403);
  $db->beginTransaction();$row=rowById($db,'login_tokens','hash',hash('sha256',$token));$sysop=$row?rowById($db,'sysops','callsign',$row['callsign']):null;
  if(!$row||$row['expires']<time()||!$sysop||!hash_equals($sysop['version'],$row['version'])){$db->rollBack();appFail('Login link expired, already used, or access removed. Request a new link.',403);}
  $q=$db->prepare('DELETE FROM login_tokens WHERE callsign=?');$q->execute([$row['callsign']]);auditEvent($db,'sysop',$sysop['callsign'],'sysop',$sysop['callsign'],'login');$db->commit();
  session_regenerate_id(true);$_SESSION['sysop']=$sysop['callsign'];$_SESSION['sysop_version']=$sysop['version'];$_SESSION['sysop_expires']=time()+28800;$_SESSION['sysop_csrf']=bin2hex(random_bytes(24));appReply(['ok'=>true,'csrf'=>$_SESSION['sysop_csrf']]);
 }
 if(!$who)appFail('Sysop login required.',401);
 if($action==='logout'){unset($_SESSION['sysop'],$_SESSION['sysop_version'],$_SESSION['sysop_expires']);session_regenerate_id(true);appReply(['ok'=>true]);}
 limitRequests($db,'sysop:'.$who['callsign'],120,60);
 if($action==='station_save'){
  $d=validateStation($input);$db->beginTransaction();$before=rowById($db,'stations','callsign',$d['callsign']);saveStationRow($db,$d);auditEvent($db,'sysop',$who['callsign'],'station',$d['callsign'],$before?'change':'add',$before,rowById($db,'stations','callsign',$d['callsign']));$db->commit();appReply(['ok'=>true]);
 }
 if($action==='station_remove'){
  $call=strtoupper(trim((string)($input['callsign']??'')));$db->beginTransaction();$before=rowById($db,'stations','callsign',$call);if(!$before){$db->rollBack();appFail('Station not found.',404);}
  $q=$db->prepare('DELETE FROM stations WHERE callsign=?');$q->execute([$call]);$q=$db->prepare('DELETE FROM pending WHERE callsign=?');$q->execute([$call]);auditEvent($db,'sysop',$who['callsign'],'station',$call,'remove',$before);$db->commit();appReply(['ok'=>true]);
 }
 if($action==='link_save'){
  $d=validateLink($input);$db->beginTransaction();$before=rowById($db,'node_links','id',$d['id']);saveLinkRow($db,$d,'sysop');auditEvent($db,'sysop',$who['callsign'],'link',$d['id'],$before?'change':'add',$before,rowById($db,'node_links','id',$d['id']));$db->commit();appReply(['ok'=>true]);
 }
 if($action==='link_remove'){
  $id=(string)($input['id']??'');$db->beginTransaction();$before=rowById($db,'node_links','id',$id);if(!$before){$db->rollBack();appFail('Link not found.',404);}
  $q=$db->prepare('DELETE FROM node_links WHERE id=?');$q->execute([$id]);$q=$db->prepare('DELETE FROM link_owners WHERE link_id=?');$q->execute([$id]);auditEvent($db,'sysop',$who['callsign'],'link',$id,'remove',$before);$db->commit();appReply(['ok'=>true]);
 }
 if($action==='sysop_save'){
  $call=baseCall((string)($input['callsign']??''));$email=trim((string)($input['email']??''));if(!checkCall($call)||!filter_var($email,FILTER_VALIDATE_EMAIL))appFail('Enter a valid base callsign and email.');
  $db->beginTransaction();$before=rowById($db,'sysops','callsign',$call);$q=$db->prepare('INSERT INTO sysops VALUES(?,?,?,?) ON CONFLICT(callsign) DO UPDATE SET email=excluded.email,version=excluded.version');$q->execute([$call,$email,bin2hex(random_bytes(16)),gmdate('c')]);auditEvent($db,'sysop',$who['callsign'],'sysop',$call,$before?'change':'add',$before,['callsign'=>$call,'email'=>$email]);$db->commit();appReply(['ok'=>true]);
 }
 if($action==='sysop_remove'){
  $call=baseCall((string)($input['callsign']??''));$db->beginTransaction();$before=rowById($db,'sysops','callsign',$call);if(!$before){$db->rollBack();appFail('Sysop not found.',404);}if((int)$db->query('SELECT COUNT(*) FROM sysops')->fetchColumn()<=1){$db->rollBack();appFail('The last sysop cannot be removed.');}
  $q=$db->prepare('DELETE FROM sysops WHERE callsign=?');$q->execute([$call]);$q=$db->prepare('DELETE FROM login_tokens WHERE callsign=?');$q->execute([$call]);auditEvent($db,'sysop',$who['callsign'],'sysop',$call,'remove',$before);$db->commit();appReply(['ok'=>true]);
 }
 if($action==='key_create'){
  $name=trim((string)($input['name']??''));$nodes=array_values(array_unique(array_map(fn($s)=>strtoupper(trim($s)),explode(',',(string)($input['nodes']??'')))));$scopes=$input['scopes']??[];$days=(int)($input['days']??90);
  if(!$name||strlen($name)>100||!is_array($scopes)||!$scopes||array_diff($scopes,['links','metrics'])||$days<1||$days>365)appFail('Supply a key name, valid scopes, and expiry from 1 to 365 days.');
  foreach($nodes as $node)if(!checkCall($node)||!rowById($db,'stations','callsign',$node))appFail('Each key must be scoped to explicitly listed stations.');
  $db->beginTransaction();$id=bin2hex(random_bytes(8));$token='gp_'.$id.'.'.bin2hex(random_bytes(32));$q=$db->prepare('INSERT INTO telemetry_keys(id,name,key_hash,scopes,nodes,created,expires) VALUES(?,?,?,?,?,?,?)');$q->execute([$id,$name,hash('sha256',$token),json_encode(array_values(array_unique($scopes))),json_encode($nodes),gmdate('c'),time()+$days*86400]);auditEvent($db,'sysop',$who['callsign'],'api_key',$id,'create',null,['name'=>$name,'nodes'=>$nodes,'scopes'=>$scopes]);$db->commit();appReply(['token'=>$token,'id'=>$id]);
 }
 if($action==='key_revoke'){
  $id=(string)($input['id']??'');$before=rowById($db,'telemetry_keys','id',$id);if(!$before)appFail('Key not found.',404);$db->beginTransaction();$q=$db->prepare('UPDATE telemetry_keys SET revoked=1 WHERE id=?');$q->execute([$id]);auditEvent($db,'sysop',$who['callsign'],'api_key',$id,'revoke');$db->commit();appReply(['ok'=>true]);
 }
 appFail('Unknown action.',404);
}catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();error_log('Sysop API: '.$e->getMessage());appFail('The request could not be completed.',500);}
