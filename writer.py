import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import subprocess
import datetime
import re
# txt2jsonは同じフォルダにある前提
try:
    from txt2json import parse_segawa_script, main as convert_json
except ImportError:
    pass # txt2jsonがない場合のエラーハンドリングが必要なら追加

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
        self.geometry("650x600")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.create_widgets()
        
        # 初期表示更新
        self.on_mode_change()

    def create_widgets(self):
        # --- 1. 記事選択エリア ---
        frame_top = ttk.LabelFrame(self, text="記事の選択・作成", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        # ジャンル選択
        frame_cat = ttk.Frame(frame_top)
        frame_cat.pack(fill="x", pady=5)
        ttk.Label(frame_cat, text="ジャンル:").pack(side="left")
        self.combo_category = ttk.Combobox(frame_cat, values=list(CATEGORIES.keys()), state="readonly")
        self.combo_category.current(0)
        self.combo_category.pack(side="left", padx=5, fill="x", expand=True)
        self.combo_category.bind("<<ComboboxSelected>>", self.on_category_change)

        # モード選択（ラジオボタン）
        frame_mode = ttk.Frame(frame_top)
        frame_mode.pack(fill="x", pady=5)
        self.mode_var = tk.StringVar(value="existing")
        
        ttk.Radiobutton(frame_mode, text="既存記事", variable=self.mode_var, value="existing", command=self.on_mode_change).pack(side="left", padx=5)
        ttk.Radiobutton(frame_mode, text="新規作成", variable=self.mode_var, value="new", command=self.on_mode_change).pack(side="left", padx=5)
        ttk.Radiobutton(frame_mode, text="テスト/下書き", variable=self.mode_var, value="draft", command=self.on_mode_change).pack(side="left", padx=5)

        # ファイル選択・入力エリア
        self.frame_file = ttk.Frame(frame_top)
        self.frame_file.pack(fill="x", pady=5)
        
        # ※この中身はモードによって書き換える
        self.lbl_file = ttk.Label(self.frame_file, text="記事を選択:")
        self.lbl_file.pack(side="left")
        
        self.combo_file = ttk.Combobox(self.frame_file, state="readonly", width=40)
        self.combo_file.pack(side="left", padx=5, fill="x", expand=True)
        
        self.entry_new_id = ttk.Entry(self.frame_file)
        # 初期状態では非表示にしておくなど制御が必要だが、update_uiでやる

        ttk.Button(frame_top, text="エディタで開く", command=self.open_editor).pack(pady=5)


        # --- 2. 画像インポートエリア ---
        frame_img = ttk.LabelFrame(self, text="画像のインポート", padding=10)
        frame_img.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_img, text="画像を選択すると sources フォルダにコピーされます。").pack()
        frame_img_btns = ttk.Frame(frame_img)
        frame_img_btns.pack(pady=5)
        ttk.Button(frame_img_btns, text="画像を選択...", command=self.import_image).pack(side="left", padx=5)
        
        self.entry_img_path = ttk.Entry(frame_img, width=60)
        self.entry_img_path.pack(pady=5, fill="x")

        # --- 3. 公開エリア ---
        frame_action = ttk.LabelFrame(self, text="サイト反映 & 公開", padding=10)
        frame_action.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_convert = ttk.Button(frame_action, text="サイトに反映 (JSON変換 + リンク更新)", command=self.update_site)
        btn_convert.pack(fill="x", pady=2)
        
        btn_push = ttk.Button(frame_action, text="GitHubにアップロード", command=self.git_push)
        btn_push.pack(fill="x", pady=2)
        
        self.log_area = tk.Text(frame_action, height=6)
        self.log_area.pack(fill="both", expand=True, pady=5)

    # --- UI制御ロジック ---

    def on_category_change(self, event=None):
        self.update_file_list()

    def on_mode_change(self):
        mode = self.mode_var.get()
        
        # ウィジェットの表示切り替え
        self.combo_file.pack_forget()
        self.entry_new_id.pack_forget()
        
        if mode == "new":
            self.lbl_file.config(text="ファイル名 (ID):")
            self.entry_new_id.pack(side="left", padx=5, fill="x", expand=True)
            self.combo_category.config(state="readonly") # ジャンル選択有効
        elif mode == "draft":
            self.lbl_file.config(text="ファイル選択:")
            self.combo_file.pack(side="left", padx=5, fill="x", expand=True)
            self.combo_category.config(state="disabled") # ドラフトはジャンル関係なし
            self.update_file_list()
        else: # existing
            self.lbl_file.config(text="記事を選択:")
            self.combo_file.pack(side="left", padx=5, fill="x", expand=True)
            self.combo_category.config(state="readonly")
            self.update_file_list()

    def get_article_title(self, path):
        """ファイルの Title: 行を取得する"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for _ in range(5): # 最初の5行くらいを見る
                    line = f.readline()
                    if line.lower().startswith("title:"):
                        return line[6:].strip()
        except:
            return "読み込みエラー"
        return "タイトルなし"

    def update_file_list(self):
        mode = self.mode_var.get()
        values = []
        
        if mode == "existing":
            cat = self.combo_category.get()
            dir_path = os.path.join(POSTS_DIR, cat)
            if os.path.exists(dir_path):
                files = [f for f in os.listdir(dir_path) if f.endswith('.txt')]
                files.sort()
                for f in files:
                    path = os.path.join(dir_path, f)
                    title = self.get_article_title(path)
                    values.append(f"{f} : {title}")
        
        elif mode == "draft":
            # ルートディレクトリの .txt を列挙 (除外リストあり)
            excludes = ["requirements.txt", "license.txt"]
            files = [f for f in os.listdir(BASE_DIR) if f.endswith('.txt') and f not in excludes]
            for f in files:
                path = os.path.join(BASE_DIR, f)
                title = self.get_article_title(path)
                values.append(f"{f} : {title}")

        self.combo_file['values'] = values
        if values:
            self.combo_file.current(0)
        else:
            self.combo_file.set('')

    # --- 操作ロジック ---

    def get_target_path(self):
        mode = self.mode_var.get()
        cat = self.combo_category.get()
        
        if mode == "new":
            fid = self.entry_new_id.get().strip()
            if not fid:
                messagebox.showwarning("エラー", "ファイル名を入力してください")
                return None
            if not fid.endswith(".txt"):
                fid += ".txt"
            
            dir_path = os.path.join(POSTS_DIR, cat)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            return os.path.join(dir_path, fid)
            
        elif mode == "existing":
            val = self.combo_file.get()
            if not val: return None
            fname = val.split(' : ')[0].strip()
            return os.path.join(POSTS_DIR, cat, fname)
            
        elif mode == "draft":
            val = self.combo_file.get()
            if not val: return None
            fname = val.split(' : ')[0].strip()
            return os.path.join(BASE_DIR, fname)
            
        return None

    def open_editor(self):
        path = self.get_target_path()
        if not path: return
        
        if not os.path.exists(path):
            # 新規作成テンプレート
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"Title: タイトル未定\nDate: {datetime.date.today().strftime('%Y/%m/%d')}\n\n# はじめに\n\n瀬川\n    ここに本文を書いてね。\n")
            self.log(f"作成しました: {path}")
            # リスト更新
            if self.mode_var.get() == "new":
                # 新規作成したら既存モードに切り替える？まあそのままでいいか
                pass
        
        os.startfile(path)
        self.log(f"開きました: {path}")

    def import_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
        if not file_path: return
        
        mode = self.mode_var.get()
        if mode == "draft":
            # ドラフトの場合は sources/temp にするか、あるいは直下？
            # 整理のため sources/draft に入れる
            cat = "draft"
        else:
            cat = self.combo_category.get()
            
        target_dir = os.path.join(SOURCES_DIR, cat)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        filename = os.path.basename(file_path)
        target_path = os.path.join(target_dir, filename)
        
        shutil.copy2(file_path, target_path)
        
        rel_path = f"sources/{cat}/{filename}"
        cmd_str = f"!img: {rel_path} [キャプション]"
        
        self.entry_img_path.delete(0, tk.END)
        self.entry_img_path.insert(0, cmd_str)
        self.clipboard_clear()
        self.clipboard_append(cmd_str)
        self.log(f"画像コピー完了: {rel_path}")
        messagebox.showinfo("成功", "パスをクリップボードにコピーしました！")

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def update_site(self):
        self.log("記事を変換中...")
        subprocess.run(["python", "txt2json.py", "posts"], shell=True)
        # ドラフトもJSONにするならここで指定
        # subprocess.run(["python", "txt2json.py", "draft_sample.txt"], shell=True) 
        
        self.log("seminars.html を更新中...")
        self.update_seminars_html()
        self.log("完了しました。")

    def update_seminars_html(self):
        # seminars.html 更新ロジック (前回のコードと同じ)
        with open(SEMINARS_HTML, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        for cat, cat_name in CATEGORIES.items():
            dir_path = os.path.join(POSTS_DIR, cat)
            if not os.path.exists(dir_path): continue
            
            files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
            files.sort(reverse=True)
            
            new_list_items = []
            for json_file in files:
                fid = os.path.splitext(json_file)[0]
                json_path = os.path.join(dir_path, json_file)
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        import json
                        data = json.load(f)
                        title = data.get('title', '無題')
                        date = data.get('date', '----/--/--')
                except:
                    continue
                
                item_html = f'''                <li class="article-item">
                    <a href="article_view.html?p={cat}/{fid}">
                        <span class="article-date">{date}</span>
                        {title}
                    </a>
                </li>'''
                new_list_items.append(item_html)
            
            marker = f'<!-- AUTO-INSERT: {cat} -->'
            if marker in html_content:
                pattern = re.compile(f'({marker})(.*?)(</ul>)', re.DOTALL)
                def replace_func(match):
                    return match.group(1) + "\n" + "\n".join(new_list_items) + "\n            " + match.group(3)
                html_content = pattern.sub(replace_func, html_content)
        
        with open(SEMINARS_HTML, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def git_push(self):
        self.log("Git同期開始...")
        try:
            subprocess.run(["git", "add", "."], check=True, shell=True)
            try:
                subprocess.run(["git", "commit", "-m", "Update via Segawa Writer"], check=True, shell=True)
            except:
                pass
            
            self.log("Pulling...")
            subprocess.run(["git", "pull", "origin", "main"], check=True, shell=True)
            
            self.log("Pushing...")
            subprocess.run(["git", "push", "origin", "main"], check=True, shell=True)
            
            self.log("完了！")
            messagebox.showinfo("成功", "公開完了！")
        except subprocess.CalledProcessError as e:
            self.log(f"Error: {e}")
            messagebox.showerror("エラー", str(e))

if __name__ == "__main__":
    app = SegawaWriter()
    app.mainloop()