# Harness Skills

Canonical, task-routed workflows. Platform mirrors are generated with:

```bash
python3 scripts/sync_platform_skills.py
```

Default lifecycle:

```text
harness-clarify -> harness-spec -> harness-plan -> harness-review(plan)
-> harness-tdd / harness-evidence -> harness-review(close)
-> harness-github / harness-handoff -> harness-compound
```

Skills guide work but do not own lifecycle state or manufacture evidence.
