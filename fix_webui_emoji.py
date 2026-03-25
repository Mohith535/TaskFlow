"""Fix surrogate emoji sequences in web_ui.py that corrupt the HTML."""
import re

path = 'task_manager/web_ui.py'

with open(path, encoding='latin-1') as f:
    content = f.read()

# Replace the entire victory message block with clean ASCII
old_block = """            if (total === 0)     msg = 'Fresh start. Add your first win. \\\\u2b50';
            else if (done === 0) msg = 'Momentum building. Pick one. \\\\u26a1';
            else if (pct < 50)   msg = 'Flow state activated. \\\\ud83d\\\\udd25';
            else if (pct < 100)  msg = \"Mastery mode. You're unstoppable. \\\\ud83d\\\\udcaa\";
            else                 msg = 'Cleared! \\\\ud83c\\\\udf89 Reset or celebrate?';"""

new_block = """            if (total === 0)     msg = 'Fresh start. Add your first win.';
            else if (done === 0) msg = 'Momentum building. Pick one.';
            else if (pct < 50)   msg = 'Flow state activated.';
            else if (pct < 100)  msg = 'Mastery mode. Unstoppable.';
            else                 msg = 'All tasks cleared! Celebrate.';"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Replaced victory block directly.")
else:
    # Fallback: use regex to catch any variant
    content = re.sub(
        r"msg = 'Fresh start[^']*';",
        "msg = 'Fresh start. Add your first win.';",
        content
    )
    content = re.sub(
        r"msg = 'Momentum building[^']*';",
        "msg = 'Momentum building. Pick one.';",
        content
    )
    content = re.sub(
        r"msg = 'Flow state activated[^']*';",
        "msg = 'Flow state activated.';",
        content
    )
    content = re.sub(
        r'msg = ["\']Mastery mode[^"\']*["\'];',
        "msg = 'Mastery mode. Unstoppable.';",
        content
    )
    content = re.sub(
        r"msg = 'Cleared![^']*';",
        "msg = 'All tasks cleared! Celebrate.';",
        content
    )
    print("Used regex fallback.")

# Also strip any remaining surrogate pairs just in case
# Encode to utf-8 with surrogateescape to strip bad chars
content_bytes = content.encode('latin-1')
content_clean = content_bytes.decode('utf-8', errors='replace')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_clean)

print("Done. File written as clean UTF-8.")

# Verify
with open(path, encoding='utf-8') as f:
    verify = f.read()
print(f"File size: {len(verify)} chars. Surrogate check: {'bad' if chr(0xD83D) in verify else 'clean'}")
