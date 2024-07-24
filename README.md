#  esb-smart-meter-reading-automation

![](https://github.com/badger707/esb-smart-meter-reading-automation/blob/main/esb-smart-meter.png)
<br><br>
# How to read your Smart Meter data automatically?
<br>

Simple Python code to download your smart electricy meter readings/data from ESB Networks user portal.

Code consists of 2 main processes - (1) user login to web portal, (2) historic file download.

(1) Login to web portal script part is based/taken from this code, [link](https://gist.github.com/schlan/f72d823dd5c1c1d19dfd784eb392dded).

(2) Since ESB Networks updated User Portal and the proccess of historic file download, old aproach to download the file no longer works.<br>
This Python script is adjusted to work with new download structure/proccess as of 24-Jul-2024

# Requirements<br>
* You need to create account with ESB here https://myaccount.esbnetworks.ie <br>
* In your account, link your electricity meter MPRN
<br><br>
# Script setup<br>
* update MPRN, user and password in the script.

<br><br>
UPDATES: <br>
* 24-Jul-2024 -- Python script changes to accomodate ESB Networks user portal changes to download historic usage file. 
* 09-May-2024 -- there was some changes on ESB side and this broke CSV parsing in script, fixed & tested, JSON output works as expected.


