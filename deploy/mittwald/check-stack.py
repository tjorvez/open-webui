#!/usr/bin/env python3
"""Refuse to replace unrelated services or volumes in a mittwald stack."""

import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import uuid


def main():
    token = os.environ.get('MITTWALD_API_TOKEN', '')
    if not token:
        raise SystemExit('Missing configuration: MITTWALD_API_TOKEN')
    try:
        stack_id = str(uuid.UUID(os.environ.get('MITTWALD_STACK_ID', '')))
    except ValueError:
        raise SystemExit('MITTWALD_STACK_ID must be a stack UUID')
    request = urllib.request.Request(
        f'https://api.mittwald.de/v2/stacks/{stack_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            current = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f'Cannot inspect mittwald stack: HTTP {error.code}')
    except (urllib.error.URLError, ValueError):
        raise SystemExit('Cannot inspect mittwald stack')
    desired = json.loads(Path(__file__).with_name('stack.json').read_text())
    services = {service['serviceName'] for service in current['services']}
    volumes = {volume['name'] for volume in current['volumes']}
    if services - desired['services'].keys() or volumes - {v['name'] for v in desired['volumes'].values()}:
        raise SystemExit(
            'Stack contains unrelated services or volumes. Use a dedicated testing project '
            'or include its complete configuration in deploy/mittwald/stack.json.'
        )
    print('Target stack contains no unrelated services or volumes.')


if __name__ == '__main__':
    main()
