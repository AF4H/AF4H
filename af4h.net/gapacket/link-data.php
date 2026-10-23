<?php
declare(strict_types=1);
function ensureLinkSchema(PDO $db):void{
 $db->exec('CREATE TABLE IF NOT EXISTS node_links (id TEXT PRIMARY KEY,a_node TEXT NOT NULL,z_node TEXT NOT NULL,frequency_hz INTEGER,capacity_bps INTEGER NOT NULL,status TEXT NOT NULL,last_seen TEXT NOT NULL,source TEXT NOT NULL DEFAULT "telemetry",updated TEXT NOT NULL)');
}
function linkDisplayState(string $status,string $lastSeen,int $now):string{
 $seen=strtotime($lastSeen);if($seen===false)return 'disabled';$age=max(0,$now-$seen);
 if($status==='disabled'||$age>604800)return 'disabled';
 if($age>259200)return 'long_offline';
 if($status!=='online'||$age>3600)return 'offline';
 return 'online';
}
function publicLinkData(PDO $db,int $now):array{
 $links=$db->query('SELECT id,a_node,z_node,frequency_hz,capacity_bps,status,last_seen,source,updated FROM node_links ORDER BY id')->fetchAll(PDO::FETCH_ASSOC);
 foreach($links as &$link){$link['capacity_bps']=(int)$link['capacity_bps'];$link['frequency_hz']=$link['frequency_hz']===null?null:(int)$link['frequency_hz'];$link['display_state']=linkDisplayState($link['status'],$link['last_seen'],$now);}unset($link);
 return $links;
}
