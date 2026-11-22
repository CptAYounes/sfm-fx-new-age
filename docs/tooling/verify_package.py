"""Portable public-edition verification; original host verifier is archived separately."""
from pathlib import Path
import runpy
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/verify_publication.py'), run_name='__main__')
