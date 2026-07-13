# Jira Cloud REST API v3 — raw reference

Read this when `jira.py` doesn't cover the case: discovering field/project/type
IDs, custom fields, JQL tuning, or building a call the wrapper doesn't expose. All
paths are under `$JIRA_BASE_URL/rest/api/3`. Auth is the same Basic header the
wrapper uses.

```bash
# curl auth shorthand used below
AUTH=(--user "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json")
```

## Table of contents
- [Auth](#auth)
- [Search (JQL) — the v3 gotcha](#search-jql--the-v3-gotcha)
- [Get an issue](#get-an-issue)
- [Create an issue](#create-an-issue)
- [Update an issue](#update-an-issue)
- [Comments](#comments)
- [Transitions](#transitions)
- [ADF (Atlassian Document Format)](#adf-atlassian-document-format)
- [Discovering IDs (projects, issue types, fields)](#discovering-ids)

## Auth
Basic auth: base64 of `email:api_token`. Curl's `--user` does the encoding.
Tokens are managed at <https://id.atlassian.com/manage-profile/security/api-tokens>
and can be revoked individually. Never commit a token; keep it in an env var.

## Search (JQL) — the v3 gotcha
The old `GET/POST /rest/api/3/search` was **removed** — it now returns `410 Gone`.
Use `POST /rest/api/3/search/jql`. Two behavior changes bite people:

1. **No fields by default.** You must pass `fields`, or you get back only keys.
2. **Cursor pagination.** There is no `startAt` / `total`. Response carries
   `nextPageToken` when more pages exist; pass it back to get the next page. Loop
   until the response has no `nextPageToken`.

```bash
curl -s "${AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "$JIRA_BASE_URL/rest/api/3/search/jql" \
  -d '{
        "jql": "project = ABC AND statusCategory != Done ORDER BY created DESC",
        "fields": ["summary","status","assignee"],
        "maxResults": 50
      }'
# next page: add  "nextPageToken": "<token from previous response>"
```

## Get an issue
```bash
curl -s "${AUTH[@]}" \
  "$JIRA_BASE_URL/rest/api/3/issue/ABC-123?fields=summary,status,description"
```
Omit `fields` to get every navigable field. Add `expand=renderedFields` to get
HTML-rendered versions of ADF fields.

## Create an issue
`POST /rest/api/3/issue`. Body wraps everything in `fields`. `project` is by
`key` (or `id`), `issuetype` by `name` (or `id`), `description` is ADF.

```bash
curl -s "${AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "$JIRA_BASE_URL/rest/api/3/issue" \
  -d '{
        "fields": {
          "project": { "key": "ABC" },
          "issuetype": { "name": "Task" },
          "summary": "Short one-line title",
          "description": {
            "version": 1, "type": "doc",
            "content": [{ "type": "paragraph",
              "content": [{ "type": "text", "text": "Body goes here." }] }]
          },
          "labels": ["backend"],
          "priority": { "name": "High" }
        }
      }'
# -> { "id": "10042", "key": "ABC-124", "self": "..." }
```
Sub-task: add `"parent": { "key": "ABC-1" }` and use a sub-task issue type.

## Update an issue
`PUT /rest/api/3/issue/ABC-123` — returns **204 No Content** on success. Two
mutually-usable shapes:
- `{"fields": {...}}` — overwrite field values (same shape as create).
- `{"update": {...}}` — verb-based edits, e.g. add one label without resending all:
  `{"update": {"labels": [{"add": "urgent"}]}}`.

```bash
curl -s "${AUTH[@]}" -H "Content-Type: application/json" \
  -X PUT "$JIRA_BASE_URL/rest/api/3/issue/ABC-123" \
  -d '{ "fields": { "summary": "New title" } }'
```

## Comments
`POST /rest/api/3/issue/ABC-123/comment`, body is `{ "body": <ADF> }`.
```bash
curl -s "${AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "$JIRA_BASE_URL/rest/api/3/issue/ABC-123/comment" \
  -d '{ "body": { "version":1,"type":"doc","content":[
        {"type":"paragraph","content":[{"type":"text","text":"Looks good."}]}]}}'
```

## Transitions
Status changes go through transitions, not by writing `status` directly. First
list what's available *from the current status*, then post the transition id.
```bash
curl -s "${AUTH[@]}" "$JIRA_BASE_URL/rest/api/3/issue/ABC-123/transitions"
# -> transitions[].id / .name / .to.name

curl -s "${AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "$JIRA_BASE_URL/rest/api/3/issue/ABC-123/transitions" \
  -d '{ "transition": { "id": "31" } }'   # 204 on success
```
The available transitions depend on the workflow and the issue's current status,
so always fetch them fresh rather than hardcoding an id.

## ADF (Atlassian Document Format)
Rich-text fields (`description`, comment `body`, etc.) are a JSON document, not a
string. Minimal valid doc for one paragraph of plain text:
```json
{ "version": 1, "type": "doc",
  "content": [ { "type": "paragraph",
    "content": [ { "type": "text", "text": "Hello" } ] } ] }
```
Common nodes: `paragraph`, `hardBreak`, `bulletList`/`orderedList` > `listItem` >
`paragraph`, `codeBlock` (`attrs.language`), and marks on text like
`{"type":"text","text":"x","marks":[{"type":"strong"}]}`. `jira.py`'s
`text_to_adf` covers plain multi-paragraph text; hand-build for lists/code.
Full spec: <https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/>

## Discovering IDs
Field/type/project identifiers are instance-specific — look them up, don't guess.
```bash
# Project keys & ids
curl -s "${AUTH[@]}" "$JIRA_BASE_URL/rest/api/3/project/search?query=abc"

# Issue types valid for a project (create metadata)
curl -s "${AUTH[@]}" \
  "$JIRA_BASE_URL/rest/api/3/issue/createmeta/ABC/issuetypes"

# Fields required/allowed for a given project+issuetype (id 10001 here)
curl -s "${AUTH[@]}" \
  "$JIRA_BASE_URL/rest/api/3/issue/createmeta/ABC/issuetypes/10001"

# All fields (find a custom field's id, e.g. Story Points -> customfield_100xx)
curl -s "${AUTH[@]}" "$JIRA_BASE_URL/rest/api/3/field"
```
Custom fields are addressed by id (`customfield_10011`), passed to `jira.py` via
`--field 'customfield_10011=5'`.
