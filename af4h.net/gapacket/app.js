'use strict';
const $=id=>document.getElementById(id), colors={online:'#269361',ready:'#367ec5',interested:'#d59427'};
const map=L.map('map').setView([32.6,-83.4],7);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
let confirmedCall='',csrf='',pin=null,stations=[],links=[],revision='',refreshing=false,layer=L.layerGroup().addTo(map),linkLayer=L.layerGroup().addTo(map), busy=false;
const call=()=>$('callsign').value.trim().toUpperCase();
const validCall=/^(?:[KNW][0-9][A-Z]{1,3}|(?:A[A-L]|[KNW][A-Z])[0-9][A-Z]{1,3})(?:\/[0-9]{1,2})?$/;
const callsignError='Enter a US callsign with a K, N, W, or AA–AL prefix, one digit, and 1–3 suffix letters. An optional station number is /0 through /99.';
function showCallError(show=true){
 const invalid=!validCall.test(call()),field=$('callsign'),error=$('callsign-error');
 error.textContent=show&&invalid?callsignError:'';error.hidden=!(show&&invalid);
 field.setAttribute('aria-invalid',show&&invalid?'true':'false');
 field.setCustomValidity(invalid?callsignError:'');return !invalid;
}
function validateCall(){if(!showCallError()){ $('callsign').focus();throw Error(callsignError);}}
$('callsign').addEventListener('blur',()=>showCallError(call()!==''));
$('callsign').addEventListener('invalid',e=>{e.preventDefault();showCallError();$('callsign').focus();});
$('station').addEventListener('invalid',()=>{showCallError(call()!=='' );},true);
function message(t){$('message').textContent=t}
async function api(action,data={}){if(action!=='list')validateCall();const r=await fetch('api.php?action='+action,action==='list'?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...data,csrf})});let d;try{d=await r.json()}catch{throw Error('The server returned an unreadable response.')}if(!r.ok){const e=Error(d.error||'Request failed');e.code=d.code;throw e;}return d}
function point(lat,lng,zoom=false){if(pin)pin.setLatLng([lat,lng]);else pin=L.marker([lat,lng],{draggable:true}).addTo(map).bindTooltip('Your station — drag to adjust');if(zoom)map.setView([lat,lng],13)}
map.on('click',e=>{point(e.latlng.lat,e.latlng.lng);message('Pin selected. Review your status, then save your station.')});
const linkColors={online:'#269361',offline:'#4b5055',long_offline:'#b9bdc0'};
const linkLabels={online:'Online',offline:'Offline',long_offline:'Long offline (>3 days)',disabled:'Disabled / hidden (>7 days or disabled)'};
function linkWidth(bps){return 2+8*Math.max(0,Math.min(1,Math.log(Math.max(300,Number(bps)||300)/300)/Math.log(57600/300)));}
function addText(parent,tag,text){const e=document.createElement(tag);e.textContent=text;parent.append(e);return e;}
function linkDetails(link,stationId){
 const box=document.createElement('div');box.className='link-detail';
 const other=stationId?(link.a_node===stationId?link.z_node:link.a_node):link.a_node+' ↔ '+link.z_node;
 addText(box,'strong',other+(link.source==='test'?' · TEST LINK':''));
 addText(box,'div',(link.frequency_hz===null?'Frequency not supplied':(link.frequency_hz/1000000).toLocaleString(undefined,{maximumFractionDigits:6})+' MHz')+' · '+Number(link.capacity_bps).toLocaleString()+' bps');
 addText(box,'div',linkLabels[link.display_state]+' · reported '+link.status);
 addText(box,'div','Last seen: '+new Date(link.last_seen).toLocaleString());
 const ids=new Set(stations.map(s=>s.callsign));
 if(link.display_state==='disabled')addText(box,'small','Not plotted: link disabled or last seen over 7 days ago.');
 else if(!ids.has(link.a_node)||!ids.has(link.z_node))addText(box,'small','Not plotted: '+[link.a_node,link.z_node].filter(n=>!ids.has(n)).join(', ')+' is not a listed station.');
 return box;
}
function stationDetails(s){
 const content=document.createElement('div');content.className='station-details';
 addText(content,'strong',s.callsign);addText(content,'div','Station: '+s.status);
 addText(content,'small','Updated '+new Date(s.updated).toLocaleString());
 const connected=links.filter(l=>l.a_node===s.callsign||l.z_node===s.callsign);
 addText(content,'h4',connected.length+' reported link'+(connected.length===1?'':'s'));
 if(!connected.length)addText(content,'div','No connectivity reports yet.');
 connected.forEach(l=>content.append(linkDetails(l,s.callsign)));return content;
}
function render(){
 layer.clearLayers();linkLayer.clearLayers();const byId=new Map(stations.map(s=>[s.callsign,s]));let plotted=0;
 links.forEach(l=>{
  const a=byId.get(l.a_node),z=byId.get(l.z_node);
  if(!a||!z||l.display_state==='disabled')return;
  const line=L.polyline([[a.lat,a.lng],[z.lat,z.lng]],{color:linkColors[l.display_state],weight:linkWidth(l.capacity_bps),opacity:l.display_state==='long_offline'?.7:.85,dashArray:l.display_state==='online'?null:'7 5'}).addTo(linkLayer);
  line.bindTooltip(()=>linkDetails(l),{className:'connectivity-tooltip',sticky:true}).bindPopup(()=>linkDetails(l));plotted++;
 });
 stations.forEach(s=>{
  L.circleMarker([s.lat,s.lng],{radius:8,color:'#fff',weight:2,fillColor:colors[s.status],fillOpacity:1}).addTo(layer)
   .bindTooltip(()=>stationDetails(s),{className:'connectivity-tooltip',direction:'auto',interactive:true})
   .bindPopup(()=>stationDetails(s),{maxWidth:370});
 });
 $('count').textContent=stations.length+' stations · '+plotted+' plotted links · '+stations.filter(s=>s.status==='online').length+' online stations';
}
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{const d=await api('list');csrf=d.csrf;
  if(revision!==d.revision){revision=d.revision;stations=d.stations;links=d.links||[];render();}
  $('sync').textContent='Auto-refresh every 5s · checked '+new Date().toLocaleTimeString();
 }catch(e){$('sync').textContent='Refresh failed; retrying automatically.';throw e;}finally{refreshing=false;}
}

