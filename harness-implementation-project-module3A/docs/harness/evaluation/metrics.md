# HEB Metrics

Record raw metrics, but do not interpret them alone.

```yaml
schema_version: heb.run_metrics.v0.1
run_id: ""
case_id: ""
agent_id: ""
model: ""
harness_variant: ""
start_time: ""
end_time: ""
wall_clock_seconds: 0
input_tokens: 0
output_tokens: 0
total_tokens: 0
tool_calls: 0
shell_commands: 0
file_reads: 0
file_writes: 0
test_runs: 0
failed_test_runs: 0
retries: 0
manual_interventions: 0
human_review_minutes: 0
changed_files: 0
diff_lines_added: 0
diff_lines_deleted: 0
evidence_count: 0
fresh_evidence_count: 0
waiver_count: 0
hard_gate_failures: []
```

Token count, wall time, or diff size can be misleading. Interpret them with outcome, evidence, recovery, boundary, ambiguity, and human burden.
