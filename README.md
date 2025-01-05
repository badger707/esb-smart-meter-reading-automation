#  esb-smart-meter-reading-automation

![](https://github.com/badger707/esb-smart-meter-reading-automation/blob/main/esb-smart-meter.png)
<br><br>
## How to read your Smart Meter data automatically?
Simple Python code to download your smart electricy meter readings/data from ESB Networks user portal.
<br>
## Requirements<br>
* You need to create account with ESBN here https://myaccount.esbnetworks.ie <br>
* In your account, link your electricity meter MPRN
<br><br>
## Script Setup<br>
* update MPRN, user and password in the script:<br>
```
meter_mprn = "mprn_number"
esb_user_name = "email@email.com"
esb_password = "password"
```

## Output Format<br>
* Either CSV of JSON. Select required format by uncommenting one of last 2 rows where it says: <br>
```
###/ Select file format of your choice /###
#print(csv_file)
print(json_file)
```

## Debug Mode for troubleshooting
* Set debug_mode to True if you want to see extended info of what sript is doing and sending/receiving.
````
## Debug Mode print messages, set to True or False ##
debug_mode=False
````

## Error Messages
* When things goes wrong and User Portal starts serving human verification pages, script will stop with one or another error message based on received response content analysis:
````
 [Script Message] Unable to reach login page -- too many retries (max=2 in 24h) or prior sessions was not closed properly. Please try again after midnight.
````
````
 [FAILED] Unable to get full set of required cookies -- too many retries (captcha?) or prior sessions was not closed properly. Please wait 6 hours for server to timeout and try again.
````

## Known Limitations<br>
* ESBN User Portal have enabled human verification process for logins since around Nov'24, this creates inconvenience/chalenges regardless of what you use -- standard web browser or script like this.
* Server side limit: it does allow you to make only 2 clean logins per one IP per 24 hours without triggering human verification or captcha traps.
* Trying to make 3 or more logins during the day - server will start serving human verification pages or captcha or complain about disabled javascript or disabled cookies on your side. This script will detect this and will provide comments in console/terminal and will terminate/stop.
* Server side timers/blockers/limits resets once a day at midnight - plan your workflow accordingly.
  

## UPDATES: <br>
* 04-Jan-2025 -- Reworked login and file download proccess due to Nov'24 portal changes.
* 24-Jul-2024 -- Python script changes to accomodate ESB Networks user portal changes to download historic usage file. 
* 09-May-2024 -- there was some changes on ESB side and this broke CSV parsing in script, fixed & tested, JSON output works as expected.


