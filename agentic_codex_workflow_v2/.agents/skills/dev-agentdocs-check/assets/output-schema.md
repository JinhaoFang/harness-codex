# agentdocs_check 输出 schema（v1）

```json
{
  "status": "OK | WARN | BLOCK | EXCEPTION_ALLOWED",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "workflow": "...",
  "checks": [
    {
      "name": "flowcheck|lint|coverage",
      "status": "OK|WARN|BLOCK|EXCEPTION_ALLOWED",
      "message": "...",
      "details": {}
    }
  ],
  "suggested_next_steps": ["..."]
}
```
