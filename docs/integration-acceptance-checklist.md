# Integration acceptance checklist

Use this checklist before publishing or merging a Chronicle integration (adapter, callback, or pipeline connector).

## Contract and behavior

1. Input/output contract is documented and references [Eval contract](eval_contract.md).
2. Integration emits stable claim/evidence linkage behavior across reruns.
3. Error paths are explicit (invalid input, missing evidence, scoring failures).

## Trust and safety posture

1. Docs state Chronicle limitations (defensibility is not truth adjudication).
2. Evidence-claim linking assumptions are explicit (automatic vs curated).
3. Any external fetch behavior is bounded and safe by default.

## Reproducibility

1. There is at least one deterministic example command.
2. Generated artifacts can be verified with `chronicle-verify` where applicable.
3. Version and dependency expectations are pinned or clearly stated.

## Quality gates

1. Python checks pass (`ruff`, `pytest`, `mypy`) for touched code.
2. Doc links pass (`python3 scripts/check_doc_links.py .`).
3. If Neo4j behavior is affected, run `python3 scripts/check_neo4j_contract.py`.
4. For end-to-end confidence, run `python3 scripts/run_reference_workflows.py`.
5. If integration emits scored rows, validate contract shape with `python3 scripts/adapters/validate_adapter_outputs.py --input <file.jsonl>`.
6. Run `python3 scripts/adapters/check_examples.py` before modifying adapter examples or starter behavior.

## Documentation minimum

1. Integration usage is added to docs or script README with exact commands.
2. Required environment variables and optional flags are listed.
3. If field names are non-standard, include a mapping profile example for adapter users.
4. Non-goals and unsupported modes are listed to avoid overpromising.
