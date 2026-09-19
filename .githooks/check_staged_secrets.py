"""Fail the commit if .env or credentials.json are staged with real values.

Run by .githooks/pre-commit. Check by hand with:
    python .githooks/check_staged_secrets.py
"""

import json
import subprocess
import sys

ENV_FILE = ".env"
CREDENTIALS_FILE = "credentials.json"
CREDENTIAL_SECRET_FIELDS = ("client_id", "client_secret", "project_id")
FORBIDDEN_SUFFIXES = ("token.json", ".pem", ".p12")


def stagedFiles():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def stagedContent(path):
    result = subprocess.run(["git", "show", ":" + path], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def filledEnvKeys(content):
    filled = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value.strip().strip("'\"").strip():
            filled.append(key.strip())
    return filled


def filledCredentialFields(content):
    # Parsed as JSON because the file is valid either pretty-printed or on a
    # single line, and a line-based check misreads one of them.
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return []

    section = data.get("installed") or data.get("web") or {}
    if not isinstance(section, dict):
        return []

    return [f for f in CREDENTIAL_SECRET_FIELDS if str(section.get(f) or "").strip()]


def main():
    problems = []
    staged = stagedFiles()

    if ENV_FILE in staged:
        content = stagedContent(ENV_FILE)
        if content is not None:
            filled = filledEnvKeys(content)
            if filled:
                problems.append("%s has real values for: %s" % (ENV_FILE, ", ".join(filled)))

    if CREDENTIALS_FILE in staged:
        content = stagedContent(CREDENTIALS_FILE)
        if content is not None:
            filled = filledCredentialFields(content)
            if filled:
                problems.append("%s has real values for: %s" % (CREDENTIALS_FILE, ", ".join(filled)))

    for path in staged:
        if any(path.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            problems.append("%s must never be committed." % path)

    if not problems:
        return 0

    line = "-" * 64
    print(line)
    print("COMMIT BLOCKED: this would publish real credentials.")
    print(line)
    for problem in problems:
        print("  " + problem)
    print("")
    print("Nothing on disk was changed. To keep your filled-in copies out of git:")
    print("    git reset HEAD %s %s" % (ENV_FILE, CREDENTIALS_FILE))
    print("    git update-index --skip-worktree %s %s" % (ENV_FILE, CREDENTIALS_FILE))
    print("")
    print("Override with --no-verify if you really mean it.")
    print(line)
    return 1


if __name__ == "__main__":
    sys.exit(main())
