#!/usr/bin/env python

"""
    Implementation of the new FritzBox Hash-Authentication
    No error handling
"""
try:
    from md5 import md5
except ImportError:
    from hashlib import md5
try:
    from httplib import HTTPConnection
except ImportError:
    from http.client import HTTPConnection
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from netrc import netrc
import xml.etree.ElementTree as ET


class CommunicationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class LoginError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FritzBoxWeb(object):
    
    def __init__(self, host='fritz.box'):
        self.host = host
        self.user        = None
        self.session_id  = None
        self._connection = None

    def connect(self):
        if not self._connection:
            self._connection = HTTPConnection(self.host)
        return self._connection

    def login(self, user, password):
        challenge = self.get_challenge()
        self.session_id = self.create_session(user, password)

    @classmethod
    def calculate_challenge_response(cls, challenge, password):
        response_encoded = (u'%s-%s'% (challenge, password)).encode('utf-16LE')
        response_hash    = md5(response_encoded).hexdigest()
        return u'%s-%s' % (challenge, response_hash)

    def get_challenge(self):
        try:
            conn = self.connect()
            conn.request("GET", '/login_sid.lua')
            r1 = conn.getresponse()
            if r1.status == 200:
                data = r1.read()
        except:
            raise CommunicationError('Could not connect to Fritzbox')

        try:
            root = ET.fromstring(data)
            challenge = root.findall('Challenge')[0].text
        except:
            raise CommunicationError('Challenge could not be read')
        
        return challenge


    def create_session(self, user, password):
        conn = self.connect() 

        challenge = self.get_challenge()
        response = FritzBoxWeb.calculate_challenge_response(challenge, password)
        headers = {"Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/plain"}
        params = urlencode({'user': user, 'response': response})
        conn.request("POST", '/login_sid.lua', params, headers)
        r1 = conn.getresponse()
        response_xml = r1.read()
        root = ET.fromstring(response_xml)
        return root.findall('SID')[0].text


if __name__ == '__main__':
    host = '192.168.178.1'
    
    nrc = netrc()
    (user, account, password)  = nrc.authenticators(host)

    fb = FritzBoxWeb(host)
    fb.login(user, password)

    print(fb.session_id)

    conn = fb.connect()
    conn.request("GET", '/home/home.lua?sid={session_id}'.format(session_id=fb.session_id))

    r = conn.getresponse()
    print(r.read())

    print(fb.session_id)
    #fb2 = FritzBox()
    #print fb2.get_challenge()
    #print fb.login(user, "123")


