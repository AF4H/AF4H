<?php
declare(strict_types=1);
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
  $text="From: AF4H Packet Map <af4h@af4h.net>\r\nTo: ".$recipient."\r\nSubject: ".$subject."\r\nDate: ".date(DATE_RFC2822)."\r\nMessage-ID: <".bin2hex(random_bytes(16))."@af4h.net>\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nAuto-Submitted: auto-generated\r\nX-Mailer: AF4H Station Map\r\nContent-Transfer-Encoding: quoted-printable\r\n\r\n".preg_replace('/^\\./m','..',quoted_printable_encode(str_replace("\n","\r\n",str_replace(["\r\n","\r"],"\n",$body))));
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
