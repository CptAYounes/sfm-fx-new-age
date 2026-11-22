"""Foreground wrapper: use discovered desktop routing, propagate real exit."""
from pathlib import Path
import json,os,subprocess,sys


def run():
    root=Path(__file__).resolve().parents[1];out=root/'.runtime/public-fiat-access-v1'
    label=sys.argv[1];assert label in {'source-native-final','installed-native-final'}
    package=root/'src' if label.startswith('source') else Path(json.loads((out/'build-receipt.json').read_bytes())['installed_package_root'])
    env=dict(os.environ,SFM_KRAKEN_PACKAGE=str(package),SFM_KRAKEN_OUT=str(out/label))
    for p in Path('/proc').iterdir():
        try:
            if p.name.isdecimal() and p.stat().st_uid==os.getuid() and (p/'comm').read_text().strip()=='plasmashell':
                for item in (p/'environ').read_bytes().split(b'\0'):
                    k,_,v=item.partition(b'=')
                    if k in (b'DISPLAY',b'XAUTHORITY',b'XDG_RUNTIME_DIR',b'DBUS_SESSION_BUS_ADDRESS'):env[k.decode()]=v.decode()
                break
        except (OSError,UnicodeError):pass
    assert env.get('DISPLAY')
    with (out/(label+'.log')).open('x') as f:
        process=subprocess.run([sys.executable,'-I','-B',str(root/'verification/kraken_public_desktop.py')],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=390)
    print('NATIVE_PROCESS_EXIT',label,process.returncode)
    result=out/label/'acceptance.json'
    if result.is_file():
        data=json.loads(result.read_bytes())
        print(json.dumps({k:v for k,v in data.items() if k not in ('observed_keys','quantity_states','feed_state','bounded_publication_counts')},indent=2))
    return process.returncode


if __name__=='__main__':raise SystemExit(run())
