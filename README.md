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
## Setup<br>
This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

1. Install dependencies:<br>
```
uv sync
```
2. Copy the example environment file and fill in your details:<br>
```
cp .env.example .env
```
3. Edit `.env` with your ESB account credentials and meter MPRN:<br>
```
ESB_USERNAME=email@example.com
ESB_PASSWORD=your-password
ESB_MPRN=10000000000
```
The `.env` file is git-ignored and never committed.

4. Run the script:<br>
```
uv run esb-smart-meter-reader.py
```

Output goes to stdout — redirect with the shell to save to a file:
```
uv run esb-smart-meter-reader.py > readings.json
uv run esb-smart-meter-reader.py --format csv > readings.csv
```

## CLI options<br>
| Option | Description |
| --- | --- |
| `--format json\|csv` | Output format (default: `json`). |
| `--help` | Show all options. |

## Configuration (`.env`)<br>
| Variable | Description |
| --- | --- |
| `ESB_USERNAME` | Your ESB Networks account email. |
| `ESB_PASSWORD` | Your ESB Networks account password. |
| `ESB_MPRN` | The MPRN of the meter to read. |
| `ESB_SEARCH_TYPE` | Dataset to download (default `intervalkwh`). |
| `ESB_USER_AGENT` | Optional User-Agent override (has a sensible default). |
| `LOG_LEVEL` | Logging verbosity: `DEBUG`, `INFO` (default), `WARNING`, `ERROR`. |

## Debug Mode for troubleshooting
* Set `LOG_LEVEL=DEBUG` in `.env` to see extended info of what the script is doing and sending/receiving.

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
* 26-Jun-2026 -- Refactored: credentials/options moved to a `.env` file, switched to `uv`, replaced `debug_mode` prints with the `logging` module, and split the script into functions.
* 28-Aug-2025 -- It seems there is some "User Agent" version validation on the server side, script fails when trying to connect with old/outdated "User Agent". Script code updated to use the latest agent. If you run into issues/errors - try to update the "User Agent" string and see if this resolves the error.
* 04-Jan-2025 -- Reworked login and file download proccess due to Nov'24 portal changes.
* 24-Jul-2024 -- Python script changes to accomodate ESB Networks user portal changes to download historic usage file. 
* 09-May-2024 -- there was some changes on ESB side and this broke CSV parsing in script, fixed & tested, JSON output works as expected.


