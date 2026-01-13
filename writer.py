import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import subprocess
import datetime
import re
from txt2json import parse_segawa_script, main as convert_json # 既存の変換ロジックを再利用

# 設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, 'posts')
SOURCES_DIR = os.path.join(BASE_DIR, 'sources')
SEMINARS_HTML = os.path.join(BASE_DIR, 'seminars.html')

CATEGORIES = {
    'logic': '命題論理ゼミ',
    'algebra': 'リー代数ゼミ',
    'computation': '計算可能性ゼミ'
}

class SegawaWriter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Segawa Writer - 記事管理システム")
        self.geometry("600x500")
        
        # スタイル設定
        style = ttk.Style()
        style.theme_use('clam')
        
        # UI構築
        self.create_widgets()
        
    def create_widgets(self):
        # 1. 記事選択エリア
        frame_top = ttk.LabelFrame(self, text="記事の選択・作成", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_top, text="ジャンル:").grid(row=0, column=0, sticky="w")
        self.combo_category = ttk.Combobox(frame_top, values=list(CATEGORIES.keys()), state="readonly")
        self.combo_category.current(0)
        self.combo_category.grid(row=0, column=1, padx=5, sticky="ew")
        
        ttk.Label(frame_top, text="ファイルID (例: 01):").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_id = ttk.Entry(frame_top)
        self.entry_id.grid(row=1, column=1, padx=5, sticky="ew")
        
        ttk.Button(frame_top, text="編集 / 新規作成", command=self.open_editor).grid(row=1, column=2, padx=5)
        
        frame_top.columnconfigure(1, weight=1)

        # 2. 画像インポートエリア
        frame_img = ttk.LabelFrame(self, text="画像のインポート", padding=10)
        frame_img.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_img, text="画像を選択すると、sourcesフォルダにコピーされ\n記事用のパス (!img: ...) が表示されます。").pack(pady=5)
        ttk.Button(frame_img, text="画像を選択...", command=self.import_image).pack()
        
        self.entry_img_path = ttk.Entry(frame_img, width=50)
        self.entry_img_path.pack(pady=5, fill="x")

        # 3. 公開エリア
        frame_action = ttk.LabelFrame(self, text="サイト反映 & 公開", padding=10)
        frame_action.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_convert = ttk.Button(frame_action, text="サイトに反映 (JSON変換 + リンク追加)", command=self.update_site)
        btn_convert.pack(fill="x", pady=5)
        
        btn_push = ttk.Button(frame_action, text="GitHubにアップロード (Git Push)", command=self.git_push)
        btn_push.pack(fill="x", pady=5)
        
        self.log_area = tk.Text(frame_action, height=8)
        self.log_area.pack(fill="both", expand=True, pady=5)

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def get_paths(self):
        cat = self.combo_category.get()
        fid = self.entry_id.get().strip()
        if not fid:
            messagebox.showwarning("エラー", "ファイルIDを入力してください")
            return None, None, None
        
        dir_path = os.path.join(POSTS_DIR, cat)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            
        txt_path = os.path.join(dir_path, f"{fid}.txt")
        return cat, fid, txt_path

    def open_editor(self):
        cat, fid, txt_path = self.get_paths()
        if not txt_path: return
        
        if not os.path.exists(txt_path):
            # 新規作成テンプレート
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"Title: タイトル未定\nDate: {datetime.date.today().strftime('%Y/%m/%d')}\n\n# はじめに\n\n瀬川\n    ここに本文を書いてね。\n")
            self.log(f"新規作成: {txt_path}")
        
        # 既定のエディタで開く (Windows)
        os.startfile(txt_path)

    def import_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
        if not file_path: return
        
        cat = self.combo_category.get()
        target_dir = os.path.join(SOURCES_DIR, cat)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        filename = os.path.basename(file_path)
        target_path = os.path.join(target_dir, filename)
        
        shutil.copy2(file_path, target_path)
        
        # 相対パスを生成
        rel_path = f"sources/{cat}/{filename}"
        cmd_str = f"!img: {rel_path} [キャプション]"
        
        self.entry_img_path.delete(0, tk.END)
        self.entry_img_path.insert(0, cmd_str)
        
        # クリップボードにコピー
        self.clipboard_clear()
        self.clipboard_append(cmd_str)
        
        self.log(f"画像をコピーしました: {rel_path}")
        messagebox.showinfo("成功", "パスをクリップボードにコピーしました！\n記事に貼り付けてください。")

    def update_site(self):
        # 1. 全JSON変換
        self.log("記事を変換中...")
        subprocess.run(["python", "txt2json.py", "posts"], shell=True)
        self.log("変換完了")
        
        # 2. seminars.html の更新
        self.update_seminars_html()

    def update_seminars_html(self):
        # 現在のファイル一覧を取得してリンクを生成
        self.log("seminars.html を更新中...")
        
        with open(SEMINARS_HTML, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        for cat, cat_name in CATEGORIES.items():
            dir_path = os.path.join(POSTS_DIR, cat)
            if not os.path.exists(dir_path): continue
            
            # JSONファイルを走査して日付順または名前順にソート
            files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
            files.sort(reverse=True) # 新しい順（簡易的にファイル名で）
            
            new_list_items = []
            for json_file in files:
                fid = os.path.splitext(json_file)[0]
                json_path = os.path.join(dir_path, json_file)
                
                # タイトルと日付を取得
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        import json
                        data = json.load(f)
                        title = data.get('title', '無題')
                        date = data.get('date', '----/--/--')
                except:
                    continue
                
                # リンクHTML生成
                item_html = f'''                <li class="article-item">
                    <a href="article_view.html?p={cat}/{fid}">
                        <span class="article-date">{date}</span>
                        {title}
                    </a>
                </li>'''
                new_list_items.append(item_html)
            
            # 挿入
            marker = f'<!-- AUTO-INSERT: {cat} -->'
            if marker in html_content:
                # マーカーから次の </ul> までを置換... ではなく、
                # マーカーの直後にリストを再生成して挿入する方式にする（既存の手動リンクが消えるリスクがあるが、管理を一元化するため）
                # 今回は「マーカーの直後」に追記するのではなく、「マーカー ～ </ul> の間」を書き換える
                
                pattern = re.compile(f'({marker})(.*?)(</ul>)', re.DOTALL)
                
                def replace_func(match):
                    return match.group(1) + "\n" + "\n".join(new_list_items) + "\n            " + match.group(3)
                
                html_content = pattern.sub(replace_func, html_content)
        
        with open(SEMINARS_HTML, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        self.log("seminars.html を更新しました。")

    def git_push(self):
        self.log("Gitへのアップロードを開始...")
        try:
            # 1. Add & Commit
            subprocess.run(["git", "add", "."], check=True, shell=True)
            
            # コミットは変更がない場合にエラーになることがあるので、try-exceptで囲むか、あるいはエラーを許容する
            try:
                subprocess.run(["git", "commit", "-m", "Auto update via Segawa Writer"], check=True, shell=True)
            except subprocess.CalledProcessError:
                self.log("変更がないためコミットはスキップされました。")

            # 2. Pull (競合解消のため)
            self.log("リモートリポジトリと同期中(pull)...")
            subprocess.run(["git", "pull", "origin", "main"], check=True, shell=True)

            # 3. Push
            self.log("GitHubへ送信中(push)...")
            subprocess.run(["git", "push", "origin", "main"], check=True, shell=True)
            
            self.log("アップロード完了！")
            messagebox.showinfo("成功", "サイトの公開が完了しました！")
            
        except subprocess.CalledProcessError as e:
            self.log(f"エラーが発生しました: {e}")
            messagebox.showerror("エラー", f"Git操作に失敗しました。\n\n詳細:\n{e}")

if __name__ == "__main__":
    app = SegawaWriter()
    app.mainloop()
