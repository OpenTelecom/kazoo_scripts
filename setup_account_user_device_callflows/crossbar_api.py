import requests
import hashlib
import getpass
import json
import os
import config
import logging

log = logging.getLogger("crossbar_api")

class CrossbarException(Exception):
    def __init__(self, r):
        self.status_code = r.status_code
        try:
            self.msg = r.json()
            self.json = r.json()
        except:
            self.msg = r.text
        log.info("crossbar request failed: %s %s %s" % (r.url, self.status_code, self.msg))
    def __str__(self):
        return "Status code: %s, Body: \n%s\n" % (self.status_code, self.msg)

class CrossbarAPI():
    BASE_URL = os.environ.get("CROSSBAR") or config.CROSSBAR_URL
    BASE_HEADERS = {'Content-Type': 'application/json'}
    headers = BASE_HEADERS

    def log_in(self):
        username = raw_input("User name for log in: ")
        password = getpass.getpass("Password for user: ")
        account_name = raw_input("Account name for log in: ")
        self.authenticate(account_name, username, password)

    def authenticate(self, account_name, username, password):
        pre_hash_string = "%s:%s" % (username, password)
        hashtoken = hashlib.md5(pre_hash_string.encode('utf-8')).hexdigest()
        json_doc = {'data': {
            'credentials': hashtoken,
            'account_name': account_name
            }}
        r = requests.put(self.BASE_URL + "user_auth", data=json.dumps(json_doc), headers=self.BASE_HEADERS)
        if r.status_code in [201, 200]:
            self.auth_token = r.json()['auth_token']
            self.auth_account_id = r.json()['data']['account_id']
            self.headers = dict(self.BASE_HEADERS.items() + {'X-Auth-Token' : self.auth_token}.items())
        else:
            print("Failed to authenticate with status code %d" % r.status_code)
            raise CrossbarException(r)

    def get(self, endpoint):
        url = self.BASE_URL + endpoint
        r = requests.get(url, headers=self.headers)
        return self._process_response(r, 200)

    def get_raw(self, endpoint, mime):
        url = self.BASE_URL + endpoint
        headers = self.headers.copy()
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.text
        raise CrossbarException(r)

    def delete(self, endpoint):
        url = self.BASE_URL + endpoint
        r = requests.delete(url, headers=self.headers)
        return self._process_response(r, 200)

    def put(self, endpoint, data):
        url = self.BASE_URL + endpoint
        r = requests.put(url, headers=self.headers, data=json.dumps({"data": data}))
        return self._process_response(r, [201, 200])

    def post(self, endpoint, data):
        url = self.BASE_URL + endpoint
        r = requests.post(url, headers=self.headers, data=json.dumps({"data": data}))
        return self._process_response(r, 200)

    def put_raw(self, endpoint, data, mime):
        url = self.BASE_URL + endpoint
        headers = self.headers.copy()
        headers['Content-Type'] = mime
        r = requests.put(url, headers=headers, data=data)
        return self._process_response(r, [201, 200])

    def post_raw(self, endpoint, data, mime):
        url = self.BASE_URL + endpoint
        headers = self.headers.copy()
        headers['Content-Type'] = mime
        r = requests.post(url, headers=headers, data=data)
        return self._process_response(r, [201, 200])

    def _process_response(self, r, statuses):
        statuses = statuses if isinstance(statuses, list) else [statuses]
        if r.status_code in statuses:
            return r.json()['data']
        else:
            raise CrossbarException(r)
