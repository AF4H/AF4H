# QSL Label Printing (bash) scripts

## as used by AF4H

---

### Contents:

#### gsx190ii.ppd:

Customized CUPS print driver for the Citizen GSX-190II, based on the Epson 9-Pin PPD. All non-English translations have been removed, all non-"US Letter" paper sizes have been removed, and 2 new paper sizes were added: 

 - "Avery 4076" (2+15/16 in tall by 5 in wide) - used for the QSL confirmation labels
 - "Avery 4011" (15/16 in tall by 3+1/2 in wide) - used for address labels


#### qsl-confirmation.glabels:

The template used to generate the "Avery 4076" QSL confirmation, which is then applied to the QSL card.

---

## To-Do/Coming Soon:

Scripts will be (re)-made to do various operations:

 - Download the log file (from QRZ.COM) as ADIF and do some cleanup
 - Batch-generate QSL Confirmation labels
 - Batch-generate address labels based on address/QSL info in the users' QRZ profile and cleaned up through the USPS API (for US addresses)
