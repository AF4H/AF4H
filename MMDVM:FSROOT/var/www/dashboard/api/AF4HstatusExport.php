<?php
include_once $_SERVER['DOCUMENT_ROOT'].'/config/config.php';          // MMDVMDash Config
include_once $_SERVER['DOCUMENT_ROOT'].'/mmdvmhost/tools.php';        // MMDVMDash Tools
include_once $_SERVER['DOCUMENT_ROOT'].'/mmdvmhost/functions.php';    // MMDVMDash Functions
include_once $_SERVER['DOCUMENT_ROOT'].'/config/language.php';        // Translation Code

echo "DMR: ";
if (checkDMRLogin("MMDVMHost") > 0) { echo "OFFLINE"; }
else { echo "ONLINE"; }
echo "<br />";

echo "DAPNET: ";
if (!isProcessRunning("DAPNETGateway")) { echo "OFFLINE"; }
else { echo "ONLINE"; } 
echo "<br />";


?>


