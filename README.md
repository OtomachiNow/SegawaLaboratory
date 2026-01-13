# 瀬川研究室 (Segawa Laboratory) Webプロジェクト

「瀬川研究室」の公式ブログ（静的サイト）のソースコードです。
GitHub Pages でのホスティングを想定しています。

## 1. プロジェクト構成

```text
SegawaLab/
├── index.html          # トップページ
├── article_view.html   # 記事ビューワー（JSONを読み込んで表示）
├── seminars.html       # ゼミ一覧ページ
├── txt2json.py         # 記事変換ツール（.txt -> .json）
├── posts/              # 記事データ置き場
│   └── logic/          # カテゴリごとのフォルダ
│       ├── 01.txt      # 原稿テキスト（Git管理推奨）
│       └── 01.json     # 変換後のデータ（Web表示用）
├── subs/               # 旧コンテンツ（数学、ゲームなど）
│   ├── math.html
│   ├── game.html
│   └── ...
└── sources/            # 画像などの静的アセット
```

## 2. 記事の追加方法

### 手順
1.  **原稿の作成**: `.txt` ファイルを作成し、後述する記法で記事を書く。
2.  **JSONへの変換**: `txt2json.py` を実行して `.json` ファイルを生成する。
    ```powershell
    # 例: draft.txt を posts/logic/01.json に変換
    python txt2json.py draft.txt posts/logic/01.json
    ```
3.  **リンクの追加**: `seminars.html` を編集し、新しい記事へのリンクを追加する。
    ```html
    <li class="article-item">
        <a href="article_view.html?p=logic/01">記事タイトル</a>
    </li>
    ```
4.  **公開**: 生成された `.json` と編集した `.html` を GitHub にプッシュする。

---

## 3. 記事記法 (Segawa Script)

テキストファイルで以下の記法を使うことで、会話形式の記事を簡単に作成できます。

### ヘッダー
ファイルの先頭にメタデータを記述します。
```text
Title: 命題論理の導入
Date: 2026/01/12
```

### 見出し
`#` で始めるとセクション見出しになります。
```text
# 第1章 はじめに
```

### 会話
話者名の行の直後から、インデント（タブまたはスペース）して内容を書きます。空行でブロック終了です。
```text
瀬川
    ここは会話パートよ。
    改行もそのまま反映されるわ。

栃村
    わかりました！
```
※ `article_view.html` で話者名（瀬川、栃村、柿山など）に応じてアイコンや色が自動で切り替わります。

### 画像 (!img)
```text
!img: sources/logic/fig1.png [図のキャプション]
```
※ 画像ファイルは `sources/` フォルダ以下などに配置し、相対パスで指定します。

### 数式 (!math / $ / $$)
インライン数式は `$ ... $`、ディスプレイ数式は `$$ ... $$` で記述します（TeX形式）。
バックスラッシュ `\` はそのままでOKです（エスケープ不要）。

会話の中に混ぜることも、独立して表示することもできます。
**独立して表示する場合（中央寄せ）:**
```text
!math:
    $$
    \int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
    $$
```

### 証明・折りたたみ (!fold)
詳細な証明などを折りたたんで表示します。
```text
!fold: 定理の証明を見る
    ここからは証明パートです。
    数式も使えます。
    $$ E = mc^2 $$
```

### コードブロック (!code)
シンタックスハイライト付きのコードを表示します。
```text
!code: python
    def hello():
        print("Hello, World!")
```

---

## 4. 画像ファイルの管理

*   画像ファイルは `sources/` ディレクトリ内に、カテゴリごとにサブフォルダを作って管理することを推奨します（例: `sources/logic/`, `sources/game/`）。
*   記事内からは相対パス（`sources/...`）で参照してください。

## 5. 開発者向けメモ

*   **スタイル修正**: `article_view.html` 内の `<style>` タグを編集してください。
*   **キャラクター追加**: 
    1.  `article_view.html` の CSS に `.char-name` クラスを追加。
    2.  JavaScript (`loadArticle`関数) の条件分岐に新しい名前を追加。

```