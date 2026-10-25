# SQLite experiment results

These cases measure local recorded actions, not external delivery.

| Case | Observed outcomes | Actions | Expected actions | Match |
|---|---|---:|---:|---|
| restart_keeps_replay_state | 200:accepted x1, 409:replay x1 | 1 | 1 | yes |
| same_id_changed_body | 200:accepted x1, 409:replay x1, stored:original x1 | 1 | 1 | yes |
| rate_restart_recovery_and_principals | 200:accepted x5, 429:rate x2 | 5 | 5 | yes |
| nonce_retention_and_id_reuse | 200:accepted x2, 409:replay x1 | 2 | 2 | yes |
| two_process_duplicate | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| two_process_rate | 200:accepted x3, 429:rate x5 | 3 | 3 | yes |
| crash_before_commit | 200:accepted x1, actions_before_retry:0 x1, child_exit:73 x1 | 1 | 1 | yes |
| crash_after_commit | 409:replay x1, actions_before_retry:1 x1, child_exit:74 x1 | 1 | 1 | yes |
| locked_database_no_memory_fallback | 200:accepted x1, 503:storage_unavailable x1 | 1 | 1 | yes |
| rejections_do_not_write | 400:schema x1, 401:authentication x1, 403:scope x1 | 0 | 0 | yes |
