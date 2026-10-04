#!/usr/bin/env python3
"""Render the mittwald stack without shell interpolation or logging secrets."""

import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

TEMPLATE = Path(__file__).with_name('stack.json')
VARIABLE = re.compile(r'^\$\{([A-Z_]+)\}$')


def render(value):
    if isinstance(value, dict):
        return {key: render(item) for key, item in value.items()}
    if isinstance(value, list):
        return [render(item) for item in value]
    if isinstance(value, str) and (match := VARIABLE.fullmatch(value)):
        name = match[1]
        result = os.environ.get(name, '')
        if not result.strip():
            raise ValueError(f'Missing environment variable: {name}')
        return result
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        stack = render(json.loads(TEMPLATE.read_text()))
        env = stack['services']['open-webui']['envs']
        url = urlsplit(env['WEBUI_URL'])
        if url.scheme != 'https' or not url.hostname or url.path not in ('', '/') or url.query or url.fragment or url.username:
            raise ValueError('WEBUI_URL must be an HTTPS origin without credentials, query or path')
        env['WEBUI_URL'] = env['CORS_ALLOW_ORIGIN'] = env['WEBUI_URL'].rstrip('/')
        if len(env['WEBUI_SECRET_KEY']) < 32:
            raise ValueError('WEBUI_SECRET_KEY must have at least 32 characters')
        if len(env['WEBUI_ADMIN_PASSWORD']) < 12:
            raise ValueError('WEBUI_ADMIN_PASSWORD must have at least 12 characters')
        if '@' not in env['WEBUI_ADMIN_EMAIL']:
            raise ValueError('WEBUI_ADMIN_EMAIL must be an email address')
        if not re.fullmatch(r'ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}', stack['services']['open-webui']['image']):
            raise ValueError('IMAGE_REF must be a GHCR image pinned to a SHA256 digest')
        # JSON is valid YAML. Encoding the rendered values protects quotes,
        # newlines and special characters in secrets from template injection.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(stack, output, indent=2)
            output.write('\n')
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
