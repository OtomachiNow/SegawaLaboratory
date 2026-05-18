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
        "type": "math",
        "order": 0,
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
        elif line.lower().startswith("type:"):
            article["type"] = line[5:].strip().lower() or "math"
        elif line.lower().startswith("storyorder:"):
            raw_order = line[11:].strip()
            try:
                article["order"] = float(raw_order)
            except ValueError:
                article["order"] = 0
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

    def box_class(title):
        if "定義" in title:
            return "box-def"
        if "定理" in title:
            return "box-thm"
        if "証明" in title:
            return "box-proof"
        if "まとめ" in title:
            return "box-summary"
        if "宿題" in title:
            return "box-hw"
        return ""

    def strip_block_indent(text):
        if text.startswith("    "):
            return text[4:]
        if text.startswith("\t"):
            return text[1:]
        return text

    def read_begin_block(start_idx, begin_prefix, end_marker):
        header = lines[start_idx].strip()
        title = header[len(begin_prefix):].strip()
        content_lines = []
        depth = 1
        idx = start_idx + 1
        while idx < len(lines):
            current = lines[idx].strip()
            if current.startswith(begin_prefix):
                depth += 1
                content_lines.append(lines[idx])
            elif current == end_marker:
                depth -= 1
                if depth == 0:
                    return title, content_lines, idx + 1
                content_lines.append(lines[idx])
            else:
                content_lines.append(lines[idx])
            idx += 1
        return title, content_lines, idx

    def format_block_content(block_lines):
        result = []
        idx = 0
        while idx < len(block_lines):
            stripped = block_lines[idx].strip()

            if stripped.startswith("!begin:math"):
                math_lines = []
                idx += 1
                while idx < len(block_lines) and block_lines[idx].strip() != "!end:math":
                    math_lines.append(strip_block_indent(block_lines[idx].rstrip()))
                    idx += 1
                if idx < len(block_lines):
                    idx += 1
                math_content = "\n".join(line.strip() for line in math_lines).strip()
                if math_content.startswith("$$") and math_content.endswith("$$"):
                    result.append(math_content)
                else:
                    result.append("$$\n" + math_content + "\n$$")
                continue

            if stripped.startswith("!begin:box:"):
                nested_title = stripped[len("!begin:box:"):].strip()
                nested_lines = []
                depth = 1
                idx += 1
                while idx < len(block_lines):
                    current = block_lines[idx].strip()
                    if current.startswith("!begin:box:"):
                        depth += 1
                        nested_lines.append(block_lines[idx])
                    elif current == "!end:box":
                        depth -= 1
                        if depth == 0:
                            idx += 1
                            break
                        nested_lines.append(block_lines[idx])
                    else:
                        nested_lines.append(block_lines[idx])
                    idx += 1
                nested_body = format_block_content(nested_lines)
                css_class = box_class(nested_title)
                result.append(
                    f'<div class="article-box {css_class}">'
                    f'<div class="box-title">{format_line(nested_title)}</div>'
                    f'<div class="box-body">{nested_body}</div>'
                    f'</div>'
                )
                continue

            if stripped in {"!end:box", "!end:math"}:
                idx += 1
                continue

            result.append(format_line(strip_block_indent(block_lines[idx].rstrip())))
            idx += 1

        return "\n".join(result).strip()

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
                "type": "fold",
                "summary": summary,
                "content": "\n".join(content_lines)
            })
            continue

        # 4.5. 真理値表 (!truth:)
        if stripped.startswith("!truth:"):
            rows = []
            line_idx += 1
            while line_idx < len(lines):
                next_raw = lines[line_idx]
                if next_raw.strip() and not (next_raw.startswith(" ") or next_raw.startswith("\t")):
                    break
                row_text = next_raw.strip()
                if row_text:
                    separator = "|" if "|" in row_text else ","
                    rows.append([format_line(cell.strip()) for cell in row_text.split(separator)])
                line_idx += 1
            
            article["data"].append({
                "type": "truth",
                "rows": rows
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

        # 4.1. 旧記法の独立数式 (!begin:math ... !end:math)
        if stripped.startswith("!begin:math"):
            content_lines = []
            line_idx += 1
            while line_idx < len(lines) and lines[line_idx].strip() != "!end:math":
                content_lines.append(strip_block_indent(lines[line_idx].rstrip()))
                line_idx += 1
            if line_idx < len(lines):
                line_idx += 1
            content = "\n".join(line.strip() for line in content_lines).strip()
            if not (content.startswith("$$") and content.endswith("$$")):
                content = "$$\n" + content + "\n$$"
            article["data"].append({
                "type": "math",
                "content": content
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
                "content": "\n".join(content_lines)
            })
            continue

        # 6.1. 旧記法の囲み枠 (!begin:box: ... !end:box)
        if stripped.startswith("!begin:box:"):
            title, block_lines, line_idx = read_begin_block(line_idx, "!begin:box:", "!end:box")
            title = format_line(title)
            article["data"].append({
                "type": "box",
                "title": title,
                "content": format_block_content(block_lines)
            })
            continue

        if stripped in {"!end:box", "!end:math"}:
            line_idx += 1
            continue

        # 7. 通常の会話 (話者名)
        speaker_parts = stripped.split()
        speaker = speaker_parts[0]
        side = "left"
        if len(speaker_parts) > 1 and speaker_parts[-1] in ["左", "右", "left", "right"]:
            side = "right" if speaker_parts[-1] in ["右", "right"] else "left"
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
                "side": side,
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
