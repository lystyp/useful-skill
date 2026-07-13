#!/usr/bin/env python3
"""Jira Cloud REST API v3 wrapper — handles auth, ADF, and cursor pagination.

Why this exists: three things about Jira Cloud v3 are easy to get wrong, and this
script hides all of them so callers never have to think about them again:

  1. Auth      — Basic auth with `email:api_token` base64-encoded. Read from env.
  2. ADF       — v3 write endpoints reject plain strings for `description`/comment;
                 they want Atlassian Document Format (a JSON doc). We build it.
  3. Search    — the old GET/POST /rest/api/3/search is GONE (410). The replacement
                 /rest/api/3/search/jql is cursor-paginated (nextPageToken), has no
                 `total`, and returns NO fields unless you ask. We handle all of it.

Credentials come from the environment (never hardcode a token in a file):
  JIRA_BASE_URL   https://your-domain.atlassian.net   (site root, no /rest suffix)
  JIRA_EMAIL      your Atlassian account email
  JIRA_API_TOKEN  a token from https://id.atlassian.com/manage-profile/security/api-tokens

Every write subcommand (create/update/comment/transition) mutates real Jira. The
caller is responsible for confirming intent before running these — see SKILL.md.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_PREFIX = "/rest/api/3"


def _fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _config():
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    missing = [
        name
        for name, val in (
            ("JIRA_BASE_URL", base),
            ("JIRA_EMAIL", email),
            ("JIRA_API_TOKEN", token),
        )
        if not val
    ]
    if missing:
        _fail(
            "missing env var(s): "
            + ", ".join(missing)
            + ". See SKILL.md 'One-time setup'."
        )
    return base, email, token


def _request(method, path, body=None, params=None):
    """Send a request against the v3 API. Returns parsed JSON, or None on 204.

    On any non-2xx we print Jira's own error body (it usually names the exact bad
    field, e.g. 'customfield_10011 is required') and exit — far more useful than a
    bare stack trace.
    """
    base, email, token = _config()
    url = base + API_PREFIX + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:
            detail = json.dumps(json.loads(detail), ensure_ascii=False, indent=2)
        except ValueError:
            pass
        _fail(f"HTTP {e.code} {method} {path}\n{detail}")
    except urllib.error.URLError as e:
        _fail(f"cannot reach {base}: {e.reason}")


def text_to_adf(text):
    """Plain text -> minimal ADF doc. Blank lines split paragraphs; single
    newlines become hard breaks so multi-line notes keep their shape."""
    doc = {"version": 1, "type": "doc", "content": []}
    for block in text.split("\n\n"):
        lines = block.split("\n")
        nodes = []
        for i, line in enumerate(lines):
            if i > 0:
                nodes.append({"type": "hardBreak"})
            if line:
                nodes.append({"type": "text", "text": line})
        doc["content"].append({"type": "paragraph", "content": nodes})
    return doc


def _parse_field(pair):
    """'key=value' -> (key, value). Value is parsed as JSON when possible so you
    can pass '{"name":"High"}' or '["a","b"]'; otherwise it stays a plain string."""
    if "=" not in pair:
        _fail(f"--field expects key=value, got: {pair}")
    key, _, val = pair.partition("=")
    try:
        return key, json.loads(val)
    except ValueError:
        return key, val


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _issue_url(base, key):
    return f"{base}/browse/{key}"


# --- subcommands ----------------------------------------------------------------


def cmd_myself(args):
    me = _request("GET", "/myself")
    print(f"Connected as {me.get('displayName')} <{me.get('emailAddress')}>")
    print(f"accountId: {me.get('accountId')}")


def cmd_search(args):
    fields = args.fields.split(",") if args.fields else ["summary", "status"]
    body = {"jql": args.jql, "maxResults": args.max, "fields": fields}
    issues = []
    while True:
        page = _request("POST", "/search/jql", body=body)
        issues.extend(page.get("issues", []))
        token = page.get("nextPageToken")
        if not args.all or not token or len(page.get("issues", [])) == 0:
            break
        body["nextPageToken"] = token

    if args.raw:
        _out(issues)
        return
    for it in issues:
        f = it.get("fields", {})
        status = (f.get("status") or {}).get("name", "")
        summary = f.get("summary", "")
        print(f"{it['key']:<16} {status:<14} {summary}")
    print(f"\n{len(issues)} issue(s)" + ("" if args.all else " (first page; use --all to follow pages)"))


def cmd_get(args):
    params = {"fields": args.fields} if args.fields else None
    _out(_request("GET", f"/issue/{args.key}", params=params))


def cmd_create(args):
    fields = {
        "project": {"key": args.project},
        "issuetype": {"name": args.type},
        "summary": args.summary,
    }
    if args.desc:
        fields["description"] = text_to_adf(args.desc)
    if args.parent:
        fields["parent"] = {"key": args.parent}
    for pair in args.field or []:
        k, v = _parse_field(pair)
        fields[k] = v

    res = _request("POST", "/issue", body={"fields": fields})
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    print(f"created {res['key']}  {_issue_url(base, res['key'])}")


def cmd_update(args):
    fields = {}
    if args.summary is not None:
        fields["summary"] = args.summary
    if args.desc is not None:
        fields["description"] = text_to_adf(args.desc)
    for pair in args.field or []:
        k, v = _parse_field(pair)
        fields[k] = v
    if not fields:
        _fail("nothing to update: pass --summary, --desc, and/or --field")

    _request("PUT", f"/issue/{args.key}", body={"fields": fields})  # 204, no body
    print(f"updated {args.key}")


def cmd_comment(args):
    res = _request(
        "POST", f"/issue/{args.key}/comment", body={"body": text_to_adf(args.text)}
    )
    print(f"commented on {args.key} (comment id {res.get('id')})")


def cmd_transitions(args):
    data = _request("GET", f"/issue/{args.key}/transitions")
    for t in data.get("transitions", []):
        to = (t.get("to") or {}).get("name", "")
        print(f"{t['id']:<6} {t['name']:<24} -> {to}")


def _resolve_transition(key, to):
    """Accept a transition id or a (case-insensitive) name and return the id."""
    data = _request("GET", f"/issue/{key}/transitions")
    transitions = data.get("transitions", [])
    for t in transitions:
        if t["id"] == to or t["name"].lower() == to.lower():
            return t["id"]
    names = ", ".join(f"{t['name']}({t['id']})" for t in transitions) or "none available"
    _fail(f"no transition matching '{to}' on {key}. Available: {names}")


def cmd_transition(args):
    tid = _resolve_transition(args.key, args.to)
    body = {"transition": {"id": tid}}
    if args.comment:
        body["update"] = {
            "comment": [{"add": {"body": text_to_adf(args.comment)}}]
        }
    _request("POST", f"/issue/{args.key}/transitions", body=body)  # 204
    print(f"transitioned {args.key} via {args.to}")


def build_parser():
    p = argparse.ArgumentParser(prog="jira.py", description="Jira Cloud v3 helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("myself", help="verify credentials / connectivity").set_defaults(
        func=cmd_myself
    )

    s = sub.add_parser("search", help="run a JQL query (cursor-paginated v3)")
    s.add_argument("jql")
    s.add_argument("--fields", help="comma list; default 'summary,status'")
    s.add_argument("--max", type=int, default=50, help="page size (default 50)")
    s.add_argument("--all", action="store_true", help="follow nextPageToken to the end")
    s.add_argument("--raw", action="store_true", help="print full JSON instead of a table")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="fetch one issue as JSON")
    g.add_argument("key")
    g.add_argument("--fields", help="comma list; default = all navigable fields")
    g.set_defaults(func=cmd_get)

    c = sub.add_parser("create", help="create an issue")
    c.add_argument("--project", required=True, help="project key, e.g. ABC")
    c.add_argument("--type", required=True, help="issue type name, e.g. Task")
    c.add_argument("--summary", required=True)
    c.add_argument("--desc", help="plain text; converted to ADF")
    c.add_argument("--parent", help="parent issue key (for sub-tasks)")
    c.add_argument("--field", action="append", help="extra field as key=value (value may be JSON); repeatable")
    c.set_defaults(func=cmd_create)

    u = sub.add_parser("update", help="update fields on an issue")
    u.add_argument("key")
    u.add_argument("--summary")
    u.add_argument("--desc", help="plain text; converted to ADF")
    u.add_argument("--field", action="append", help="extra field as key=value (value may be JSON); repeatable")
    u.set_defaults(func=cmd_update)

    m = sub.add_parser("comment", help="add a comment")
    m.add_argument("key")
    m.add_argument("text")
    m.set_defaults(func=cmd_comment)

    t = sub.add_parser("transitions", help="list available transitions for an issue")
    t.add_argument("key")
    t.set_defaults(func=cmd_transitions)

    tr = sub.add_parser("transition", help="move an issue through a transition")
    tr.add_argument("key")
    tr.add_argument("--to", required=True, help="transition id or name (e.g. 'Done')")
    tr.add_argument("--comment", help="optional comment to add with the transition")
    tr.set_defaults(func=cmd_transition)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
