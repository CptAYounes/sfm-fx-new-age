"""Synthetic offline regression tests for token-transport and credential boundaries."""
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from sfm_fx_new_age.connector import oauth


def saved_session(tmp_path, request):
    store = oauth.SecretStore(tmp_path / 'private' / 'tokens.json')
    store.save({'client_secret': 'SYNTHETIC_SECRET', 'refresh_token': 'SYNTHETIC_REFRESH'})
    config = oauth.OAuthConfig('synthetic-client', 'http://127.0.0.1:49151/callback')
    return oauth.OAuthSession(config, store, request=request), store


@pytest.mark.parametrize('url', [
    'http://openapi.ctrader.com/apps/token?grant_type=refresh_token',
    'https://attacker.example/apps/token?grant_type=refresh_token',
    'https://openapi.ctrader.com.attacker.example/apps/token?grant_type=refresh_token',
    'https://user:pass@openapi.ctrader.com/apps/token?grant_type=refresh_token',
    'https://openapi.ctrader.com:444/apps/token?grant_type=refresh_token',
    'https://openapi.ctrader.com/apps/token?grant_type=refresh_token#fragment',
    'https://openapi.ctrader.com/other?grant_type=refresh_token',
    'https://openapi.ctrader.com/apps/token?grant_type=refresh_token&grant_type=authorization_code',
])
def test_token_transport_rejects_nonofficial_or_ambiguous_destination(monkeypatch, url):
    calls = []
    monkeypatch.setattr(oauth, 'urlopen', lambda *a, **k: calls.append(True), raising=False)
    monkeypatch.setattr(oauth, 'build_opener', lambda *a: type('Opener', (), {'open': lambda *a, **k: calls.append(True)})(), raising=False)
    with pytest.raises(ValueError):
        oauth.token_http_request(url, 15)
    assert calls == []


@pytest.mark.parametrize('code', [301, 302, 303, 307, 308])
def test_token_redirect_is_refused_before_a_second_request(code):
    handler = oauth.TokenRedirectHandler()
    original = Request(oauth.TOKEN_URL + '?client_secret=SYNTHETIC_SECRET')
    with pytest.raises(HTTPError) as error:
        handler.redirect_request(original, BytesIO(), code, 'Redirect', {}, 'https://attacker.example/collect')
    assert error.value.code == code
    assert 'SYNTHETIC_SECRET' not in str(error.value)
    assert 'attacker.example' not in str(error.value)


def test_token_transport_installs_redirect_blocker_and_preserves_provider_methods(monkeypatch):
    handlers = []
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append((request.method, request.full_url, timeout))
            return BytesIO(b'{}')
    def build(*values):
        handlers.extend(values)
        return Opener()
    monkeypatch.setattr(oauth, 'build_opener', build, raising=False)
    oauth.token_http_request(oauth.TOKEN_URL + '?grant_type=refresh_token&refresh_token=SYNTHETIC', 15)
    oauth.token_http_request(oauth.TOKEN_URL + '?grant_type=authorization_code&code=SYNTHETIC', 15)
    assert len(handlers) == 2 and all(isinstance(x, oauth.TokenRedirectHandler) for x in handlers)
    assert [r[0] for r in requests] == ['POST', 'GET']


@pytest.mark.parametrize('fault', ['oversized', 'array', 'token_object', 'empty_token', 'boolean_expiry', 'oversized_error', 'duplicate_key'])
def test_token_response_failures_are_bounded_and_do_not_replace_saved_credentials(tmp_path, fault):
    valid = {'accessToken': 'SYNTHETIC_ACCESS', 'refreshToken': 'SYNTHETIC_ROTATED', 'expiresIn': 600}
    if fault == 'oversized':
        payload = b' ' * 65537 + json.dumps(valid).encode()
    elif fault == 'array':
        payload = b'[]'
    elif fault == 'duplicate_key':
        payload = b'{"accessToken":"SYNTHETIC_A","accessToken":"SYNTHETIC_B","refreshToken":"SYNTHETIC_R","expiresIn":600}'
    else:
        if fault == 'token_object': valid['accessToken'] = {'unexpected': 'SYNTHETIC_SECRET'}
        elif fault == 'empty_token': valid['refreshToken'] = ''
        elif fault == 'boolean_expiry': valid['expiresIn'] = True
        payload = json.dumps(valid).encode()
    reads = []
    class ReadBounded(BytesIO):
        def read(self, size=-1):
            reads.append(size)
            assert isinstance(size, int) and 0 < size <= 65537, 'Token response must never be read without a byte budget'
            return super().read(size)
    def request(url, timeout):
        if fault == 'oversized_error':
            raise HTTPError(url, 400, 'SYNTHETIC_PRIVATE', {}, ReadBounded(b' ' * 65537))
        return ReadBounded(payload)
    session, store = saved_session(tmp_path, request)
    before = store.path.read_bytes()
    with pytest.raises(ValueError) as error:
        session.refresh()
    assert reads == [65537]
    assert store.path.read_bytes() == before
    assert session.last_status == 'TOKEN_EXCHANGE_FAILED'
    assert 'SYNTHETIC' not in str(error.value)


