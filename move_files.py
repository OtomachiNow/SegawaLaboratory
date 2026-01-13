import os
import shutil

# 現在のディレクトリ (SegawaLab)
base_dir = os.getcwd()
target_dir = os.path.join(base_dir, "瀬川研究室執筆")
exclude_dirs = ["瀬川研究室執筆", "SegawaLab執筆用アプリ制作"]

# ファイルとフォルダのリストを取得
for item in os.listdir(base_dir):
    if item in exclude_dirs:
        continue
    
    src_path = os.path.join(base_dir, item)
    dst_path = os.path.join(target_dir, item)
    
    print(f"Moving {item} to {target_dir}")
    try:
        shutil.move(src_path, dst_path)
    except Exception as e:
        print(f"Error moving {item}: {e}")

# .git フォルダの移動（os.listdirには通常含まれるが念のため）
# Windowsの場合、os.listdirで.gitも見えるはずだが、見えなかった場合のために明示的に
git_dir = os.path.join(base_dir, ".git")
if os.path.exists(git_dir):
    try:
        shutil.move(git_dir, os.path.join(target_dir, ".git"))
        print("Moved .git directory")
    except Exception as e:
        print(f"Error moving .git: {e}")
