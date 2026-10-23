// Public station history and measured telemetry; private addresses stay server-side.
let historyDialog=null,historyStation=null,historyGeneration=0;
function historyElement(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
function metricValue(value,suffix=''){return value===null||value===undefined?'Not reported':Number(value).toLocaleString(undefined,{maximumFractionDigits:1})+suffix;}
async function openStationHistory(callsign){
 historyStation=callsign;
 if(!historyDialog){historyDialog=historyElement('dialog');historyDialog.className='station-history-dialog';historyDialog.setAttribute('aria-label','Station history and telemetry');document.body.append(historyDialog);historyDialog.addEventListener('close',()=>{historyStation=null;historyGeneration++});}
 if(!historyDialog.open)historyDialog.showModal();
 await loadStationHistory(callsign);
}
async function loadStationHistory(callsign){
 const generation=++historyGeneration;const scroll=historyDialog.scrollTop;
 const close=historyElement('button','Close');close.type='button';close.className='history-close';close.onclick=()=>historyDialog.close();
 const header=historyElement('div');header.className='history-heading';header.append(historyElement('h2',callsign),close);
 const body=historyElement('div');body.append(historyElement('p','Loading station history…'));historyDialog.replaceChildren(header,body);
 try{
  const response=await fetch('history.php?callsign='+encodeURIComponent(callsign),{cache:'no-store'});const d=await response.json();if(!response.ok)throw Error(d.error||'History unavailable');
  if(generation!==historyGeneration||historyStation!==callsign)return;
  body.replaceChildren();const status=historyElement('p','Station status: '+d.station.status+' · updated '+readableTime(d.station.updated));body.append(status);
  body.append(historyElement('h3','Measured telemetry'));
  body.append(historyElement('p','Averages use reported samples. Counts are totals for reported intervals; missing measurements are not treated as zero.'));
  const grid=historyElement('div');grid.className='metrics-grid';
  for(const [window,label]of [['24h','Last 24 hours'],['7d','Last 7 days']]){
   const m=d.metrics[window],card=historyElement('section');card.append(historyElement('h4',label));
   detailRow(card,'Samples',m.samples.toLocaleString());detailRow(card,'Avg. throughput',metricValue(m.average_throughput_bps,' bps'));detailRow(card,'Errors',metricValue(m.error_count));detailRow(card,'Retries',metricValue(m.retry_count));detailRow(card,'Retry rate',metricValue(m.retry_rate_percent,'%'));detailRow(card,'Last report',m.last_seen?readableTime(m.last_seen):'Not reported');grid.append(card);
  }
  body.append(grid);body.append(historyElement('p','Retry rate = retries ÷ packets reported in the same window. Raw telemetry is retained for 30 days.'));
  body.append(historyElement('h3','Reported connections'));
  if(!d.links.length)body.append(historyElement('p','No link reports.'));d.links.forEach(l=>body.append(linkDetails(l,callsign)));
  body.append(historyElement('h3','Station history'));
  if(!d.history.length)body.append(historyElement('p','No recorded history yet.'));
  d.history.forEach(e=>{const item=historyElement('div');item.className='history-event';item.append(historyElement('strong',e.action==='baseline'?'Existing station baseline':e.action[0].toUpperCase()+e.action.slice(1)));item.append(historyElement('div',new Date(e.at).toLocaleString()+' · '+e.actor_type.replace('_',' ')+' '+e.actor));if(e.status||e.previous_status)item.append(historyElement('div','Status: '+(e.previous_status||'—')+' → '+(e.status||'removed')));body.append(item)});
  body.append(historyElement('small','History starts when auditing was enabled. Latest 100 events shown. Emails, addresses, and credentials are not public.'));
  historyDialog.scrollTop=scroll;
 }catch(e){if(generation===historyGeneration)body.replaceChildren(historyElement('p',e.message));}
}
