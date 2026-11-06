<?php
// Return one complete front-and-back card as a plain JPEG for external embeds.
$files = glob(__DIR__ . '/images/*.jpg') ?: [];
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: 0');
header('X-Content-Type-Options: nosniff');
if (!$files) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=utf-8');
    exit('No QSL cards available yet.');
}
$file = $files[random_int(0, count($files) - 1)];
header('Content-Type: image/jpeg');
header('Content-Length: ' . filesize($file));
readfile($file);
