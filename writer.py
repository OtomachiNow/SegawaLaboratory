import datetime
import json
import os
import subprocess
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from txt2json import parse_segawa_script


BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"
CONFIG_FILE = BASE_DIR / "config.json"
TOC_FILE = POSTS_DIR / "toc.json"
SEMINARS_HTML = BASE_DIR / "seminars.html"
STORY_HTML = BASE_DIR / "story.html"
ABOUT_HTML = BASE_DIR / "about.html"


DEFAULT_TEMPLATE = """Title: 無題
Date: {date}
Type: math
Status: draft

# 導入

栃村 右
    ここに栃村の発言を書く。

瀬川 左
    ここに瀬川の説明を書く。
"""


class SiteManager:
    def __init__(self, log_callback=print):
        self.log = log_callback
        self.config = self.load_config()

    def load_config(self):
        if not CONFIG_FILE.exists():
            return {"categories": {}}
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def categories(self):
        return self.config.get("categories", {})

    def article_files(self):
        if not POSTS_DIR.exists():
            return []
        return sorted(POSTS_DIR.glob("*/*.txt"))

    def parse_article_file(self, path):
        try:
            data = parse_segawa_script(path)
        except Exception:
            data = {"title": path.stem, "date": "", "type": "math", "order": 0, "published": False}
        category = path.parent.name
        return {
            "path": path,
            "category": category,
            "id": f"{category}/{path.stem}",
            "title": data.get("title", path.stem),
            "date": data.get("date", ""),
            "type": data.get("type", "math"),
            "order": data.get("order", 0) or 0,
            "published": data.get("published", True),
        }

    def build_toc(self):
        toc = {}
        for txt_path in self.article_files():
            item = self.parse_article_file(txt_path)
            if item["category"] in {"draft", "trash"} or not item["published"]:
                continue
            toc.setdefault(item["category"], []).append({
                "id": item["id"],
                "title": item["title"],
                "date": item["date"],
                "order": item["order"],
                "type": item["type"],
            })

        for key, articles in toc.items():
            articles.sort(key=lambda x: (x.get("order") or 0, x.get("date", ""), x.get("id", "")))

        POSTS_DIR.mkdir(exist_ok=True)
        with TOC_FILE.open("w", encoding="utf-8") as f:
            json.dump(toc, f, ensure_ascii=False, indent=2)
        self.log("posts/toc.json を更新しました。")
        return toc

    def convert_all(self):
        count = 0
        for txt_path in self.article_files():
            try:
                data = parse_segawa_script(txt_path)
                json_path = txt_path.with_suffix(".json")
                with json_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                count += 1
            except Exception as exc:
                self.log(f"変換失敗: {txt_path.relative_to(BASE_DIR)}: {exc}")
        self.log(f"{count} 件の記事を JSON に変換しました。")

    def update_site(self):
        self.config = self.load_config()
        self.convert_all()
        toc = self.build_toc()
        self.update_seminars_html(toc)
        self.update_story_html(toc)
        self.log("サイト反映が完了しました。")

    def update_seminars_html(self, toc):
        body = []
        for key, info in self.categories.items():
            if key in {"draft", "trash", "story"}:
                continue
            articles = toc.get(key, [])
            if articles:
                article_html = "\n".join(
                    f'                <li class="article-item"><a href="article_view.html?p={a["id"]}">'
                    f'<span class="article-date">{a["date"]}</span>{a["title"]}</a></li>'
                    for a in sorted(articles, key=lambda x: x.get("date", ""), reverse=True)
                )
            else:
                article_html = '                <li class="article-item" style="color:#ccc;">まだ記事がありません</li>'

            body.append(f"""
        <div class="post">
            <h2 class="seminar-title">{info.get("name", key)}</h2>
            <p class="seminar-desc">{info.get("desc", "")}</p>
            <ul class="article-list">
{article_html}
            </ul>
        </div>
""")

        self.replace_generated_block(SEMINARS_HTML, "\n".join(body))
        self.log("seminars.html を更新しました。")

    def update_story_html(self, toc):
        ordered = []
        for articles in toc.values():
            ordered.extend([a for a in articles if a.get("order") and a.get("order") > 0])
        ordered.sort(key=lambda x: x.get("order", 0))

        items = []
        for article in ordered:
            badge_class = "badge-novel" if article.get("type") == "novel" else "badge-math"
            badge_text = "小説" if article.get("type") == "novel" else "数学"
            items.append(f"""
                <li class="story-item">
                    <span class="story-order">{article.get("order"):g}.</span>
                    <div class="story-info">
                        <a href="article_view.html?p={article["id"]}" class="story-title">{article["title"]} <span class="{badge_class}">{badge_text}</span></a>
                        <div class="story-meta">{article["date"]}</div>
                    </div>
                </li>""")

        content = '<ul class="story-list">\n' + "\n".join(items) + "\n</ul>"
        self.replace_generated_block(STORY_HTML, content)
        self.log("story.html を更新しました。")

    def replace_generated_block(self, html_path, new_content):
        start = "<!-- AUTO_GENERATED_START -->"
        end = "<!-- AUTO_GENERATED_END -->"
        text = html_path.read_text(encoding="utf-8")
        if start not in text or end not in text:
            raise RuntimeError(f"{html_path.name} に自動生成マーカーがありません。")
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        html_path.write_text(before + start + "\n" + new_content + "\n" + end + after, encoding="utf-8")


class SettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("設定")
        self.geometry("820x640")
        self.config_data = master.manager.load_config()
        self.selected_speaker = None
        self.create_widgets()
        self.load_values()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        tabs = ttk.Notebook(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        basic = ttk.Frame(tabs, padding=10)
        basic.columnconfigure(1, weight=1)
        tabs.add(basic, text="基本")

        ttk.Label(basic, text="サイト名").grid(row=0, column=0, sticky="w", pady=4)
        self.site_title = ttk.Entry(basic)
        self.site_title.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="サブタイトル").grid(row=1, column=0, sticky="w", pady=4)
        self.site_subtitle = ttk.Entry(basic)
        self.site_subtitle.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="トップ見出し").grid(row=2, column=0, sticky="w", pady=4)
        self.home_title = ttk.Entry(basic)
        self.home_title.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="日誌見出し").grid(row=3, column=0, sticky="w", pady=4)
        self.nisi_title = ttk.Entry(basic)
        self.nisi_title.grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="トップ説明 HTML").grid(row=4, column=0, sticky="nw", pady=4)
        self.home_desc = tk.Text(basic, height=10, wrap="word")
        self.home_desc.grid(row=4, column=1, sticky="nsew", pady=4)
        basic.rowconfigure(4, weight=1)

        speakers = ttk.Frame(tabs, padding=10)
        speakers.columnconfigure(1, weight=1)
        speakers.rowconfigure(0, weight=1)
        tabs.add(speakers, text="登場人物")

        self.speaker_list = tk.Listbox(speakers, width=18)
        self.speaker_list.grid(row=0, column=0, rowspan=5, sticky="ns", padx=(0, 8))
        self.speaker_list.bind("<<ListboxSelect>>", self.on_select_speaker)

        ttk.Label(speakers, text="名前").grid(row=0, column=1, sticky="nw")
        self.speaker_name = ttk.Entry(speakers)
        self.speaker_name.grid(row=0, column=2, sticky="ew", pady=(0, 6))
        ttk.Label(speakers, text="色").grid(row=1, column=1, sticky="nw")
        self.speaker_color = ttk.Entry(speakers)
        self.speaker_color.grid(row=1, column=2, sticky="ew", pady=(0, 6))
        ttk.Label(speakers, text="アイコン").grid(row=2, column=1, sticky="nw")
        self.speaker_icon = ttk.Entry(speakers)
        self.speaker_icon.grid(row=2, column=2, sticky="ew", pady=(0, 6))
        ttk.Label(speakers, text="自己紹介").grid(row=3, column=1, sticky="nw")
        self.speaker_desc = tk.Text(speakers, height=12, wrap="word")
        self.speaker_desc.grid(row=3, column=2, sticky="nsew")
        speaker_actions = ttk.Frame(speakers)
        speaker_actions.grid(row=4, column=2, sticky="ew", pady=(8, 0))
        ttk.Button(speaker_actions, text="反映", command=self.apply_speaker).pack(side="left")
        ttk.Button(speaker_actions, text="追加", command=self.add_speaker).pack(side="left", padx=4)
        ttk.Button(speaker_actions, text="削除", command=self.delete_speaker).pack(side="left")

        categories = ttk.Frame(tabs, padding=10)
        categories.columnconfigure(1, weight=1)
        categories.rowconfigure(0, weight=1)
        tabs.add(categories, text="分類")
        self.category_list = tk.Listbox(categories, width=18)
        self.category_list.grid(row=0, column=0, rowspan=4, sticky="ns", padx=(0, 8))
        self.category_list.bind("<<ListboxSelect>>", self.on_select_category)
        ttk.Label(categories, text="キー").grid(row=0, column=1, sticky="nw")
        self.category_key = ttk.Entry(categories)
        self.category_key.grid(row=0, column=2, sticky="ew", pady=(0, 6))
        ttk.Label(categories, text="表示名").grid(row=1, column=1, sticky="nw")
        self.category_name = ttk.Entry(categories)
        self.category_name.grid(row=1, column=2, sticky="ew", pady=(0, 6))
        ttk.Label(categories, text="説明").grid(row=2, column=1, sticky="nw")
        self.category_desc = tk.Text(categories, height=8, wrap="word")
        self.category_desc.grid(row=2, column=2, sticky="nsew")
        category_actions = ttk.Frame(categories)
        category_actions.grid(row=3, column=2, sticky="ew", pady=(8, 0))
        ttk.Button(category_actions, text="反映", command=self.apply_category).pack(side="left")
        ttk.Button(category_actions, text="追加", command=self.add_category).pack(side="left", padx=4)
        ttk.Button(category_actions, text="削除", command=self.delete_category).pack(side="left")

        about = ttk.Frame(tabs, padding=10)
        about.columnconfigure(0, weight=1)
        about.rowconfigure(0, weight=1)
        tabs.add(about, text="研究室紹介")
        self.about_html = tk.Text(about, wrap="word", undo=True)
        self.about_html.grid(row=0, column=0, sticky="nsew")

        bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        bottom.grid(row=1, column=0, sticky="ew")
        ttk.Button(bottom, text="保存", command=self.save).pack(side="right")
        ttk.Button(bottom, text="閉じる", command=self.destroy).pack(side="right", padx=4)

    def load_values(self):
        self.site_title.insert(0, self.config_data.get("site_title", ""))
        self.site_subtitle.insert(0, self.config_data.get("site_subtitle", ""))
        self.home_title.insert(0, self.config_data.get("home_title", ""))
        self.nisi_title.insert(0, self.config_data.get("nisi_title", ""))
        self.home_desc.insert("1.0", self.config_data.get("home_desc", ""))

        self.refresh_speaker_list()
        self.refresh_category_list()
        if ABOUT_HTML.exists():
            self.about_html.insert("1.0", ABOUT_HTML.read_text(encoding="utf-8"))

    def refresh_speaker_list(self):
        self.speaker_list.delete(0, "end")
        for name in self.config_data.setdefault("speakers", {}).keys():
            self.speaker_list.insert("end", name)

    def refresh_category_list(self):
        self.category_list.delete(0, "end")
        for key in self.config_data.setdefault("categories", {}).keys():
            self.category_list.insert("end", key)

    def on_select_speaker(self, _event=None):
        selection = self.speaker_list.curselection()
        if not selection:
            return
        name = self.speaker_list.get(selection[0])
        self.selected_speaker = name
        data = self.config_data.get("speakers", {}).get(name, {})
        self.speaker_name.delete(0, "end")
        self.speaker_name.insert(0, name)
        self.speaker_color.delete(0, "end")
        self.speaker_color.insert(0, data.get("color", ""))
        self.speaker_icon.delete(0, "end")
        self.speaker_icon.insert(0, data.get("icon", ""))
        self.speaker_desc.delete("1.0", "end")
        self.speaker_desc.insert("1.0", data.get("desc", ""))

    def apply_speaker(self):
        old_name = self.selected_speaker
        name = self.speaker_name.get().strip()
        if not name:
            return
        speakers = self.config_data.setdefault("speakers", {})
        if old_name and old_name != name:
            speakers.pop(old_name, None)
        speakers[name] = {
            "color": self.speaker_color.get().strip(),
            "icon": self.speaker_icon.get().strip(),
            "desc": self.speaker_desc.get("1.0", "end-1c"),
        }
        self.selected_speaker = name
        self.refresh_speaker_list()

    def add_speaker(self):
        self.selected_speaker = None
        self.speaker_name.delete(0, "end")
        self.speaker_color.delete(0, "end")
        self.speaker_color.insert(0, "#f0f0f0")
        self.speaker_icon.delete(0, "end")
        self.speaker_desc.delete("1.0", "end")

    def delete_speaker(self):
        if self.selected_speaker:
            self.config_data.setdefault("speakers", {}).pop(self.selected_speaker, None)
            self.selected_speaker = None
            self.refresh_speaker_list()

    def on_select_category(self, _event=None):
        selection = self.category_list.curselection()
        if not selection:
            return
        key = self.category_list.get(selection[0])
        data = self.config_data.get("categories", {}).get(key, {})
        self.category_key.delete(0, "end")
        self.category_key.insert(0, key)
        self.category_name.delete(0, "end")
        self.category_name.insert(0, data.get("name", key) if isinstance(data, dict) else str(data))
        self.category_desc.delete("1.0", "end")
        self.category_desc.insert("1.0", data.get("desc", "") if isinstance(data, dict) else "")

    def apply_category(self):
        key = self.category_key.get().strip()
        if not key:
            return
        self.config_data.setdefault("categories", {})[key] = {
            "name": self.category_name.get().strip() or key,
            "desc": self.category_desc.get("1.0", "end-1c"),
        }
        self.refresh_category_list()

    def add_category(self):
        self.category_key.delete(0, "end")
        self.category_name.delete(0, "end")
        self.category_desc.delete("1.0", "end")

    def delete_category(self):
        selection = self.category_list.curselection()
        if not selection:
            return
        key = self.category_list.get(selection[0])
        self.config_data.setdefault("categories", {}).pop(key, None)
        self.refresh_category_list()

    def save(self):
        self.apply_speaker()
        self.apply_category()
        self.config_data["site_title"] = self.site_title.get().strip()
        self.config_data["site_subtitle"] = self.site_subtitle.get().strip()
        self.config_data["home_title"] = self.home_title.get().strip()
        self.config_data["nisi_title"] = self.nisi_title.get().strip()
        self.config_data["home_desc"] = self.home_desc.get("1.0", "end-1c")
        CONFIG_FILE.write_text(json.dumps(self.config_data, ensure_ascii=False, indent=4), encoding="utf-8")
        ABOUT_HTML.write_text(self.about_html.get("1.0", "end-1c"), encoding="utf-8")
        self.master.manager.config = self.master.manager.load_config()
        self.master.refresh_articles()
        self.master.log("設定を保存しました。")
        messagebox.showinfo("設定", "保存しました。")


