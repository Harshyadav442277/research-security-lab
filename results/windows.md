# Measured experiment outcomes

Known-limit and ablation rows pass when the deliberately weak behavior is observed.

| Scenario | Observed HTTP outcomes | Recorded effects | Expected effects | Match |
|---|---|---:|---:|---|
| valid | 200:accepted x1 | 1 | 1 | yes |
| valid_explicit_port | 200:accepted x1 | 1 | 1 | yes |
| tampered_signature | 401:authentication x1 | 0 | 0 | yes |
| non_ascii_signature | 401:authentication x1 | 0 | 0 | yes |
| forged_key_id | 401:authentication x1 | 0 | 0 | yes |
| cross_device | 403:scope x1 | 0 | 0 | yes |
| cross_device_without_scope | 200:accepted x1 | 1 | 1 | yes |
| unknown_tool | 403:tool x1 | 0 | 0 | yes |
| bad_json | 400:schema x1 | 0 | 0 | yes |
| non_object | 400:schema x1 | 0 | 0 | yes |
| duplicate_json_key | 400:schema x1 | 0 | 0 | yes |
| boolean_timestamp | 400:schema x1 | 0 | 0 | yes |
| invalid_utf8 | 400:schema x1 | 0 | 0 | yes |
| oversize | 413:body_size x1 | 0 | 0 | yes |
| wrong_content_type | 415:content_type x1 | 0 | 0 | yes |
| stale | 403:freshness x1 | 0 | 0 | yes |
| future | 403:freshness x1 | 0 | 0 | yes |
| stale_without_freshness | 200:accepted x1 | 1 | 1 | yes |
| url_00 | 403:url x1 | 0 | 0 | yes |
| url_01 | 403:url x1 | 0 | 0 | yes |
| url_02 | 403:url x1 | 0 | 0 | yes |
| url_03 | 403:url x1 | 0 | 0 | yes |
| url_04 | 403:url x1 | 0 | 0 | yes |
| url_05 | 403:url x1 | 0 | 0 | yes |
| url_06 | 403:url x1 | 0 | 0 | yes |
| url_07 | 403:url x1 | 0 | 0 | yes |
| url_08 | 403:url x1 | 0 | 0 | yes |
| url_09 | 403:url x1 | 0 | 0 | yes |
| url_10 | 403:url x1 | 0 | 0 | yes |
| url_without_gate | 200:accepted x1 | 1 | 1 | yes |
| duplicate_length | 400:framing x1 | 0 | 0 | yes |
| chunked_framing | 400:framing x1 | 0 | 0 | yes |
| negative_length | 400:framing x1 | 0 | 0 | yes |
| sequential_replay | 200:accepted x1, 409:replay x1 | 1 | 1 | yes |
| replay_disabled | 200:accepted x2 | 2 | 2 | yes |
| rate_limit | 200:accepted x3, 429:rate x1 | 3 | 3 | yes |
| rate_disabled | 200:accepted x4 | 4 | 4 | yes |
| concurrent_atomic_00 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_00 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_01 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_01 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_02 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_02 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_03 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_03 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_04 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_04 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_05 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_05 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_06 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_06 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_07 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_07 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_08 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_08 | 200:accepted x8 | 8 | 8 | yes |
| concurrent_atomic_09 | 200:accepted x1, 409:replay x7 | 1 | 1 | yes |
| concurrent_disabled_09 | 200:accepted x8 | 8 | 8 | yes |
| future_nonce_retention | 200:accepted x1, 403:freshness x1, 409:replay x1 | 1 | 1 | yes |
| rate_recovery_and_principal_isolation | 200:accepted x5, 429:rate x1 | 5 | 5 | yes |
| known_limitation_restart_replay | 200:accepted x2 | 2 | 2 | yes |
