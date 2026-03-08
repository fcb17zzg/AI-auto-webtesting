import json
from pathlib import Path

from aut.dsl.models import ResolvedCase, ResolvedStep
from aut.replay import ReplayStore, build_replay_record
from aut.runner import ExecutionContext
from aut.runner.contracts import StepResult


def test_replay_store_save_and_load_roundtrip(tmp_path: Path) -> None:
    case = ResolvedCase(
        name="create-vpc",
        path=Path("cases/product/create_vpc.yaml"),
        description="demo",
        steps=[ResolvedStep(task="open page", source=Path("demo.yaml"))],
        metadata={"feature": "network"},
    )
    context = ExecutionContext(
        case_name="create-vpc",
        run_id="run-20260308010101",
        variables={"USERNAME": "tester"},
    )
    results = [
        StepResult(
            task="open page",
            success=True,
            message="ok",
            artifacts={
                "url": "http://example.com",
                "assertions": [
                    {
                        "type": "playwright",
                        "locator": "get_by_text('ok')",
                        "method": "to_be_visible()",
                        "passed": True,
                        "reason": "",
                    }
                ],
            },
        )
    ]

    record = build_replay_record(case, context, results, driver="dry-run")
    store = ReplayStore(tmp_path)
    saved_path = store.save(record)
    loaded = store.load(saved_path)

    assert saved_path.exists()
    assert loaded.run_id == "run-20260308010101"
    assert loaded.case_name == "create-vpc"
    assert loaded.driver == "dry-run"
    assert len(loaded.steps) == 1
    assert loaded.steps[0].task == "open page"
    assert loaded.steps[0].artifacts["url"] == "http://example.com"
    assert loaded.steps[0].artifacts["assertions"][0]["passed"] is True


def test_replay_file_json_shape(tmp_path: Path) -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[],
    )
    context = ExecutionContext(case_name="demo", run_id="run-demo")
    record = build_replay_record(case, context, [], driver="dry-run")
    saved_path = ReplayStore(tmp_path).save(record)

    payload = json.loads(saved_path.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "1.0"
    assert payload["runId"] == "run-demo"
    assert payload["driver"] == "dry-run"
    assert isinstance(payload["steps"], list)
