import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_config_uses_compatible_build_configuration():
    config = json.loads((PROJECT_ROOT / 'vercel.json').read_text())

    assert config['$schema'] == 'https://openapi.vercel.sh/vercel.json'
    assert 'builds' in config
    assert 'functions' not in config
    python_build = next(build for build in config['builds'] if build['src'] == 'api/index.py')
    assert python_build['use'] == '@vercel/python'
    includes = python_build['config']['includeFiles']
    assert 'frontend/dist/**' in includes
    assert 'images/**' in includes
    assert 'pictures/**' in includes
    assert 'templates/**' in includes


def test_vercel_ignore_excludes_secrets_and_ephemeral_files():
    ignored = (PROJECT_ROOT / '.vercelignore').read_text().splitlines()

    assert '.env' in ignored
    assert '.env.*' in ignored
    assert 'uploads' in ignored
    assert 'tests' in ignored
    assert '!.env.example' in ignored
