import json
import sys
import os
import re

def json_to_segawa_script(json_path, txt_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lines = []
    
    # ヘッダー
    lines.append(f"Title: {data.get('title', '無題')}")
    lines.append(f"Date: {data.get('date', '----/--/--')}")
    if not data.get('published', True):
        lines.append("Status: draft")
    lines.append("") # 空行

    # 本文
    for item in data.get('data', []):
        type_ = item.get('type')
        content = item.get('content', '')
        
        # HTMLタグの簡易逆変換 (<br> -> \n)
        content = content.replace("<br>", "\n")
        
        # インデント処理
        def indent_text(text):
            return "\n".join(["    " + line for line in text.split('\n')])

        if type_ == 'heading':
            lines.append(f"# {content}")
            
        elif type_ == 'dialogue':
            speaker = item.get('speaker', 'Unknown')
            lines.append(speaker)
            lines.append(indent_text(content))
            
        elif type_ == 'box':
            title = item.get('title', '')
            lines.append(f"!box: {title}")
            lines.append(indent_text(content))
            
        elif type_ == 'math':
            lines.append("!math:")
            lines.append(indent_text(content))
            
        elif type_ == 'code':
            lang = item.get('language', '')
            lines.append(f"!code: {lang}")
            lines.append(indent_text(content))
            
        elif type_ == 'image':
            src = item.get('src', '')
            caption = item.get('caption', '')
            caption_part = f" [{caption}]" if caption else ""
            lines.append(f"!img: {src}{caption_part}")
            
        elif type_ == 'details':
            summary = item.get('summary', '')
            lines.append(f"!fold: {summary}")
            lines.append(indent_text(content))
            
        lines.append("") # ブロック間の空行

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    print(f"Restored: {txt_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json2txt.py <input.json> [output.txt]")
    else:
        in_file = sys.argv[1]
        out_file = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(in_file)[0] + ".txt"
        json_to_segawa_script(in_file, out_file)
