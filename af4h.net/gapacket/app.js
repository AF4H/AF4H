'use strict';
const $=id=>document.getElementById(id), colors={online:'#269361',ready:'#367ec5',interested:'#d59427'};
const map=L.map('map').setView([32.6,-83.4],7);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
let confirmedCall='',csrf='',pin=null,stations=[],layer=L.layerGroup().addTo(map), busy=false;
const call=()=>$('callsign').value.trim().toUpperCase();
const validCall=/^(?:[KNW][0-9][A-Z]{1,3}|(?:A[A-L]|[KNW][A-Z])[0-9][A-Z]{1,3})(?:\/[0-9]{1,2})?$/;
function validateCall(){if(!validCall.test(call()))throw Error('Enter your assigned US callsign, optionally followed by /0 through /99. N0CALL is a placeholder only.');}
function message(t){$('message').textContent=t}
async function api(action,data={}){if(action!=='list')validateCall();const r=await fetch('api.php?action='+action,action==='list'?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...data,csrf})});let d;try{d=await r.json()}catch{throw Error('The server returned an unreadable response.')}if(!r.ok){const e=Error(d.error||'Request failed');e.code=d.code;throw e;}return d}
function point(lat,lng,zoom=false){if(pin)pin.setLatLng([lat,lng]);else pin=L.marker([lat,lng],{draggable:true}).addTo(map).bindTooltip('Your station — drag to adjust');if(zoom)map.setView([lat,lng],13)}
map.on('click',e=>{point(e.latlng.lat,e.latlng.lng);message('Pin selected. Review your status, then save your station.')});
function render(){layer.clearLayers();stations.forEach(s=>{const content=document.createElement('div'),title=document.createElement('strong'),line=document.createElement('p'),time=document.createElement('small');title.textContent=s.callsign;line.textContent=s.status[0].toUpperCase()+s.status.slice(1);time.textContent='Updated '+new Date(s.updated).toLocaleString();content.append(title,line,time);L.circleMarker([s.lat,s.lng],{radius:8,color:'#fff',weight:2,fillColor:colors[s.status],fillOpacity:1}).addTo(layer).bindPopup(content)});$('count').textContent=stations.length+' station'+(stations.length===1?'':'s')+' · '+stations.filter(s=>s.status==='online').length+' online'}
async function refresh(){const d=await api('list');csrf=d.csrf;stations=d.stations;render()}
async function run(fn){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await fn()}catch(e){message(e.message)}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
$('lookup').onclick=()=>run(async()=>{
 const stationCall=call(),check=await api('check',{callsign:stationCall});
 if(check.exists&&confirmedCall!==stationCall){if(!confirm(stationCall+': Callsign already registered. Update?')){message('Update canceled. Use a suffix such as '+stationCall.split('/')[0]+'/14 to add another station.');return;}confirmedCall=stationCall;}
 message('Looking up '+stationCall+' on QRZ…');
 const d=await api('lookup',{callsign:stationCall});$('address').value=d.address;
 if(check.station){point(check.station.lat,check.station.lng,true);document.querySelector('[name=status][value='+check.station.status+']').checked=true;message('Existing station loaded. QRZ filled the address; review it and save your changes.');}
 else if(d.lat!==null&&d.lng!==null&&Number.isFinite(d.lat)&&Number.isFinite(d.lng)){point(d.lat,d.lng,true);message('QRZ address loaded. Review the address and pin before saving.');}
 else{if(pin){pin.remove();pin=null}message('Address loaded. Click the map to place your station.');}
});
$('address').addEventListener('input',()=>{if(pin){pin.remove();pin=null}message('Address changed. Click the map to confirm the new station location.')});
$('callsign').addEventListener('input',()=>{confirmedCall='';$('address').value='';if(pin){pin.remove();pin=null}});
$('station').onsubmit=e=>{e.preventDefault();run(async()=>{
 if(!pin)throw Error('Click the map to confirm your station location.');
 const stationCall=call(),p=pin.getLatLng(),payload={callsign:stationCall,address:$('address').value,status:document.querySelector('[name=status]:checked').value,lat:p.lat,lng:p.lng,confirm_update:confirmedCall===stationCall};
 try{await api('save',payload);}catch(e){
  if(e.code!=='already_registered')throw e;
  if(!confirm(stationCall+': Callsign already registered. Update?')){message('Update canceled. Your existing station was not changed.');return;}
  confirmedCall=stationCall;await api('save',{...payload,confirm_update:true});
 }
 confirmedCall=stationCall;await refresh();message('Your station is saved and visible on the shared map.');
})};
$('fit').onclick=()=>{if(stations.length)map.fitBounds(L.latLngBounds(stations.map(s=>[s.lat,s.lng])),{padding:[35,35],maxZoom:12});else map.setView([32.6,-83.4],7)};
refresh().then(()=>message('Enter your callsign to add your station.')).catch(e=>message(e.message));
setInterval(()=>{if(!busy)refresh().catch(()=>{})},60000);

