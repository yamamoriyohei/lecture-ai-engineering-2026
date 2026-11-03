"""第3回 宿題（発展 a）: 演習の学習支援エージェントを Google の ADK で組み立て直したもの。

指示（INSTRUCTIONS）とツール（app/tools.py の関数）は演習とまったく同じものを使い、
「エージェントを組み立てる部分」だけを ADK で書いている。app/ のファイルは変えていない。

使い方（リポジトリの直下で）:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
    PYTHONPATH=. uv run --with google-adk adk web adk_agent   # ブラウザの開発用画面で、ツール呼び出しも見られる

ADK が読むのは、このファイルの root_agent だけ。
"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

root_agent = Agent(
    model=MODEL,  # 演習と同じモデル（既定 gemini-3.5-flash-lite。環境変数 AIE_MODEL で切り替え）
    name="glossary_agent",
    description="AIE2026 の用語集と各回の要点を使って答える学習支援エージェント",
    instruction=INSTRUCTIONS,
    # Pydantic AI の agent.tool_plain(...) と同じく、関数をそのまま渡すと docstring と型ヒントがツールの説明になる。
    # save_learning_log（承認付き）は発展の範囲外なので渡していない
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)
