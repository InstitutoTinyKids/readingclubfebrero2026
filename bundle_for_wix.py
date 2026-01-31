import os
import base64
import re
import json

# Configuration
SOURCE_HTML = "The Girl Who Never Made Mistakes - Libro Febrero 2026.html"
OUTPUT_HTML = "The Girl Who Never Made Mistakes - Wix Version.html"
IMAGES_DIR = "images_extracted"
AUDIOS_DIR = "audios"

def get_base64_mime(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    mime_type = "application/octet-stream"
    if ext == ".png": mime_type = "image/png"
    elif ext == ".jpg" or ext == ".jpeg": mime_type = "image/jpeg"
    elif ext == ".wav": mime_type = "audio/wav"
    elif ext == ".mp3": mime_type = "audio/mpeg"
    
    with open(filepath, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded}"

print("Reading source HTML...")
with open(SOURCE_HTML, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Embed Images in storyData
print("Embedding images...")
def replace_image_url(match):
    path = match.group(1)
    # The path in HTML is relative, e.g., "images_extracted/page_4.png"
    # We need to find this file locally.
    local_path = path.replace('/', os.sep)
    if os.path.exists(local_path):
        print(f"  Encoding {local_path}...")
        b64 = get_base64_mime(local_path)
        return f'imageUrl: "{b64}"'
    else:
        print(f"  Warning: Image not found {local_path}")
        return match.group(0) # No change

# Access imageUrl: "path"
# Regex matches: imageUrl: "([^"]+)"
content = re.sub(r'imageUrl: "([^"]+)"', replace_image_url, content)

# 2. Embed Background Image (bg.png)
# Expected CSS/JS usage: "bg.png" in const bgImage = ... or similar?
# Let's check the HTML for "bg.png".
# Based on context, it was used in `backgroundImage: 'url(bg.png)'` possibly or an <img> tag?
# In previous edits, I saw: <div className="absolute inset-0 bg-cover bg-center transition-all duration-1000 transform" style={{ backgroundImage: 'url(bg.png)' }}>
if os.path.exists("bg.png"):
    print("Embedding bg.png...")
    bg_b64 = get_base64_mime("bg.png")
    content = content.replace("url(bg.png)", f"url({bg_b64})")
    content = content.replace("'bg.png'", f"'{bg_b64}'")
    content = content.replace('"bg.png"', f'"{bg_b64}"')

# 3. Create Audio Library Object
print("Processing audios...")
audio_library = {}
# Scan audios dir
if os.path.exists(AUDIOS_DIR):
    for filename in os.listdir(AUDIOS_DIR):
        if filename.endswith(".wav") or filename.endswith(".mp3"):
            # Key strategy: 
            # Code uses: `audio${idStr}.wav` or `audio${idStr}_es.wav`
            # We will use the filename as the key.
            print(f"  Encoding {filename}...")
            b64 = get_base64_mime(os.path.join(AUDIOS_DIR, filename))
            audio_library[filename] = b64

# Inject the audio library variable
audio_lib_json = json.dumps(audio_library, indent=4)
# We insert it before the App component definition or inside it.
# Ideally before `const storyData` so it's global scope within the script.
injection_point = "// --- STORY DATA (Mapping to Extracted PDF Pages) ---"
content = content.replace(injection_point, f"const audioFiles = {audio_lib_json};\n\n{injection_point}")

# 4. Modify Audio Logic to use the library
print("Modifying audio logic...")
# Look for: const audioSrc = lang === 'es' ? `audios/audio${idStr}_es.wav` : `audios/audio${idStr}.wav`;
# Replace with:
# const filename = lang === 'es' ? `audio${idStr}_es.wav` : `audio${idStr}.wav`;
# const audioSrc = audioFiles[filename];

# Regex is risky given variable whitespace. I'll search for the specific string I added recently.
target_line_part = "const audioSrc = lang === 'es' ? `audios/audio${idStr}_es.wav` : `audios/audio${idStr}.wav`;"
new_line = """
                // WIX VERSION: Load from Base64 library
                const filename = lang === 'es' ? `audio${idStr}_es.wav` : `audio${idStr}.wav`;
                const audioSrc = audioFiles[filename];
"""

if target_line_part in content:
    content = content.replace(target_line_part, new_line)
else:
    print("WARNING: Could not find exact audioSrc line to replace. The audio logic might not work in WIX version.")
    # Fallback to loose regex if exact match fails due to whitespace
    content = re.sub(r'const audioSrc = lang === .*?;', new_line.strip(), content)

# 5. Write Output
print(f"Writing {OUTPUT_HTML}...")
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! Bundle created.")
