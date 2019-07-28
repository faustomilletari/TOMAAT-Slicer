import socket
import ssl
import requests
import sys
from requests_toolbelt.adapters.fingerprint import FingerprintAdapter

"""
   SSLUtil exposes GET and POST methods from requests that support HTTPS
   verified by global certificate chain or by certificate fingerprinting.
"""


class SSLUtil:
    fingerprintsLocal = {}
    fingerprintsGlobal = {}

    '''
    # add example fingerprint
    fingerprintsLocal.update(
        {
            "B6:CA:B9:2E:B7:30:81:E3:DE:D6:FB:6A:CC:E7:AA:63:1B:0D:C5:24:C8:B3:66:1E:77:0C:80:D4:9C:62:EC:BB":
                {
                    "port": 443,
                    "host": "self-signed.badssl.com"
                },
        }

    )
    '''

    @staticmethod
    def get(url, allow_mitm=False, **kwargs):
        if not allow_mitm:
            fingerprint_info = SSLUtil.requestFingerprintFromURL(url)
            if SSLUtil.__compare_known_fingerprints__(fingerprint_info):
                # known fingerprint -> skip check
                _,_,fp = fingerprint_info
                s = requests.Session()
                s.verify = False
                s.mount(url, FingerprintAdapter(fp))
                print("Execute GET by known fingerprint")
                r = s.get(url, **kwargs)
                s.close()
                return r
            else:
                # try global certificate
                s = requests.Session()
                s.verify = True
                print("Execute GET by global HTTPS CERT system")
                r = s.get(url, **kwargs)
                s.close()
                return r
        else:
            # dangerous
            s = requests.Session()
            s.verify = False
            print("Execute GET UNSAFE")
            r = s.get(url, **kwargs)
            s.close()
            return r

    @staticmethod
    def post(url, allow_mitm=False, **kwargs):
        if not allow_mitm:
            fingerprint_info = SSLUtil.requestFingerprintFromURL(url)
            if SSLUtil.__compare_known_fingerprints__(fingerprint_info):
                # known fingerprint -> skip check
                _,_,fp = fingerprint_info
                s = requests.Session()
                s.verify = False
                s.mount(url, FingerprintAdapter(fp))
                print("Execute POST by known fingerprint")
                r = s.post(url, **kwargs)
                s.close()
                return r
            else:
                # try global certificate
                s = requests.Session()
                s.verify = True
                print("Execute POST by global HTTPS CERT system")
                r = s.post(url, **kwargs)
                s.close()
                return r
        else:
            # dangerous
            s = requests.Session()
            s.verify = False
            print("Execute POST UNSAFE")
            r = s.post(url, **kwargs)
            s.close()
            return r

    @staticmethod
    def requestFingerprintFromURL(url):
        # extract hostname / port
        if sys.version_info.major == 2:
            from urlparse import urlparse
        else:
            from urllib.parse import urlparse
        url_info = urlparse(url)

        if url_info.scheme != "https":
            return ""

        hostname = url_info.hostname
        port = url_info.port if url_info.port else 443

        # get server certificate
        import OpenSSL.crypto
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            s = ctx.wrap_socket(socket.socket(), server_hostname=hostname)
            s.connect((hostname, port))
            der = s.getpeercert(True)
            s.close()

            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1,der)
            cert_hash = x509.digest("sha256").decode("ASCII").upper()

            return hostname, port, cert_hash
        except:
            return hostname, port, ""

    @staticmethod
    def __compare_known_fingerprints__(fingerprint_info):
        hst, prt, fp = fingerprint_info
        fp = fp.upper()
        hst = hst.lower()
        fingerprints = SSLUtil.__getFingerprints__()
        return fp in fingerprints.keys() and fingerprints[fp]["host"] == hst and fingerprints[fp]["port"] == prt

    @staticmethod
    def __getFingerprints__():
        fp = {}
        fp.update(SSLUtil.fingerprintsGlobal)
        fp.update(SSLUtil.fingerprintsLocal)
        return fp

    @staticmethod
    def loadFingerprintsFromFile(filepath):
        import json
        if sys.version_info.major == 2:
            with open(filepath,"rb") as f:
                local_fingerprints = json.load(f)
        else:
            with open(filepath,"r",encoding="utf-8") as f:
                local_fingerprints = json.load(f)
        SSLUtil.fingerprintsLocal = local_fingerprints

    @staticmethod
    def loadFingerprintsFromCloud():
        print("TODO: implement cloud fingerprint store")

SSLUtil.loadFingerprintsFromCloud()

if __name__ == "__main__":
    #print(SSLUtil.get("https://self-signed.badssl.com/",verify=False).text)
    print(SSLUtil.get("https://localhost:9001/interface").text)