class SegawaWriter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Segawa Writer")
        self.geometry("1100x720")
        self.manager = SiteManager(log_callback=self.log)
        self.current_path = None
        self.server_process = None
        self.article_paths = {}
        self.create_widgets()
        self.refresh_articles()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        command_tabs = ttk.Notebook(self)
        command_tabs.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        article_tab = ttk.Frame(command_tabs, padding=6)
        command_tabs.add(article_tab, text="記事")
        ttk.Button(article_tab, text="新規", command=self.new_article).pack(side="left")
        ttk.Button(article_tab, text="保存", command=self.save_current).pack(side="left", padx=4)
        ttk.Button(article_tab, text="保存してサイト反映", command=self.save_and_update).pack(side="left", padx=4)
        ttk.Button(article_tab, text="再読込", command=self.refresh_articles).pack(side="left", padx=4)

        publish_tab = ttk.Frame(command_tabs, padding=6)
        command_tabs.add(publish_tab, text="公開")
        ttk.Button(publish_tab, text="サイト反映", command=self.update_site).pack(side="left")
        ttk.Button(publish_tab, text="保存して公開", command=self.save_update_and_publish).pack(side="left", padx=4)
        ttk.Button(publish_tab, text="プレビュー", command=self.preview_current).pack(side="left", padx=4)

        settings_tab = ttk.Frame(command_tabs, padding=6)
        command_tabs.add(settings_tab, text="設定")
        ttk.Button(settings_tab, text="設定を開く", command=self.open_settings).pack(side="left")

        content = ttk.Frame(self)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content, padding=8)
        left.grid(row=0, column=0, sticky="ns")
        left.rowconfigure(1, weight=1)

        ttk.Label(left, text="記事").grid(row=0, column=0, sticky="w")

        columns = ("status", "date")
        self.article_tree = ttk.Treeview(left, columns=columns, show="tree headings", height=24)
        self.article_tree.heading("#0", text="タイトル")
        self.article_tree.heading("status", text="状態")
        self.article_tree.heading("date", text="日付")
        self.article_tree.column("#0", width=270)
        self.article_tree.column("status", width=70)
        self.article_tree.column("date", width=90)
        self.article_tree.grid(row=1, column=0, sticky="ns")
        self.article_tree.bind("<<TreeviewSelect>>", self.on_select_article)
        self.article_tree.bind("<Button-3>", self.show_article_menu)

        self.article_menu = tk.Menu(self, tearoff=0)
        self.article_menu.add_command(label="公開/非公開を切り替え", command=self.toggle_selected_publish_status)

        right = ttk.Frame(content, padding=8)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        editor_frame = ttk.Frame(right)
        editor_frame.grid(row=0, column=0, sticky="nsew")
        editor_frame.columnconfigure(1, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        self.line_numbers = tk.Text(
            editor_frame,
            width=5,
            padx=4,
            takefocus=0,
            border=0,
            background="#f0f0f0",
            foreground="#777",
            state="disabled",
            font=("Consolas", 11),
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.editor = tk.Text(editor_frame, wrap="none", undo=True, font=("Yu Gothic UI", 11))
        self.editor.grid(row=0, column=1, sticky="nsew")
        scrollbar_y = ttk.Scrollbar(editor_frame, orient="vertical", command=self.on_editor_scrollbar)
        scrollbar_y.grid(row=0, column=2, sticky="ns")
        scrollbar_x = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.editor.xview)
        scrollbar_x.grid(row=1, column=1, sticky="ew")
        self.editor.configure(yscrollcommand=lambda first, last: self.on_editor_yscroll(first, last, scrollbar_y), xscrollcommand=scrollbar_x.set)
        self.editor.bind("<KeyRelease>", self.schedule_line_number_update)
        self.editor.bind("<MouseWheel>", self.schedule_line_number_update)
        self.editor.bind("<ButtonRelease-1>", self.schedule_line_number_update)

        help_text = (
            "形式: Title/Date/Type/StoryOrder/Status のあとに本文。"
            " 発言は「瀬川 左」「栃村 右」+ インデント本文。"
            " ブロック: # 見出し, !math:, !code: python, !box: 定義, !fold:, !truth:"
        )
        ttk.Label(right, text=help_text, foreground="#555").grid(row=1, column=0, sticky="ew", pady=(6, 0))

        bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.log_area = tk.Text(bottom, height=5, wrap="word", state="disabled")
        self.log_area.grid(row=0, column=0, sticky="ew")

    def log(self, message):
        if not hasattr(self, "log_area"):
            print(message)
            return
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def refresh_articles(self):
        self.article_tree.delete(*self.article_tree.get_children())
        self.article_paths = {}
        grouped = {}
        for item in self.manager.article_files():
            meta = self.manager.parse_article_file(item)
            grouped.setdefault(meta["category"], []).append(meta)

        categories = self.manager.categories
        for category in sorted(grouped.keys()):
            display_name = categories.get(category, {}).get("name", category) if isinstance(categories.get(category, {}), dict) else category
            parent_iid = f"category::{category}"
            self.article_tree.insert("", "end", iid=parent_iid, text=f"{display_name} ({category})", values=("", ""))
            for meta in sorted(grouped[category], key=lambda x: (x["date"], x["title"]), reverse=True):
                path = meta["path"]
                iid = str(path)
                self.article_paths[iid] = path
                status = "公開" if meta["published"] else "非公開"
                self.article_tree.insert(parent_iid, "end", iid=iid, text=meta["title"], values=(status, meta["date"]))
            self.article_tree.item(parent_iid, open=True)
        self.log("記事一覧を読み込みました。")

    def on_select_article(self, _event=None):
        selected = self.article_tree.selection()
        if not selected:
            return
        path = self.article_paths.get(selected[0])
        if not path:
            return
        if self.current_path and self.editor.edit_modified():
            if not messagebox.askyesno("未保存の変更", "現在の記事に未保存の変更があります。破棄して開きますか？"):
                return
        self.current_path = path
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", path.read_text(encoding="utf-8"))
        self.editor.edit_modified(False)
        self.update_line_numbers()
        self.log(f"開きました: {path.relative_to(BASE_DIR)}")

    def new_article(self):
        categories = [k for k in self.manager.categories.keys() if k != "trash"]
        category = simpledialog.askstring("分類", f"分類を入力してください: {', '.join(categories)}", initialvalue="logic")
        if not category:
            return
        category_dir = POSTS_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = category_dir / f"{name}.txt"
        path.write_text(DEFAULT_TEMPLATE.format(date=datetime.date.today().strftime("%Y/%m/%d")), encoding="utf-8")
        self.refresh_articles()
        self.current_path = path
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", path.read_text(encoding="utf-8"))
        self.editor.edit_modified(False)
        self.update_line_numbers()
        self.log(f"新規記事を作成しました: {path.relative_to(BASE_DIR)}")

    def save_current(self):
        if not self.current_path:
            messagebox.showinfo("保存", "記事を選択してください。")
            return False
        self.current_path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        self.editor.edit_modified(False)
        self.log(f"保存しました: {self.current_path.relative_to(BASE_DIR)}")
        self.refresh_articles()
        return True

    def save_and_update(self):
        if self.save_current():
            self.update_site()

    def save_update_and_publish(self):
        if not self.save_current():
            return
        try:
            self.manager.update_site()
            self.refresh_articles()
            self.publish_to_git()
            messagebox.showinfo("公開", "GitHub へ公開しました。")
        except Exception as exc:
            messagebox.showerror("公開エラー", str(exc))
            self.log(f"公開エラー: {exc}")

    def update_site(self):
        try:
            self.manager.update_site()
            self.refresh_articles()
        except Exception as exc:
            messagebox.showerror("サイト反映エラー", str(exc))
            self.log(f"エラー: {exc}")

    def run_git(self, args):
        command = ["git", *args]
        self.log("$ " + " ".join(command))
        env = os.environ.copy()
        path_parts = [
            env.get("Path", ""),
            os.environ.get("PATH", ""),
            os.getenv("Path", ""),
            os.getenv("PATH", ""),
        ]
        for scope in ("User", "Machine"):
            scope_path = os.environ.get(f"{scope}Path")
            if scope_path:
                path_parts.append(scope_path)
        user_path = os.popen("powershell -NoProfile -Command \"[Environment]::GetEnvironmentVariable('Path','User')\"").read().strip()
        machine_path = os.popen("powershell -NoProfile -Command \"[Environment]::GetEnvironmentVariable('Path','Machine')\"").read().strip()
        env["Path"] = ";".join(part for part in [*path_parts, user_path, machine_path] if part)
        try:
            result = subprocess.run(
                command,
                cwd=BASE_DIR,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("git コマンドが見つかりません。Git for Windows をインストールするか PATH を通してください。") from exc

        output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
        if output:
            self.log(output)
        if result.returncode != 0:
            raise RuntimeError(f"git コマンドに失敗しました: {' '.join(command)}")
        return output

    def publish_to_git(self):
        if not (BASE_DIR / ".git").exists():
            raise RuntimeError(".git が見つかりません。リポジトリ設定を確認してください。")

        self.run_git(["add", "-A"])
        status = self.run_git(["status", "--porcelain"])
        if status:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.run_git(["commit", "-m", f"Update site {timestamp}"])
        else:
            self.log("Git に公開する変更はありません。")

        self.run_git(["status", "--short", "--branch"])
        self.run_git(["push", "--force-with-lease", "origin", "main"])

    def preview_current(self):
        if self.save_current():
            self.update_site()
        if not self.current_path:
            return
        article_id = f"{self.current_path.parent.name}/{self.current_path.stem}"
        url = f"http://localhost:8000/article_view.html?p={article_id}"
        if not self.server_process or self.server_process.poll() is not None:
            self.server_process = subprocess.Popen(
                ["python", "-m", "http.server", "8000"],
                cwd=BASE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.log("プレビュー用サーバーを http://localhost:8000 で起動しました。")
        webbrowser.open(url)

    def on_editor_scrollbar(self, *args):
        self.editor.yview(*args)
        self.line_numbers.yview(*args)
        self.update_line_numbers()

    def on_editor_yscroll(self, first, last, scrollbar):
        scrollbar.set(first, last)
        self.line_numbers.yview_moveto(first)
        self.update_line_numbers()

    def schedule_line_number_update(self, _event=None):
        self.after_idle(self.update_line_numbers)

    def update_line_numbers(self):
        if not hasattr(self, "line_numbers"):
            return
        line_count = int(self.editor.index("end-1c").split(".")[0])
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", numbers)
        self.line_numbers.configure(state="disabled")
        self.line_numbers.yview_moveto(self.editor.yview()[0])

    def show_article_menu(self, event):
        row = self.article_tree.identify_row(event.y)
        if not row or row not in self.article_paths:
            return
        self.article_tree.selection_set(row)
        self.article_menu.tk_popup(event.x_root, event.y_root)

    def toggle_selected_publish_status(self):
        selected = self.article_tree.selection()
        if not selected:
            return
        path = self.article_paths.get(selected[0])
        if not path:
            return
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        status_index = None
        current_public = True
        for idx, line in enumerate(lines[:12]):
            if line.lower().startswith("status:"):
                status_index = idx
                value = line.split(":", 1)[1].strip().lower()
                current_public = value not in {"draft", "private", "非公開"}
                break
        new_status = "draft" if current_public else "public"
        if status_index is None:
            insert_at = 0
            for idx, line in enumerate(lines[:12]):
                if ":" in line:
                    insert_at = idx + 1
                    continue
                break
            lines.insert(insert_at, f"Status: {new_status}")
        else:
            lines[status_index] = f"Status: {new_status}"
        path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        if self.current_path == path:
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", path.read_text(encoding="utf-8"))
            self.editor.edit_modified(False)
            self.update_line_numbers()
        self.refresh_articles()
        self.log(f"公開状態を切り替えました: {path.relative_to(BASE_DIR)} -> {new_status}")

    def open_settings(self):
        SettingsWindow(self)


if __name__ == "__main__":
    app = SegawaWriter()
    app.mainloop()
