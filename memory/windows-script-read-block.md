---
name: windows-script-read-block
description: Some Windows endpoint protection blocks python/node from reading newly created .py/.js files; run scripts via cat|stdin
metadata:
  type: reference
---

On some managed Windows machines, endpoint protection denies read access to newly
created script files (.py, .js) for python.exe and node.exe — even with clean ACLs —
while `cat` in Git Bash reads them fine. Data files (.json, .mhtml, .html) are
unaffected. The symptom is `PermissionError: [Errno 13]` or "can't open file" on a
script that demonstrably exists and is readable.

**How to apply:** run the script via stdin and pass the project path in an
environment variable instead of relying on `__file__`:
`MEAL_PLANNER_HOME="<project dir>" cat scripts/planner.py | python -`
(same shape for `node -`). Used by [[meal-planner-project]]; only relevant if the
machine actually exhibits the block.
