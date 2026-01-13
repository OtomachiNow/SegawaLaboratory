import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import subprocess
import datetime
import re
import json

# 設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, 'posts')
SOURCES_DIR = os.path.join(BASE_DIR, 'sources')
SEMINARS_HTML = os.path.join(BASE_DIR, 'seminars.html')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

class SiteManager:
    """GUIに依存しないサイト管理ロジック"""
    def __init__(self, log_callback=print):
        self.log = log_callback
        self.categories = self.load_config()

    def load_config(self):
        default_cats = {
            'logic': {'name': '命題論理ゼミ', 'desc': '形式論理の基礎'},
            'algebra': {'name': 'リー代数ゼミ', 'desc': 'リー群・リー代数'},
            'computation': {'name': '計算可能性ゼミ', 'desc': 'チューリングマシン等'},
            'draft': {'name': '下書き・その他', 'desc': '作業用'}
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cats = data.get('categories', {})
                    new_cats = {}
                    for k, v in cats.items():
                        if isinstance(v, str):
                            new_cats[k] = {'name': v, 'desc': ''}
                        else:
                            new_cats[k] = v
                    return new_cats if new_cats else default_cats
            except:
                return default_cats
        return default_cats

    def update_site(self):
        self.log("記事を変換中...")
        subprocess.run(["python", "txt2json.py", "posts"], shell=True, cwd=BASE_DIR)
        
        self.log("seminars.html を再構築中...")
        self.update_seminars_html()
        self.log("完了しました。")

    def update_seminars_html(self):
        with open(SEMINARS_HTML, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        start_marker = '<div class="main">'
        if '<h1>ゼミ一覧</h1>' not in html_content:
            self.log("Error: <h1>ゼミ一覧</h1> tag not found in seminars.html")
            return

        header_part = html_content.split('<h1>ゼミ一覧</h1>')[0] + '<h1>ゼミ一覧</h1>\n'
        
        footer_split = html_content.split('<footer class="foot')
        if len(footer_split) < 2:
            self.log("Error: footer tag not found.")
            return
            
        footer_part = '\n    </div>\n</div>\n\n<footer class="foot' + footer_split[1]
        
        body_content = ""
        
        for key, info in self.categories.items():
            if key == 'draft' or key == 'trash': continue
            
            cat_name = info['name']
            cat_desc = info['desc']
            dir_path = os.path.join(POSTS_DIR, key)
            
            articles_html = ""
            if os.path.exists(dir_path):
                files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
                files.sort(reverse=True)
                
                for json_file in files:
                    fid = os.path.splitext(json_file)[0]
                    json_path = os.path.join(dir_path, json_file)
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if not data.get('published', True):
                                continue
                            title = data.get('title', '無題')
                            date = data.get('date', '----/--/--')
                            
                            articles_html += f'''                <li class="article-item">
                    <a href="article_view.html?p={key}/{fid}">
                        <span class="article-date">{date}</span>
                        {title}
                    </a>
                </li>\n'''
                    except:
                        continue
            
            if not articles_html:
                articles_html = '''                <li class="article-item">
                    <a href="#" style="color: #ccc; cursor: default;">
                        <span class="article-date">Coming Soon</span>
                        準備中
                    </a>
                </li>\n'''

            section_html = f'''
        <!-- {cat_name} -->
        <div class="seminar-section">
            <h2 class="seminar-title">{cat_name}</h2>
            <p class="seminar-desc">{cat_desc}</p>
            <ul class="article-list">
{articles_html}            </ul>
        </div>
'''
            body_content += section_html

        new_html = header_part + body_content + footer_part
        
        with open(SEMINARS_HTML, 'w', encoding='utf-8') as f:
            f.write(new_html)
            
        self.log("seminars.html has been rebuilt.")

    def git_push(self):
        self.log("Gitへのアップロードを開始...")
        try:
            subprocess.run(["git", "add", "."], check=True, shell=True, cwd=BASE_DIR)
            try:
                subprocess.run(["git", "commit", "-m", "Auto update via Segawa Writer"], check=True, shell=True, cwd=BASE_DIR)
            except subprocess.CalledProcessError:
                pass

            self.log("リモートリポジトリと同期中(pull)...")
            subprocess.run(["git", "pull", "origin", "main"], check=True, shell=True, cwd=BASE_DIR)

            self.log("GitHubへ送信中(push)...")
            subprocess.run(["git", "push", "origin", "main"], check=True, shell=True, cwd=BASE_DIR)
            
            self.log("アップロード完了！")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"エラーが発生しました: {e}")
            raise e

class SegawaWriter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Segawa Writer - 管理・公開")
        self.geometry("600x500")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.create_widgets()
        self.manager = SiteManager(log_callback=self.log)
        
    def create_widgets(self):
        frame_action = ttk.LabelFrame(self, text="サイト反映 & 公開", padding=10)
        frame_action.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_convert = ttk.Button(frame_action, text="サイトに反映 (JSON変換 + HTML再構築)", command=self.update_site)
        btn_convert.pack(fill="x", pady=5)
        
        btn_push = ttk.Button(frame_action, text="GitHubにアップロード", command=self.git_push)
        btn_push.pack(fill="x", pady=5)
        
        self.log_area = tk.Text(frame_action, height=15)
        self.log_area.pack(fill="both", expand=True, pady=5)

    def log(self, message):
        try:
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END)
        except:
            print(message)

    def update_site(self):
        self.manager.update_site()

    def git_push(self):
        try:
            if self.manager.git_push():
                messagebox.showinfo("成功", "サイトの公開が完了しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"Git操作に失敗しました。\n\n詳細:\n{e}")

if __name__ == "__main__":
    app = SegawaWriter()
    app.mainloop()
