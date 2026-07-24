## Deliverable

`evals/data/silver_eval_rows.jsonl` and `evals/data/eval_dataset.jsonl` committed to
repo; CI Stage 5 eval gate runs on a combined Yasha+Silver dataset (≥58 rows),
crossing the PAC statistical threshold.

## Acceptance Criteria

- [ ] AC1: `evals/data/silver_eval_rows.jsonl` has ≥20 rows (fallback) / ≥30 rows (target),
      all EvalRow fields present, all routes valid
- [ ] AC2: `evals/data/eval_dataset.jsonl` has same count, all DeepEval fields present
- [ ] AC3: `scripts/merge_eval_datasets.py` merges N JSONL files, deduplicates by
      `row_id`, raises `ValueError` on invalid/missing fields
- [ ] AC4: `tests/test_data/combined_eval.jsonl` produced by merge of Yasha(28) +
      Silver(≥30) = ≥58 rows
- [ ] AC5: CI Stage 5 runs eval gate against `combined_eval.jsonl`
- [ ] AC6: `python3 -m pytest tests/ -k "not deepeval" --ignore=tests/live_bot_test.py -x -q` green

## Test Map

| AC  | Test Name                               | File                                    |
|-----|-----------------------------------------|-----------------------------------------|
| AC1 | `TestSilverOnDisk::test_eval_rows_schema`       | `tests/test_generate_silver_dataset.py` |
| AC2 | `TestSilverOnDisk::test_deepeval_schema`        | `tests/test_generate_silver_dataset.py` |
| AC3 | `TestMergeEvalDatasets::test_deduplicates_by_row_id` | `tests/test_merge_eval_datasets.py` |
| AC3 | `TestMergeEvalDatasets::test_validates_required_fields` | `tests/test_merge_eval_datasets.py` |
| AC3 | `TestMergeEvalDatasets::test_empty_input_raises` | `tests/test_merge_eval_datasets.py` |
| AC3 | `TestMergeEvalDatasets::test_outputs_valid_jsonl` | `tests/test_merge_eval_datasets.py` |
| AC4 | `TestMergeEvalDatasets::test_combined_minimum_row_count` | `tests/test_merge_eval_datasets.py` |
| AC4 | `TestMergeEvalDatasets::test_combined_has_all_routes` | `tests/test_merge_eval_datasets.py` |
| AC5 | CI Stage 5 green                        | `azure-pipelines.yml`                   |
| AC6 | Full unit test suite                    | all tests                               |

## Out of Scope

- Prompt v99 evaluation or promotion (separate session)
- DeepEval full suite changes
- Modifying the existing smoke/Yasha datasets

## Verification

```bash
# Local unit tests
python3 -m pytest tests/ -k "not deepeval" --ignore=tests/live_bot_test.py -x -q

# Produce combined dataset (run after generator outputs exist)
python3 scripts/merge_eval_datasets.py \
  --datasets tests/test_data/foundry_yasha_eval.jsonl evals/data/silver_eval_rows.jsonl \
  --out tests/test_data/combined_eval.jsonl

# Manual eval gate check (requires credentials)
# python3 scripts/foundry_eval_gate.py --dataset tests/test_data/combined_eval.jsonl ...
```

## Generator Run Command (user runs once, needs credentials)

```bash
az keyvault secret show --vault-name shoval --name FOUNDRY-API-KEY -o tsv > /tmp/.key

python3 evals/scripts/generate_silver_dataset.py \
  --project-endpoint https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai \
  --agent-name seekapa \
  --adapt-deployment grok-4-1-fast-reasoning-2-eval \
  --judge-deployment DeepSeek-V3.2 \
  --api-key $(cat /tmp/.key) \
  --n 30 --out evals/data/

rm /tmp/.key
```
