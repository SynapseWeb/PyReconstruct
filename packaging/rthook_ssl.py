# Point the frozen app's TLS stack at a bundled CA bundle.
#
# A PyInstaller bundle does not carry the OS trust store the way a normal Python
# installation can reach it, so ssl.create_default_context() finds no CA certs
# and certificate verification fails -- e.g. cloud-volume fetching over HTTPS or
# git operations over TLS raise [SSL: CERTIFICATE_VERIFY_FAILED]. certifi ships a
# cacert.pem (bundled via the spec); exporting SSL_CERT_FILE makes the stdlib
# default SSL context (and thus urllib) trust it. setdefault() so an explicit
# environment override still wins.
import os

try:
    import certifi
    _ca = certifi.where()
    if _ca and os.path.exists(_ca):
        os.environ.setdefault("SSL_CERT_FILE", _ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca)
except Exception:
    pass
