"""第3回: エージェントに持たせるツール。

ここに書いた関数の docstring と型ヒントが、そのままモデルへの「ツールの説明文」になる。
説明文を書き換えると、モデルがツールを使うかどうか・どんな引数で呼ぶかが変わる。
"""

import json
import random
import re
from datetime import datetime
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_RESULTS = 3
# 第3回 宿題（実装）: 学習の記録の保存先。.gitignore で共有しない設定になっている
LOG_DIR = Path(__file__).resolve().parent.parent / "learning_log"


@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")


def _names(entry: dict) -> list[str]:
    return [_normalize(entry["term"]), _normalize(entry["id"])] + [
        _normalize(a) for a in entry["aliases"]
    ]


def search_glossary(query: str) -> str:
    """講座の用語集から用語を検索し、定義と、どの回で扱うかを返す。

    AIエンジニアリングの用語や、この講座（AIE2026）に固有の言葉について
    答える前に使うこと。query には調べたい用語を1つだけ入れる（例: "LoRA"）。
    """
    q = _normalize(query)
    if not q:
        return "検索語が空です。調べたい用語を1つ指定してください。"
    glossary = load_glossary()

    exact = [e for e in glossary if q in _names(e)]
    # 「r」のような短い別名が何にでも当たらないよう、名前側が短いものは除く
    partial = [
        e for e in glossary
        if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
    ]
    in_definition = [
        e for e in glossary
        if e not in exact and e not in partial and q in _normalize(e["definition"])
    ]
    hits = (exact + partial + in_definition)[:MAX_RESULTS]

    if not hits:
        return f"用語集に「{query}」は見つかりませんでした。"
    return json.dumps(
        [
            {
                "term": e["term"],
                "lecture": e["lecture"],
                "definition": e["definition"],
                "related": e["related"],
            }
            for e in hits
        ],
        ensure_ascii=False,
    )


def get_lecture_summary(lecture: int) -> str:
    """指定した回（1始まりの整数）の講義の要点を返す。

    「第3回では何を学ぶ？」のように、回の内容や関係を聞かれたときに使う。
    """
    path = DATA_DIR / "lectures" / f"{lecture:02d}.md"
    if not path.exists():
        available = sorted(p.stem for p in (DATA_DIR / "lectures").glob("*.md"))
        return f"第{lecture}回の要点はまだありません。用意されている回: {', '.join(available)}"
    return path.read_text(encoding="utf-8")


def make_quiz(lecture: int) -> str:
    """指定した回（1始まりの整数）で扱う用語から1つを選び、「この用語の意味は？」という確認問題と答えを返す。

    「第2回の内容から確認問題を出して」のように、復習用の問題を求められたときに使う。
    返した answer は、利用者が答えるまで見せないこと。
    """
    terms = [e for e in load_glossary() if e["lecture"] == lecture]
    if not terms:
        available = sorted({e["lecture"] for e in load_glossary()})
        return f"第{lecture}回の用語は用語集にありません。用語がある回: {', '.join(map(str, available))}"
    entry = random.choice(terms)
    return json.dumps(
        {
            "lecture": lecture,
            "question": f"「{entry['term']}」の意味は？",
            "answer": entry["definition"],
        },
        ensure_ascii=False,
    )


def save_learning_log(title: str, content: str) -> str:
    """学習の記録（学んだこと、疑問、次にやること）を Markdown のファイルとして learning_log/ に保存する。

    利用者が「記録して」「メモに残して」のように保存を頼んだときだけ使う。
    title には記録の短い題名、content には保存する本文を入れる（題名の見出しは自動で付くので content には書かない）。
    保存の前に、利用者の確認が入る。
    """
    title, content = title.strip(), content.strip()
    if not title or not content:
        return "題名と本文の両方が必要です。保存しませんでした。"
    # モデルが content の先頭にも題名の見出しを書くことがあるので、重複を取り除く
    content = re.sub(rf"^#+\s*{re.escape(title)}\s*\n+", "", content).strip() or content
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    # ファイル名に使えない文字は _ にする。題名が同じでも上書きしないよう日時を付ける
    slug = re.sub(r'[\\/:*?"<>|\s]+', "_", title)[:40].strip("_") or "log"
    path = LOG_DIR / f"{now:%Y%m%d-%H%M%S}_{slug}.md"
    n = 1
    while path.exists():
        n += 1
        path = LOG_DIR / f"{now:%Y%m%d-%H%M%S}_{slug}_{n}.md"
    path.write_text(f"# {title}\n\n- 日時: {now:%Y-%m-%d %H:%M}\n\n{content}\n", encoding="utf-8")
    return f"保存しました: learning_log/{path.name}"
