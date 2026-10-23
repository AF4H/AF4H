<?php
declare(strict_types=1);
ini_set('display_errors','0');require __DIR__.'/core.php';require __DIR__.'/link-data.php';
try{
 if($_SERVER['REQUEST_METHOD']!=='GET')appFail('GET required.',405);
 $call=strtoupper(trim((string)($_GET['callsign']??'')));if(!checkCall($call))appFail('Invalid station callsign.');
 $db=appDb();ensureLinkSchema($db);$station=rowById($db,'stations','callsign',$call);if(!$station)appFail('Station is not listed.',404);unset($station['address'],$station['edit_hash']);
 $q=$db->prepare('SELECT id,at,actor_type,actor,action,before_json,after_json FROM audit WHERE entity_type="station" AND entity_id=? ORDER BY id DESC LIMIT 100');$q->execute([$call]);$events=[];
 foreach($q->fetchAll(PDO::FETCH_ASSOC)as $e){$b=json_decode($e['before_json']??'null',true);$a=json_decode($e['after_json']??'null',true);unset($e['before_json'],$e['after_json']);$e['previous_status']=$b['status']??null;$e['status']=$a['status']??null;$events[]=$e;}
 $rollups=[];
 foreach(['24h'=>86400,'7d'=>604800]as $name=>$seconds){
  $q=$db->prepare('SELECT COUNT(*) AS samples,AVG(throughput_bps) AS average_throughput_bps,SUM(error_count) AS error_count,SUM(retry_count) AS retry_count,SUM(packet_count) AS packet_count,MAX(observed_at) AS last_seen FROM metric_samples WHERE station_id=? AND observed_at>=?');$q->execute([$call,gmdate('c',time()-$seconds)]);$r=$q->fetch(PDO::FETCH_ASSOC);$r['samples']=(int)$r['samples'];$r['retry_rate_percent']=$r['packet_count']>0&&$r['retry_count']!==null?100*$r['retry_count']/$r['packet_count']:null;$rollups[$name]=$r;
 }
 $links=array_values(array_filter(publicLinkData($db,time()),fn($l)=>$l['a_node']===$call||$l['z_node']===$call));appReply(['station'=>$station,'links'=>$links,'metrics'=>$rollups,'history'=>$events]);
}catch(Throwable $e){error_log('Station history: '.$e->getMessage());appFail('Station history is unavailable.',500);}