def test_secret_store_rejects_hard_linked_credentials(tmp_path):
    store = oauth.SecretStore(tmp_path / 'private' / 'tokens.json')
    store.save({'client_secret': 'SYNTHETIC_SECRET'})
    os.link(store.path, store.path.with_name('alias.json'))
    with pytest.raises(ValueError): store.load()
    with pytest.raises(ValueError): store.save({})


@pytest.mark.parametrize('operation', ['load', 'save'])
def test_secret_store_fifo_is_rejected_without_blocking(tmp_path, operation):
    folder = tmp_path / 'private'
    folder.mkdir(mode=0o700)
    path = folder / 'tokens.json'
    os.mkfifo(path, 0o600)
    code = '''
import sys
from pathlib import Path
from sfm_fx_new_age.connector.oauth import SecretStore
store=SecretStore(Path(sys.argv[1]))
try:
    store.load() if sys.argv[2]=='load' else store.save({})
except (ValueError,OSError):
    raise SystemExit(0)
raise SystemExit('Unsafe FIFO accepted')
'''
    result = subprocess.run([sys.executable, '-c', code, str(path), operation], capture_output=True, text=True, timeout=3)
    assert result.returncode == 0, result.stderr


def test_secret_store_refuses_oversized_save_before_creating_a_file(tmp_path):
    store = oauth.SecretStore(tmp_path / 'private' / 'tokens.json')
    with pytest.raises(ValueError):
        store.save({'client_secret': 'SYNTHETIC_' + 'x' * 65537})
    assert not store.path.exists()


@pytest.mark.parametrize('expiry', [600, '600'])
def test_bounded_token_response_accepts_valid_grant_at_byte_limit(tmp_path, expiry):
    body = {'accessToken': 'SYNTHETIC_ACCESS', 'refreshToken': 'SYNTHETIC_ROTATED', 'expiresIn': expiry}
    payload = json.dumps(body).encode()
    payload += b' ' * (65536 - len(payload))
    reads = []
    class Response(BytesIO):
        def read(self, size=-1):
            reads.append(size)
            return super().read(size)
    session, store = saved_session(tmp_path, lambda url, timeout: Response(payload))
    assert session.refresh() is True
    assert reads == [65537]
    assert store.load()['access_token'] == 'SYNTHETIC_ACCESS'
    assert store.load()['refresh_token'] == 'SYNTHETIC_ROTATED'


def test_redirect_is_blocked_by_real_urllib_opener_without_network(monkeypatch):
    from urllib.request import HTTPSHandler, build_opener
    from urllib.response import addinfourl
    from email.message import Message
    requests = []
    class SyntheticHTTPS(HTTPSHandler):
        def https_open(self, request):
            requests.append(request.full_url)
            headers = Message()
            headers['Location'] = 'https://attacker.example/SYNTHETIC_PRIVATE'
            response = addinfourl(BytesIO(b''), headers, request.full_url, 302)
            response.msg = 'Found'
            return response
    monkeypatch.setattr(oauth, 'build_opener', lambda *handlers: build_opener(SyntheticHTTPS(), *handlers))
    with pytest.raises(HTTPError) as error:
        oauth.token_http_request(oauth.TOKEN_URL + '?grant_type=authorization_code&code=SYNTHETIC_PRIVATE', 15)
    assert len(requests) == 1
    assert error.value.url == oauth.TOKEN_URL
    assert 'SYNTHETIC_PRIVATE' not in str(error.value)


@pytest.mark.parametrize('hostname,accepted', [('synthetic.example', True), ('wrong.example', False)])
def test_sdk_hostname_verifier_accepts_only_matching_synthetic_certificate(hostname, accepted):
    pytest.importorskip('service_identity', reason='Optional cTrader hostname verification')
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from OpenSSL.crypto import X509
    from service_identity import VerificationError
    from service_identity.pyopenssl import verify_hostname
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'synthetic.example')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(1)
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('synthetic.example')]), critical=False)
            .sign(key, hashes.SHA256()))
    class Connection:
        def get_peer_certificate(self): return X509.from_cryptography(cert)
    if accepted:
        verify_hostname(Connection(), hostname)
    else:
        with pytest.raises(VerificationError): verify_hostname(Connection(), hostname)


def test_sdk_client_requires_hostname_verifier_before_constructing_transport(monkeypatch):
    import builtins
    from sfm_fx_new_age.connector.sdk_worker import verified_client
    original = builtins.__import__
    def denied(name, *args, **kwargs):
        if name.startswith('service_identity'):
            raise ImportError('Synthetic missing required hostname verifier')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', denied)
    with pytest.raises(ImportError, match='hostname verifier'):
        verified_client('synthetic.example', 5035, object())


def test_twisted_uses_full_service_identity_verifier_not_fallback():
    pytest.importorskip('service_identity', reason='Optional cTrader hostname verification')
    from twisted.internet import _sslverify
    from service_identity.pyopenssl import verify_hostname
    assert _sslverify.verifyHostname is verify_hostname


def test_optional_fix_context_requires_tls12_certificates_and_hostname_checks():
    import ssl
    from sfm_fx_new_age.connector.fix_capture import price_tls_context
    context = price_tls_context()
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.cert_store_stats()['x509_ca'] > 0
