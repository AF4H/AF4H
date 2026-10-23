'use strict';
const $=id=>document.getElementById(id), colors={online:'#269361',ready:'#367ec5',interested:'#d59427'};
const map=L.map('map').setView([32.6,-83.4],7);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
let csrf='',pin=null,stations=[],layer=L.layerGroup().addTo(map), busy=false;
const call=()=>$('callsign').value.trim().toUpperCase();
function stored(){try{return localStorage.getItem('gapacket:'+call())||''}catch{return ''}}
function token(){return $('key').value.trim()||stored()}
function message(t){$('message').textContent=t}
async function api(action,data={}){const r=await fetch('api.php?action='+action,action==='list'?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...data,csrf})});let d;try{d=await r.json()}catch{throw Error('The server returned an unreadable response.')}if(!r.ok)throw Error(d.error||'Request failed');return d}
function point(lat,lng,zoom=false){if(pin)pin.setLatLng([lat,lng]);else pin=L.marker([lat,lng],{draggable:true}).addTo(map).bindTooltip('Your station — drag to adjust');if(zoom)map.setView([lat,lng],13)}
map.on('click',e=>{point(e.latlng.lat,e.latlng.lng);message('Pin selected. Review your status, then save your station.')});
function render(){layer.clearLayers();stations.forEach(s=>{const content=document.createElement('div'),title=document.createElement('strong'),line=document.createElement('p'),time=document.createElement('small');title.textContent=s.callsign;line.textContent=s.status[0].toUpperCase()+s.status.slice(1);time.textContent='Updated '+new Date(s.updated).toLocaleString();content.append(title,line,time);L.circleMarker([s.lat,s.lng],{radius:8,color:'#fff',weight:2,fillColor:colors[s.status],fillOpacity:1}).addTo(layer).bindPopup(content)});$('count').textContent=stations.length+' station'+(stations.length===1?'':'s')+' · '+stations.filter(s=>s.status==='online').length+' online'}
async function refresh(){const d=await api('list');csrf=d.csrf;stations=d.stations;render()}
async function run(fn){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await fn()}catch(e){message(e.message)}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
$('lookup').onclick=()=>run(async()=>{message('Looking up '+call()+' on QRZ…');const d=await api('lookup',{callsign:call()});$('address').value=d.address;if(d.lat!==null&&d.lng!==null&&Number.isFinite(d.lat)&&Number.isFinite(d.lng)){point(d.lat,d.lng,true);message('QRZ address loaded. Review the address and pin before saving.')}else{if(pin){pin.remove();pin=null}message('Address loaded. Click the map to place your station.')}});
$('address').addEventListener('input',()=>{if(pin){pin.remove();pin=null}message('Address changed. Click the map to confirm the new station location.')});
$('callsign').addEventListener('input',()=>{$('key').value='';$('keybox').hidden=true;$('address').value='';if(pin){pin.remove();pin=null}});
$('station').onsubmit=e=>{e.preventDefault();run(async()=>{if(!pin)throw Error('Click the map to confirm your station location.');const p=pin.getLatLng(),d=await api('save',{callsign:call(),address:$('address').value,status:document.querySelector('[name=status]:checked').value,lat:p.lat,lng:p.lng,token:token()});try{localStorage.setItem('gapacket:'+call(),d.token)}catch{}$('key').value=d.token;$('savedkey').value=d.token;$('keybox').hidden=false;await refresh();message('Your station is saved and visible on the shared map. Keep your edit key.');})};
$('restore').onclick=()=>run(async()=>{const d=await api('mine',{callsign:call(),token:token()});$('address').value=d.address;await refresh();const s=stations.find(s=>s.callsign===call());if(s){point(s.lat,s.lng,true);document.querySelector('[name=status][value='+s.status+']').checked=true}message('Station loaded. Make your changes and save.');});
$('remove').onclick=()=>run(async()=>{if(!confirm('Remove '+call()+' from the shared map?'))return;await api('delete',{callsign:call(),token:token()});try{localStorage.removeItem('gapacket:'+call())}catch{}if(pin){pin.remove();pin=null}$('keybox').hidden=true;await refresh();message('Your station has been removed.');});
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('savedkey').value);message('Edit key copied. Store it somewhere private.')}catch{$('savedkey').select();message('Select and copy the edit key.')}};
$('fit').onclick=()=>{if(stations.length)map.fitBounds(L.latLngBounds(stations.map(s=>[s.lat,s.lng])),{padding:[35,35],maxZoom:12});else map.setView([32.6,-83.4],7)};
refresh().then(()=>message('Enter your callsign to add your station.')).catch(e=>message(e.message));
setInterval(()=>{if(!busy)refresh().catch(()=>{})},60000);
