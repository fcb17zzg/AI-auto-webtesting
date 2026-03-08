from pathlib import Path

import pytest

from aut.dsl import CaseParser


def test_parser_expands_pre_steps_and_variables() -> None:
    parser = CaseParser(Path(__file__).resolve().parents[1] / "cases")
    case = parser.parse(
        "product/create_vpc.yaml",
        {
            "ASCM_URL": "http://example.com",
            "USERNAME": "tester",
            "PASSWORD": "secret",
            "DEFAULT_ORG_ID": "org-1",
            "VPC_NAME_UNIQUE": "vpc-demo",
        },
    )

    assert case.name == "create_vpc_unique"
    assert len(case.steps) == 8
    assert case.steps[0].task == '打开 "http://example.com/login"'
    assert case.steps[-2].task == '在“专有网络名称”输入框输入“vpc-demo”'
    assert case.steps[-1].expected[0]["type"] == "playwright"


def test_parser_detects_missing_variable() -> None:
    parser = CaseParser(Path(__file__).resolve().parents[1] / "cases")
    with pytest.raises(Exception):
        parser.parse("product/create_vpc.yaml", {"ASCM_URL": "http://example.com"})