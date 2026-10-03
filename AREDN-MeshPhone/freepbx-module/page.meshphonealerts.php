<?php
if (!defined('FREEPBX_IS_AUTH')) { die('No direct script access allowed'); }
$path = '/var/lib/meshphone-router/status.json';
$data = is_readable($path) ? json_decode(file_get_contents($path), true) : null;
function h($v) { return htmlspecialchars((string)$v, ENT_QUOTES, 'UTF-8'); }
$unmatched = $data['unmatched'] ?? [];
$conflicts = $data['conflicts'] ?? [];
$ok = ($data['ok'] ?? false) && count($unmatched) === 0 && count($conflicts) === 0;
echo '<div class="container-fluid">';
echo '<h2>MeshPhone Alerts</h2>';
if (!$data) { echo '<div class="alert alert-danger"><strong>MeshPhone status unavailable.</strong></div>'; }
elseif (!$ok) { echo '<div class="alert alert-danger"><strong>MeshPhone peer attention required.</strong>'; if (count($unmatched)) echo ' Unmatched peers: '.count($unmatched).'.'; if (count($conflicts)) echo ' Mapping conflicts: '.count($conflicts).'.'; echo '</div>'; }
else { echo '<div class="alert alert-success"><strong>MeshPhone peer discovery is healthy.</strong></div>'; }
if ($data) {
 echo '<p>Last update: '.h($data['updated_at'] ?? '').'</p>';
 echo '<h3>Matched peers</h3><table class="table table-striped"><tr><th>Peer</th><th>Host</th><th>Office</th><th>Confidence</th></tr>';
 foreach (($data['matched'] ?? []) as $r) echo '<tr><td>'.h($r['peer']??'').'</td><td>'.h($r['host']??'').'</td><td>'.h($r['office']??'').'</td><td>'.h($r['confidence']??'').'</td></tr>';
 echo '</table>';
 if ($unmatched) { echo '<h3>Unmatched peers</h3><table class="table table-striped"><tr><th>Peer</th><th>Host</th><th>Reason</th></tr>'; foreach ($unmatched as $r) echo '<tr><td>'.h($r['peer']??'').'</td><td>'.h($r['host']??'').'</td><td>'.h($r['reason']??'').'</td></tr>'; echo '</table>'; }
 if ($conflicts) { echo '<h3>Mapping conflicts</h3><table class="table table-striped"><tr><th>Office</th><th>Existing</th><th>Discovered</th></tr>'; foreach ($conflicts as $r) echo '<tr><td>'.h($r['office']??'').'</td><td>'.h($r['existing']??'').'</td><td>'.h($r['discovered']??'').'</td></tr>'; echo '</table>'; }
}
echo '</div>';
?>