async function run(fn){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await fn()}catch(e){message(e.message)}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
$('lookup').onclick=()=>run(async()=>{
 const stationCall=call(),check=await api('check',{callsign:stationCall});
 if(check.exists&&confirmedCall!==stationCall){if(!confirm(stationCall+': Callsign already registered. Update?')){message('Update canceled. Use a suffix such as '+stationCall.split('/')[0]+'/14 to add another station.');return;}confirmedCall=stationCall;}
 message('Looking up '+stationCall+' on QRZ…');
 const d=await api('lookup',{callsign:stationCall});$('address').value=d.address;
 if(check.station){point(check.station.lat,check.station.lng,true);document.querySelector('[name=status][value='+check.station.status+']').checked=true;updateRemovalMode();message('Existing station loaded. QRZ filled the address; review it and save your changes.');}
 else if(d.lat!==null&&d.lng!==null&&Number.isFinite(d.lat)&&Number.isFinite(d.lng)){point(d.lat,d.lng,true);message('QRZ address loaded. Review the address and pin before saving.');}
 else{if(pin){pin.remove();pin=null}message('Address loaded. Click the map to place your station.');}
});
$('address').addEventListener('input',()=>{if(pin){pin.remove();pin=null}message('Address changed. Click the map to confirm the new station location.')});
$('callsign').addEventListener('input',()=>{if(showCallError(call()!=='' )&&$('message').textContent===callsignError)message('Callsign format is valid. Look up QRZ or enter your station address.');confirmedCall='';$('address').value='';if(pin){pin.remove();pin=null}});
$('station').onsubmit=e=>{e.preventDefault();run(async()=>{
 validateCall();
 const removing=document.querySelector('[name=status]:checked').value==='remove';
 if(!removing&&!pin)throw Error('Click the map to confirm your station location.');
 const stationCall=call(),p=pin?pin.getLatLng():{lat:null,lng:null},payload={callsign:stationCall,address:$('address').value,status:document.querySelector('[name=status]:checked').value,lat:p.lat,lng:p.lng,confirm_update:confirmedCall===stationCall};
 let result;try{result=await api('save',payload);}catch(e){
  if(e.code!=='already_registered')throw e;
  if(!confirm(stationCall+': Callsign already registered. Update?')){message('Update canceled. Your existing station was not changed.');return;}
  confirmedCall=stationCall;result=await api('save',{...payload,confirm_update:true});
 }
 confirmedCall='';await refresh();message(result.message);
})};
$('fit').onclick=()=>{if(stations.length)map.fitBounds(L.latLngBounds(stations.map(s=>[s.lat,s.lng])),{padding:[35,35],maxZoom:12});else map.setView([32.6,-83.4],7)};
refresh().then(()=>message('Enter your callsign to add your station.')).catch(e=>message(e.message));
setInterval(()=>{if(!document.hidden)refresh().catch(()=>{})},5000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh().catch(()=>{});});
window.addEventListener('focus',()=>refresh().catch(()=>{}));


function updateRemovalMode(){const removing=document.querySelector('[name=status]:checked').value==='remove';$('address').required=!removing;$('address').disabled=removing;$('save').textContent=removing?'Email removal confirmation':'Email confirmation';}
document.querySelectorAll('[name=status]').forEach(r=>r.addEventListener('change',updateRemovalMode));updateRemovalMode();
