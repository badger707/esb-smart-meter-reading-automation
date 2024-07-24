# #!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup   # pip install beautifulsoup4
import re as re
import json
import csv

meter_mprn = "my_mprn_number"
esb_user_name = "email@email.com"
esb_password = "password"
main_url = "https://myaccount.esbnetworks.ie"
historic_consumption_url = "https://myaccount.esbnetworks.ie/Api/HistoricConsumption"
file_url = 'https://myaccount.esbnetworks.ie/DataHub/DownloadHdfPeriodic'

print("[+] open session ...")
s = requests.Session()
#s.headers.update({
#    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
#  })
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
  })
#s.headers.update({
#    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
#  })
login_page = s.get(main_url, allow_redirects=True)
print("[!] Landing page Status Code: ", login_page.status_code)
result = re.findall(r"(?<=var SETTINGS = )\S*;", str(login_page.content))
settings = json.loads(result[0][:-1])
print("-"*10)
print("csrf token: ", settings['csrf'])
print("transid token: ", settings['transId'])
print("-"*10)
s.post(
    'https://login.esbnetworks.ie/esbntwkscustportalprdb2c01.onmicrosoft.com/B2C_1A_signup_signin/SelfAsserted?tx=' + settings['transId'] + '&p=B2C_1A_signup_signin',
    data={
      'signInName': esb_user_name, 
      'password': esb_password, 
      'request_type': 'RESPONSE'
    },
    headers={
      'x-csrf-token': settings['csrf'],
    },
    allow_redirects=True)
confirm_login = s.get(
    'https://login.esbnetworks.ie/esbntwkscustportalprdb2c01.onmicrosoft.com/B2C_1A_signup_signin/api/CombinedSigninAndSignup/confirmed',
    params={
      'rememberMe': False,
      'csrf_token': settings['csrf'],
      'tx': settings['transId'],
      'p': 'B2C_1A_signup_signin',
    }
  )
soup = BeautifulSoup(confirm_login.content, 'html.parser')
form = soup.find('form', {'id': 'auto'})
print("[!] Submitting login form ...")
fff=s.post(
        form['action'],
        allow_redirects=True,
        data={
          'state': form.find('input', {'name': 'state'})['value'],
          'client_info': form.find('input', {'name': 'client_info'})['value'],
          'code': form.find('input', {'name': 'code'})['value'],
        }, 
    )
print("[!] Status Code: ", fff.status_code)
user_welcome_soup = BeautifulSoup(fff.text,'html.parser')
user_elements = user_welcome_soup.find('h1', class_='esb-title-h1')
if user_elements.text[:2] == "We":
    print("[!] Confirmed User Login: ", user_elements.text)    # It should return "Welcome, Name Surname"
else:
    print("[!!!] No Welcome message, User is not logged in.")
    s.close()
h1_elem = s.get(historic_consumption_url, allow_redirects=True)
h1_elem_content = h1_elem.text
h1_elem_soup = BeautifulSoup(h1_elem_content, 'html.parser')
h1_elem_element = h1_elem_soup.find('h1', class_='esb-title-h1')
if h1_elem_element.text[:2] == "My":
    print("[+] Jumped to page: ",h1_elem_element.text),    # It should return "My energy Consumption"
else:
    print("[!] ups - something went wrong.")
    s.close()
x_headers={
  'Host': 'myaccount.esbnetworks.ie',
  'x-ReturnUrl': historic_consumption_url,
  'Referer': historic_consumption_url,
}
x_down = s.get(main_url+"/af/t",headers=x_headers)
set_cookie_header = x_down.headers.get('Set-Cookie', '')
def extract_xsrf_token(cookie_header):
    cookies = cookie_header.split(',')
    for cookie in cookies:
        if 'XSRF-TOKEN' in cookie:
            token = cookie.split('XSRF-TOKEN=')[1].split(';')[0]
            return token
    return None
xsrf_token = extract_xsrf_token(set_cookie_header)
file_headers = {
    'Referer': historic_consumption_url,
    'content-type': 'application/json',
    'x-returnurl': historic_consumption_url,
    'x-xsrf-token': xsrf_token,
    'Origin': main_url,
}
payload_data = {
    "mprn": meter_mprn,
    "searchType": "intervalkw"
}
response_data_file = s.post(file_url, headers=file_headers, json=payload_data)
s.close()
magic_data = response_data_file.content.decode("utf-8")
my_json = []
csv_reader = csv.DictReader(magic_data.split('\n'))
for row in csv_reader:
    #print(row)
    my_json.append(row)
json_out = json.dumps(my_json, indent=2)
