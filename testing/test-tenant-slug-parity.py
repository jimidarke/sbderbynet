#!/usr/bin/env python3
"""
Cross-check the tenant-slug regex on both sides of the cloud stack.

PHP (`website/inc/cloud-tenant.inc::TENANT_SLUG_RE`) gates which slugs the
tenant-picker accepts, which directories get created, and which sandbox a
session is allowed to bind. Python (`extras/soapbox/infra/server/derbyRace.py
::TENANT_SLUG_RE`) gates which slugs the multi-tenant race-server router will
accept off MQTT before creating a `RaceContext` and writing to a per-tenant
SQLite.

If these drift, you get a silent class of bug: PHP creates a sandbox under a
slug the race-server then refuses (no DB writes from any virtual hardware
publish), or vice-versa. Neither side logs at error level — it just looks
like "the buttons don't work."

This script extracts the actual regex literal from each source file and
diffs their behaviour against a fixture set. Run on every PR that touches
either file.

Exit 0 = matching behaviour. Exit 1 = drift (lists the disagreements).
"""

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PHP_SRC = os.path.join(ROOT, 'website', 'inc', 'cloud-tenant.inc')
PY_SRC  = os.path.join(ROOT, 'extras', 'soapbox', 'infra', 'server', 'derbyRace.py')

# Fixtures span the boundary cases that have actually broken slug regexes
# in past projects: leading/trailing punctuation, length boundaries, mixed
# case, embedded special chars, empty input.
FIXTURES = [
    # (slug, expected_valid)
    ('alpha',                       True),
    ('a',                           True),
    ('a1',                          True),
    ('1',                           True),
    ('1abc',                        True),
    ('a-b',                         True),
    ('alpha-beta-gamma',            True),
    ('a' * 32,                      True),   # max length
    ('a' * 33,                      False),  # over max
    ('',                            False),  # empty
    ('-leading-hyphen',             False),
    ('UPPER',                       False),  # case
    ('mixedCase',                   False),
    ('has space',                   False),
    ('with.dot',                    False),
    ('with/slash',                  False),
    ('with_underscore',             False),
    ('emoji-\U0001f600',            False),
    ('null\x00byte',                False),
    ('a' * 32 + '-',                False),  # hyphen pushes over max
    # MQTT wildcard injection: if any of these ever round-tripped through a
    # slug, the tenant prefix would match arbitrary topics on the broker.
    # Catastrophic if it ever leaked — regex MUST block them.
    ('+',                           False),
    ('foo+bar',                     False),
    ('#',                           False),
    ('foo#bar',                     False),
    # Whitespace / control characters: ACL-line confusion plus MQTT topic
    # rules (\n, \r, \t are illegal in topics under MQTT 3.1.1 anyway).
    ('foo\nbar',                    False),
    ('foo\rbar',                    False),
    ('foo\tbar',                    False),
    (' leading-space',              False),
    ('trailing-space ',             False),
    # Hyphen-only: regex requires alphanumeric first char.
    ('-',                           False),
    ('---',                         False),
]


def extract_php_regex(path):
    """Pull the literal regex out of `define('TENANT_SLUG_RE', '...')`."""
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    m = re.search(r"define\(\s*'TENANT_SLUG_RE'\s*,\s*'([^']+)'", src)
    if not m:
        sys.exit(f"FAIL: could not find TENANT_SLUG_RE define in {path}")
    return m.group(1)


def extract_py_regex(path):
    """Pull the literal regex out of `TENANT_SLUG_RE = re.compile(r'...')`."""
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    m = re.search(r"TENANT_SLUG_RE\s*=\s*re\.compile\(\s*r'([^']+)'", src)
    if not m:
        sys.exit(f"FAIL: could not find TENANT_SLUG_RE compile in {path}")
    return m.group(1)


def php_validate(php_pattern, slug):
    """Shell out to `php -r` so we exercise PHP's actual PCRE engine, not a
    Python re-implementation. Returns True iff PHP's preg_match returns 1.
    Slug is fed through stdin so embedded nulls and other shell-hostile
    bytes round-trip intact (env vars can't carry NUL)."""
    code = (
        "$s = stream_get_contents(STDIN); "
        f"echo (preg_match({json_quote(php_pattern)}, $s) === 1) ? '1' : '0';"
    )
    try:
        proc = subprocess.run(
            ['php', '-r', code],
            input=slug.encode('utf-8'),
            capture_output=True,
            timeout=5,
            check=True,
        )
    except FileNotFoundError:
        sys.exit("FAIL: `php` not on PATH; install php-cli to run this test.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"FAIL: php -r exited {e.returncode}: stderr={e.stderr!r}")
    return proc.stdout.decode('utf-8').strip() == '1'


def json_quote(s):
    """PHP-safe single-quoted string literal. The cloud-tenant.inc regex is
    a fully bracketed PHP regex like `/^[a-z0-9][a-z0-9-]{0,31}$/` so it
    already includes the delimiters; just wrap in single quotes and escape."""
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def py_validate(py_pattern, slug):
    return bool(re.match(py_pattern, slug))


def main():
    php_pattern = extract_php_regex(PHP_SRC)
    py_pattern  = extract_py_regex(PY_SRC)
    print(f"PHP pattern:    {php_pattern}")
    print(f"Python pattern: {py_pattern}")
    print()

    failures = []
    for slug, expected in FIXTURES:
        php_ok = php_validate(php_pattern, slug)
        py_ok  = py_validate(py_pattern, slug)
        agree = (php_ok == py_ok)
        match_expected = (php_ok == expected)
        status = 'OK' if (agree and match_expected) else 'FAIL'
        marker = ' ' if status == 'OK' else '!'
        print(f"{marker} {status:4} slug={slug!r:<40}  php={int(php_ok)} py={int(py_ok)} expected={int(expected)}")
        if not agree:
            failures.append((slug, php_ok, py_ok, 'drift between PHP and Python'))
        elif not match_expected:
            failures.append((slug, php_ok, py_ok, f'both engines disagree with fixture (expected={expected})'))

    print()
    if failures:
        print(f"FAILED: {len(failures)} fixture(s) disagreed:")
        for slug, php_ok, py_ok, why in failures:
            print(f"  slug={slug!r}  php={int(php_ok)}  py={int(py_ok)}  — {why}")
        sys.exit(1)
    print(f"OK: {len(FIXTURES)} fixtures agree across PHP and Python.")


if __name__ == '__main__':
    main()
