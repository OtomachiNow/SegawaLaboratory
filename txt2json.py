import json
import sys
import re
import os

def parse_segawa_script(filepath):
    """
    Segawa Script形式のテキストファイルをパースして辞書オブジェクトを返す
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    article = {
        "title": "無題",
        "date": "----/--/--",
        "published": True, # デフォルト公開
        "data": []
    }

    line_idx = 0
    
    # --- ヘッダー解析 ---
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line:
            line_idx += 1
            continue
            
        if line.lower().startswith("title:"):
            article["title"] = line[6:].strip()
        elif line.lower().startswith("date:"):
            article["date"] = line[5:].strip()
        elif line.lower().startswith("status:"):
            status = line[7:].strip().lower()
            if status in ["draft", "private", "非公開"]:
                article["published"] = False
        else:
            break
        line_idx += 1

    # Markdown風記法の変換
    def format_line(text):
        # コード (`...`)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        # 太字 (**...**)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # リスト (* ...) -> 中黒
        if text.startswith("* "):
            text = "・" + text[2:]
        return text

    # --- 本文解析 ---
    while line_idx < len(lines):
        raw_line = lines[line_idx]
        stripped = raw_line.strip()
        
        if not stripped:
            line_idx += 1
            continue

        # 1. 見出し (#)
        if stripped.startswith("#"):
            content = stripped.lstrip("#").strip()
            # 見出しにも適用
            content = format_line(content)
            article["data"].append({
                "type": "heading",
                "content": content
            })
            line_idx += 1
            continue

        # 2. 画像 (!img:)
        if stripped.startswith("!img:"):
            # ... (変更なし) ...
            content = stripped[5:].strip()
            match = re.match(r'^(.*?)(\s*\[(.*?)\])?$', content)
            src = match.group(1).strip() if match else content
            caption = match.group(3) if match and match.group(3) else ""
            
            article["data"].append({
                "type": "image",
                "src": src,
                "caption": caption
            })
            line_idx += 1
            continue

        # 3. 折りたたみ (!fold:)
        if stripped.startswith("!fold:"):
            summary = stripped[6:].strip()
            summary = format_line(summary)
            
            content_lines = []
            line_idx += 1
            while line_idx < len(lines):
                next_raw = lines[line_idx]
                # インデントされていない、かつ空行でない場合はブロック終了
                if next_raw.strip() and not (next_raw.startswith(" ") or next_raw.startswith("\t")):
                    break
                content_lines.append(format_line(next_raw.strip()))
                line_idx += 1
            
            article["data"].append({
                "type": "details",
                "summary": summary,
                "content": "<br>".join(content_lines)
            })
            continue

        # 4. 独立数式 (!math:)
        if stripped.startswith("!math:"):
            content_lines = []
            line_idx += 1
            while line_idx < len(lines):
                next_raw = lines[line_idx]
                if next_raw.strip() and not (next_raw.startswith(" ") or next_raw.startswith("\t")):
                    break
                content_lines.append(next_raw.strip())
                line_idx += 1
            
            article["data"].append({
                "type": "math",
                "content": "\n".join(content_lines)
            })
            continue

        # 5. コードブロック (!code:)
        if stripped.startswith("!code:"):
            lang = stripped[6:].strip()
            content_lines = []
            line_idx += 1
            while line_idx < len(lines):
                next_raw = lines[line_idx]
                if next_raw.strip() and not (next_raw.startswith(" ") or next_raw.startswith("\t")):
                    break
                content_lines.append(next_raw.rstrip())
                line_idx += 1
            
            article["data"].append({
                "type": "code",
                "language": lang,
                "content": "\n".join(content_lines)
            })
            continue

        # 6. 囲み枠 (!box:)
        if stripped.startswith("!box:"):
            title = stripped[5:].strip()
            title = format_line(title)
            content_lines = []
            line_idx += 1
            while line_idx < len(lines):
                next_raw = lines[line_idx]
                if next_raw.strip() and not (next_raw.startswith(" ") or next_raw.startswith("\t")):
                    break
                content_lines.append(format_line(next_raw.strip()))
                line_idx += 1
            
            article["data"].append({
                "type": "box",
                "title": title,
                "content": "<br>".join(content_lines)
            })
            continue

        # 7. 通常の会話 (話者名)
        speaker = stripped
        content_lines = []
        line_idx += 1
        while line_idx < len(lines):
            next_raw = lines[line_idx]
            if next_raw.strip() and not (next_raw.startswith(" ") or next_raw.startswith("\t")):
                break
            content_lines.append(format_line(next_raw.strip()))
            line_idx += 1

        if content_lines:
            content_html = "<br>".join(content_lines)
            article["data"].append({
                "type": "dialogue",
                "speaker": speaker,
                "content": content_html
            })

    return article

def main():
    if len(sys.argv) < 2:
        print("Usage: python txt2json.py <input_file_or_dir> [output_file.json]")
        return

    input_path = sys.argv[1]
    
    # ディレクトリ指定の場合の一括変換
    if os.path.isdir(input_path):
        print(f"Converting all .txt files in directory: {input_path}")
        count = 0
        for root, dirs, files in os.walk(input_path):
            for file in files:
                if file.endswith(".txt"):
                    txt_path = os.path.join(root, file)
                    json_path = os.path.splitext(txt_path)[0] + ".json"
                    try:
                        article_data = parse_segawa_script(txt_path)
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(article_data, f, indent=2, ensure_ascii=False)
                        print(f"  Converted: {file} -> {os.path.basename(json_path)}")
                        count += 1
                    except Exception as e:
                        print(f"  Error converting {file}: {e}")
        print(f"Total {count} files converted.")
        return

    # ファイル指定の場合（既存処理）
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".json"

    try:
        article_data = parse_segawa_script(input_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully converted '{input_path}' to '{output_path}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()