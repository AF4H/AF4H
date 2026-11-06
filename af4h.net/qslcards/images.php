<?php
// Discover images on every request; no database or manual list required.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
$items = [];
foreach (scandir(__DIR__ . '/images') ?: [] as $name) {
    if (preg_match('/\.(jpe?g|png|webp)$/i', $name) && is_file(__DIR__ . '/images/' . $name)) {
        $items[] = ['url' => 'images/' . rawurlencode($name), 'name' => pathinfo($name, PATHINFO_FILENAME)];
    }
}
usort($items, fn($a, $b) => strnatcasecmp($a['name'], $b['name']));
echo json_encode($items, JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);
