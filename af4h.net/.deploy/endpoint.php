<?php
// Installed as /deploy.php; deployment never overwrites this control endpoint.
declare(strict_types=1);
ini_set('display_errors','0');
header('Content-Type: application/json');header('Cache-Control: no-store');
set_time_limit(100);umask(0077);
function answer($code,$message){http_response_code($code);echo json_encode(['message'=>$message]);exit;}
function download($url,$limit=20000000){
 $c=curl_init($url);$body='';curl_setopt_array($c,[CURLOPT_USERAGENT=>'AF4H-site-deployment/1.0',CURLOPT_CONNECTTIMEOUT=>8,CURLOPT_TIMEOUT=>40,CURLOPT_FOLLOWLOCATION=>false,CURLOPT_WRITEFUNCTION=>function($ch,$chunk)use(&$body,$limit){if(strlen($body)+strlen($chunk)>$limit)return 0;$body.=$chunk;return strlen($chunk);}]);
 $ok=curl_exec($c);$code=curl_getinfo($c,CURLINFO_HTTP_CODE);curl_close($c);if(!$ok||$code!==200)throw new RuntimeException('Upstream request failed');return $body;
}
function b64($s){$v=base64_decode(strtr($s,'-_','+/'),true);if($v===false)throw new RuntimeException('Invalid encoding');return $v;}
function der($tag,$value){$n=strlen($value);$len=$n<128?chr($n):chr(0x80+strlen(ltrim(pack('N',$n),"\0"))).ltrim(pack('N',$n),"\0");return chr($tag).$len.$value;}
function integer($v){$v=ltrim($v,"\0");if($v===''||(ord($v[0])&128))$v="\0".$v;return der(2,$v);}
function keyPem($k){$rsa=der(48,integer(b64($k['n'])).integer(b64($k['e'])));$spki=der(48,hex2bin('300d06092a864886f70d0101010500').der(3,"\0".$rsa));return "-----BEGIN PUBLIC KEY-----\n".chunk_split(base64_encode($spki),64,"\n")."-----END PUBLIC KEY-----\n";}
function allowed($path){
 if(!preg_match('~^[A-Za-z0-9_-]+(?:[./][A-Za-z0-9_-]+)*\.[A-Za-z0-9]+$~D',$path))return false;
 foreach(explode('/',$path)as $part)if($part==='private'||$part==='backups'||str_starts_with($part,'.'))return false;
 if(in_array(strtolower(basename($path)),['config.php','config.example.php','deploy.php'],true))return false;
 return in_array(strtolower(pathinfo($path,PATHINFO_EXTENSION)),['html','css','js','php','svg','png','jpg','jpeg','webp','gif','ico','woff','woff2','txt','json'],true);
}
if($_SERVER['REQUEST_METHOD']!=='POST')answer(405,'POST required');
$auth=$_SERVER['HTTP_AUTHORIZATION']??$_SERVER['REDIRECT_HTTP_AUTHORIZATION']??'';
if(!preg_match('/^Bearer ([A-Za-z0-9_.-]{100,16000})$/D',$auth,$matches))answer(401,'GitHub Actions identity required');
try{
 $parts=explode('.',$matches[1]);if(count($parts)!==3)answer(401,'Invalid identity');
 [$h,$p,$sig]=$parts;$header=json_decode(b64($h),true);$claims=json_decode(b64($p),true);
 if(($header['alg']??'')!=='RS256'||!is_array($claims))answer(401,'Invalid identity');
 $keys=json_decode(download('https://token.actions.githubusercontent.com/.well-known/jwks',100000),true)['keys'];$verified=false;
 foreach($keys as $key)if($key['kid']===($header['kid']??'')&&$key['kty']==='RSA'){$verified=openssl_verify($h.'.'.$p,b64($sig),keyPem($key),OPENSSL_ALGO_SHA256)===1;break;}
 if(!$verified)answer(401,'Invalid signature');
 $expected=['iss'=>'https://token.actions.githubusercontent.com','aud'=>'https://af4h.net/deploy.php','repository'=>'AF4H/AF4H','repository_id'=>'775101286','repository_owner_id'=>'164239835','ref'=>'refs/heads/main','workflow_ref'=>'AF4H/AF4H/.github/workflows/deploy-af4h.yml@refs/heads/main'];
 foreach($expected as $name=>$value)if((string)($claims[$name]??'')!==$value)answer(403,'Identity not authorized');
 if(!in_array($claims['event_name']??'',['push','workflow_dispatch'],true)||($claims['exp']??0)<time()||($claims['nbf']??PHP_INT_MAX)>time()+30||($claims['iat']??0)<time()-600)answer(403,'Identity expired or not authorized');
 $sha=$claims['sha']??'';if(!preg_match('/^[a-f0-9]{40}$/D',$sha))answer(400,'Invalid commit');
 $private=dirname(__DIR__).'/private/gapacket';$lock=fopen($private.'/deploy.lock','c');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))answer(409,'Deployment in progress');
 $head=json_decode(download('https://api.github.com/repos/AF4H/AF4H/git/ref/heads/main',100000),true);
 if(($head['object']['sha']??'')!==$sha)answer(409,'A newer commit is on main; deploy its workflow run instead');
 $stateFile=$private.'/deployment.json';$previous=is_file($stateFile)?json_decode(file_get_contents($stateFile),true):[];
 if(($previous['sha']??'')===$sha)answer(200,'Already deployed '.$sha);
 $stage=$private.'/deploy-'.bin2hex(random_bytes(8));mkdir($stage,0700);
 $archive=$stage.'/source.zip';file_put_contents($archive,download('https://codeload.github.com/AF4H/AF4H/zip/'.$sha));
 $zip=new ZipArchive();if($zip->open($archive)!==true)throw new RuntimeException('Invalid archive');
 $prefix='AF4H-'.$sha.'/af4h.net/';$files=[];$total=0;
 for($i=0;$i<$zip->numFiles;$i++){
  $stat=$zip->statIndex($i);$name=$stat['name'];if(!str_starts_with($name,$prefix))continue;$path=substr($name,strlen($prefix));if(!allowed($path))continue;
  if($stat['size']>5000000||($total+=$stat['size'])>15000000)throw new RuntimeException('Website files too large');
  $data=$zip->getFromIndex($i);if($data===false)throw new RuntimeException('Cannot read source');
  $file=$stage.'/files/'.$path;if(!is_dir(dirname($file)))mkdir(dirname($file),0700,true);file_put_contents($file,$data);
  if(str_ends_with($path,'.php')){$out=[];$code=0;exec('/usr/bin/php -l '.escapeshellarg($file).' 2>&1',$out,$code);if($code!==0)throw new RuntimeException('PHP syntax check failed');}
  $files[]=$path;
 }
 $zip->close();if(!in_array('index.html',$files,true)||!in_array('gapacket/api.php',$files,true))throw new RuntimeException('Required website files missing');
 // Stage the complete release before replacing any served file. Keep private backups.
 $old=[];$changed=[];
 try{
  foreach(array_unique(array_merge($files,$previous['files']??[]))as $path){if(!allowed($path))continue;$dest=__DIR__.'/'.$path;$parent=dirname($dest);$real=realpath($parent);if($real!==false&&$real!==__DIR__&&!str_starts_with($real,__DIR__.'/'))throw new RuntimeException('Unsafe destination');if(is_link($dest))throw new RuntimeException('Symbolic link destination');
   $old[$path]=is_file($dest)?file_get_contents($dest):null;
   if($old[$path]!==null){$backup=$stage.'/backup/'.$path;if(!is_dir(dirname($backup)))mkdir(dirname($backup),0700,true);file_put_contents($backup,$old[$path]);}
   $changed[]=$path;
   if(in_array($path,$files,true)){if(!is_dir($parent))mkdir($parent,0755,true);$temp=$parent.'/.deploy-'.bin2hex(random_bytes(5));if(!copy($stage.'/files/'.$path,$temp))throw new RuntimeException('Write failed');chmod($temp,0644);if(!rename($temp,$dest))throw new RuntimeException('Publish failed');}
   elseif(is_file($dest)&&!unlink($dest))throw new RuntimeException('Removal failed');
  }
  $state=json_encode(['sha'=>$sha,'files'=>$files,'deployed_at'=>gmdate('c'),'backup'=>basename($stage)]);file_put_contents($stateFile.'.tmp',$state);rename($stateFile.'.tmp',$stateFile);
 }catch(Throwable $e){foreach(array_reverse($changed)as $path){$dest=__DIR__.'/'.$path;if($old[$path]===null){if(is_file($dest))unlink($dest);}else file_put_contents($dest,$old[$path]);}throw $e;}
 unlink($archive);
 // Retain the latest five private deployment directories.
 $dirs=glob($private.'/deploy-*',GLOB_ONLYDIR);usort($dirs,fn($a,$b)=>filemtime($b)<=>filemtime($a));foreach(array_slice($dirs,5)as $dir){$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir,FilesystemIterator::SKIP_DOTS),RecursiveIteratorIterator::CHILD_FIRST);foreach($it as $item){$item->isDir()?rmdir($item->getPathname()):unlink($item->getPathname());}rmdir($dir);}
 answer(200,'Deployed '.$sha.' ('.count($files).' files)');
}catch(Throwable $e){error_log('AF4H deployment: '.$e->getMessage());answer(500,'Deployment failed; check the server error log');}
