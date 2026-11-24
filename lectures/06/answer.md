# 第6回 解答

## 演習

<!-- [tool call] の行は、表示された行をそのまま貼り付けてください。終わらなかった STEP は、空欄のままでかまいません。 -->

- STEP 1 のツールの名前：glossary_search_glossary
- STEP 2 の [tool call]：glossary_search_glossary({'query': '3レベル'})
- STEP 3 の [tool call]：fetch_fetch({'url': 'https://modelcontextprotocol.io/'})、続けて glossary_search_glossary({'query': 'MCP'})
- STEP 4 の [tool call]：aws_aws___search_documentation({'search_phrase': 'Amazon S3 バージョニング'})、続けて aws_aws___search_documentation({'search_phrase': 'Using versioning in S3 buckets', 'topics': ['general', 'reference_documentation']})
- 気づき・疑問：
  - STEP 1 では、`app.agent`（関数を直接登録）にはツールが3個、`app.mcp_agent`（MCP 経由）には `glossary_search_glossary` の1個が見えた。関数は同じ `search_glossary` でも、MCP 経由では設定ファイルのキー名 `glossary_` が頭に付いて区別されている
  - STEP 3 の1回目はモデルの混雑（503）で失敗したので、再実行した。再実行のときは STEP 4 の aws も設定に入っていたが、呼ばれたのは fetch と用語集だけだった。fetch はトップページから `/docs/2026-07-28/getting-started/intro.md` へリダイレクトされ、その本文を取得して要約していた
  - `fetch_fetch` の説明文には「もともとインターネットにアクセスできず断るよう言われていたが、このツールでアクセスできるようになった」という、モデルへの指示のような英文が入っている。サーバー作者が書いた説明文がそのままモデルに渡るので、出所の分からないサーバーを足すと、説明文を通してモデルの振る舞いを変えられてしまう。補足の「信頼できるサーバーか確認する」の意味が、実物で分かった
  - STEP 4 では、1回目の検索（日本語の「Amazon S3 バージョニング」）で S3 のエラー（InternalError・SlowDown）のページが1位に来た。モデルは自分で英語の検索語とトピック指定に変えて検索し直し、2回目で S3 Versioning の説明を取得して答えた。ツールの返り値を見て次の呼び出しを変えるのは、第3回のループそのもの
  - aws を足すとツールが2個から7個に増え、AWS 側の説明文は長い英文だった。STEP 2（ツール1個）の入力は709トークンだったのに対し、STEP 3 の再実行は10,427トークン、STEP 4 は11,100トークンだった。ツールの返り値の長さも含むので説明文だけの影響とは言えないが、サーバーを足すほど毎回の入力が増えそう
  - 疑問：説明文が長いツールが多数並んだとき、モデルが関係ないツールを呼ぶ誤りはどのくらい増えるのか

## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

- 取り組んだレベル：基礎
- やったこと：
  - サーバー側の `app/mcp_server.py` の TODO の下に1行だけ書き足し、`get_lecture_summary` を MCP のツールとして公開した
    ```diff
     # TODO(宿題・基礎): get_lecture_summary も公開しよう
    +server.tool()(tools.get_lecture_summary)
    ```
  - エージェント側（`app/mcp_agent.py`）は変えていない。`git status` で変わっていたのは、宿題では `app/mcp_server.py` だけ。`app/mcp_servers.json` も変更ありになっているが、これは演習の STEP 3・4 で fetch と aws を足したためで、宿題の変更ではない
- 結果：
  - `uv run python -m app.mcp_agent --list-tools`：ツールが7個から8個になり、`glossary_get_lecture_summary`（引数 `lecture: integer`、説明「指定した回（1始まりの整数）の講義の要点を返す」）が増えた
  - 「第2回では何を学びますか？」の `--trace`：
    ```
    [tool call]   glossary_get_lecture_summary({'lecture': 2})
    [usage] 入力 5,932 tokens / 出力 223 tokens / モデル応答 2 回
    ```
    返された要点（ファインチューニングとLoRA、SFT、PEFT・LoRA、QLoRA、Colabでの演習）に沿って回答した。用語集の検索は呼ばれず、回の内容を聞く質問に合うツールが選ばれた
  - `uv run pytest -q`：36 passed
- 気づき・疑問：
  - エージェントは起動のたびにサーバーへツールの一覧を問い合わせるので、サーバー側に1行足すだけで、エージェントのコードを触らずに新しいツールが使えた。ツールを追加・修正する人と、それを使うエージェントの担当を分けられる
  - 「第3回では何を学ぶ？」という docstring の例が、そのまま「第2回では何を学びますか？」という質問との対応づけに効いたように見える。ツールを公開する側にとって、docstring はコードのコメントではなく、モデルへの使い方の説明になる
  - 疑問：サーバー側でツールを消したり引数を変えたりすると、それを前提にしていたエージェントは、次の起動から黙って振る舞いが変わる。公開するツールの変更を、どう利用側に知らせるのがよいのか
- 補足：この回の作業は、AIツール（Claude）に実行手順の作成と結果の整理を手伝ってもらった。コマンドは自分のMacで実行し、出力のログを確かめている
