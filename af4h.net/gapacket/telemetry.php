<?php
declare(strict_types=1);
ini_set('display_errors','0');require __DIR__.'/core.php';require __DIR__.'/link-data.php';
try{
 if($_SERVER['REQUEST_METHOD']!=='POST')appFail('POST required.',405);
 if((int)($_SERVER['CONTENT_LENGTH']??0)>65536)appFail('Payload exceeds 64 KiB.',413);
 $auth=$_SERVER['HTTP_AUTHORIZATION']??$_SERVER['REDIRECT_HTTP_AUTHORIZATION']??'';
 if(!preg_match('/^Bearer (gp_([a-f0-9]{16})\.[a-f0-9]{64})$/D',$auth,$match))appFail('Valid telemetry API key required.',401);
 $db=appDb();ensureLinkSchema($db);$key=rowById($db,'telemetry_keys','id',$match[2]);
 if(!$key||$key['revoked']||$key['expires']<time()||!hash_equals($key['key_hash'],hash('sha256',$match[1])))appFail('API key is invalid, expired, or revoked.',401);
 limitRequests($db,'telemetry:'.$key['id'],60,60);$nodes=json_decode($key['nodes'],true);$scopes=json_decode($key['scopes'],true);
 $input=json_decode(file_get_contents('php://input'),true);if(!is_array($input)||array_diff(array_keys($input),['links','metrics']))appFail('Supply links and/or metrics arrays.');
 $links=$input['links']??[];$metrics=$input['metrics']??[];if(!is_array($links)||!is_array($metrics)||count($links)>100||count($metrics)>100)appFail('Maximum 100 links and 100 metric samples per request.');
 if($links&&!in_array('links',$scopes,true))appFail('This key cannot report links.',403);if($metrics&&!in_array('metrics',$scopes,true))appFail('This key cannot report metrics.',403);
 $validLinks=[];
 foreach($links as $d){if(!is_array($d))appFail('Invalid link.');$d=validateLink($d);$allowed=array_intersect([$d['a_node'],$d['z_node']],$nodes);$listed=false;foreach($allowed as $node)if(rowById($db,'stations','callsign',$node))$listed=true;if(!$listed)appFail('Link must include a listed station in this key’s scope.',403);$validLinks[]=$d;}
 $validMetrics=[];
 foreach($metrics as $d){
  if(!is_array($d))appFail('Invalid sample.');$station=strtoupper(trim((string)($d['station_id']??'')));
  if(!in_array($station,$nodes,true)||!rowById($db,'stations','callsign',$station))appFail('Metric station is not listed in this key’s scope.',403);
  $seen=strtotime((string)($d['observed_at']??''));if($seen===false||$seen<time()-2592000||$seen>time()+300)appFail('Metrics require a timestamp within the last 30 days.');
  $throughput=$d['throughput_bps']??null;if($throughput!==null&&(!is_numeric($throughput)||!is_finite((float)$throughput)||$throughput<0||$throughput>1000000000))appFail('Invalid throughput.');
  $values=[];foreach(['error_count','retry_count','packet_count']as $field){$v=$d[$field]??null;if($v!==null){$v=filter_var($v,FILTER_VALIDATE_INT);if($v===false||$v<0||$v>1000000000)appFail('Counts must be nonnegative integers.');}$values[]=$v;}
  if($throughput===null&&count(array_filter($values,fn($v)=>$v!==null))===0)appFail('Supply at least one measured metric.');
  $validMetrics[]=[$key['id'],$station,gmdate('c',$seen),$throughput===null?null:(float)$throughput,...$values];
 }
 $db->beginTransaction();$accepted=0;$sampleCount=0;
 foreach($validLinks as $d){
  $before=rowById($db,'node_links','id',$d['id']);$owner=rowById($db,'link_owners','link_id',$d['id']);
  if($before&&(!$owner||$owner['key_id']!==$key['id'])){$db->rollBack();appFail('This link ID is managed by another reporter or a sysop.',403);}
  if($before&&strtotime($d['last_seen'])<strtotime($before['last_seen'])){$db->rollBack();appFail('Older link reports cannot replace newer observations.',409);}
  $same=$before; if($same){unset($same['source'],$same['updated']);}
  if($same===$d)continue;
  saveLinkRow($db,$d,'telemetry');$q=$db->prepare('INSERT OR IGNORE INTO link_owners VALUES(?,?)');$q->execute([$d['id'],$key['id']]);
  auditEvent($db,'telemetry',$key['id'],'link',$d['id'],$before?'change':'add',$before,rowById($db,'node_links','id',$d['id']));$accepted++;
 }
 $q=$db->prepare('INSERT OR IGNORE INTO metric_samples(key_id,station_id,observed_at,throughput_bps,error_count,retry_count,packet_count) VALUES(?,?,?,?,?,?,?)');
 foreach($validMetrics as $sample){$q->execute($sample);$sampleCount+=$q->rowCount();}
 $q=$db->prepare('UPDATE telemetry_keys SET last_used=? WHERE id=?');$q->execute([gmdate('c'),$key['id']]);$db->exec("DELETE FROM metric_samples WHERE observed_at < '".gmdate('c',time()-2592000)."'");$db->commit();appReply(['ok'=>true,'links_updated'=>$accepted,'samples_added'=>$sampleCount]);
}catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();error_log('Telemetry: '.$e->getMessage());appFail('Telemetry could not be recorded.',500);}
