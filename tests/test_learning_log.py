"""第3回 演習・宿題（実装）のテスト（LLMもAPIキーも使わない）。

- make_quiz: 指定した回の用語から問題を作る
- save_learning_log: 承認されたときだけ learning_log/ に保存する（requires_approval=True）
"""

import json

import pytest
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent, ask_approvals, run_with_approval


@pytest.fixture(autouse=True)
def log_dir(tmp_path, monkeypatch):
    """本物の learning_log/ を汚さないよう、保存先を一時フォルダに差し替える。"""
    path = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", path)
    return path


def scripted_input(lines):
    it = iter(lines)
    return lambda _prompt: next(it)


def _returns(result, name):
    return [
        p for m in result.all_messages() for p in m.parts
        if isinstance(p, ToolReturnPart) and p.tool_name == name
    ]


# ---- make_quiz（演習）


def test_make_quiz_uses_a_term_of_that_lecture():
    quiz = json.loads(tools.make_quiz(2))
    terms = {e["term"]: e for e in tools.load_glossary()}
    term = quiz["question"].removeprefix("「").removesuffix("」の意味は？")
    assert terms[term]["lecture"] == 2
    assert quiz["answer"] == terms[term]["definition"]


def test_make_quiz_reports_unknown_lecture():
    assert "用語集にありません" in tools.make_quiz(99)


# ---- save_learning_log（宿題・実装）


def test_save_learning_log_writes_markdown(log_dir):
    message = tools.save_learning_log("LoRA の復習", "低ランク行列だけを学習する。")
    files = list(log_dir.glob("*.md"))
    assert len(files) == 1 and files[0].name in message
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("# LoRA の復習") and "低ランク行列だけを学習する。" in text


def test_save_learning_log_removes_duplicated_heading(log_dir):
    tools.save_learning_log("LoRA の記録", "# LoRA の記録\n\n## 学んだこと\n- 低ランク")
    text = next(log_dir.glob("*.md")).read_text(encoding="utf-8")
    assert text.count("# LoRA の記録") == 1 and "## 学んだこと" in text


def test_save_learning_log_does_not_overwrite_same_title(log_dir):
    tools.save_learning_log("同じ題名", "1 つ目")
    tools.save_learning_log("同じ題名", "2 つ目")
    assert len(list(log_dir.glob("*.md"))) == 2


def test_save_learning_log_rejects_empty_input(log_dir):
    assert "保存しませんでした" in tools.save_learning_log(" ", "本文")
    assert not log_dir.exists()


def test_agent_stops_for_approval_before_saving(log_dir):
    with agent.override(model=TestModel(call_tools=["save_learning_log"])):
        result = agent.run_sync("今日の学びを記録して")

    # 実行は承認待ちで止まり、まだ何も保存されていない
    assert isinstance(result.output, DeferredToolRequests)
    assert [c.tool_name for c in result.output.approvals] == ["save_learning_log"]
    assert not log_dir.exists()


def test_approved_call_saves_the_log(log_dir):
    model = TestModel(call_tools=["save_learning_log"])
    result = run_with_approval(agent, "今日の学びを記録して", model, input_fn=scripted_input(["y"]))

    assert isinstance(result.output, str)
    assert len(list(log_dir.glob("*.md"))) == 1
    # 承認前（ツール呼び出しまで）と承認後（回答）の両方の LLM 呼び出しが数えられている
    assert result.usage.requests == 2
    assert "保存しました" in str(_returns(result, "save_learning_log")[0].content)


@pytest.mark.parametrize("answer", ["n", ""])  # 空 Enter も「保存しない」
def test_denied_call_saves_nothing(log_dir, answer):
    model = TestModel(call_tools=["save_learning_log"])
    result = run_with_approval(agent, "今日の学びを記録して", model, input_fn=scripted_input([answer]))

    assert isinstance(result.output, str)
    assert not log_dir.exists()
    # 拒否したことがツールの結果としてモデルに伝わっている
    assert "許可しませんでした" in str(_returns(result, "save_learning_log")[0].content)


def test_ask_approvals_shows_arguments(capsys):
    call = ToolCallPart("save_learning_log", {"title": "題名", "content": "本文"}, tool_call_id="c1")
    results = ask_approvals(DeferredToolRequests(approvals=[call]), input_fn=scripted_input(["はい"]))
    assert results.approvals == {"c1": True}
    out = capsys.readouterr().out
    assert "title: 題名" in out and "content: 本文" in out
