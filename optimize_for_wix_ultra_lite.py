import os
import base64
import re
import json
import wave
import audioop
from PIL import Image
import io

# Configuration
SOURCE_HTML = "The Girl Who Never Made Mistakes - Libro Febrero 2026.html"
OUTPUT_HTML = "The Girl Who Never Made Mistakes - Wix Ultra Lite.html"
IMAGES_DIR = "images_extracted"
AUDIOS_DIR = "audios"

# AGGRESSIVE Optimization Settings
JPG_QUALITY = 50            # Aggressive compression
MAX_IMG_WIDTH = 800         # Resize huge images
AUDIO_TARGET_RATE = 11025   # Very low sample rate (phone quality)
AUDIO_KEEP_MONO = True      

def optimize_image_to_base64(filepath):
    """Opens an image, resizes, converts to JPG q50, returns base64 str"""
    try:
        with Image.open(filepath) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if too big
            if img.width > MAX_IMG_WIDTH:
                ratio = MAX_IMG_WIDTH / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((MAX_IMG_WIDTH, new_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=JPG_QUALITY, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"  Error optimizing image {filepath}: {e}")
        return None

def optimize_audio_to_base64(filepath):
    """Aggressive WAV downsampling"""
    try:
        with wave.open(filepath, 'rb') as wav:
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()
            content = wav.readframes(n_frames)

            # Mono
            if n_channels == 2 and AUDIO_KEEP_MONO:
                content = audioop.tomono(content, sampwidth, 1, 1)
                n_channels = 1
            
            # Downsample aggressively
            if framerate > AUDIO_TARGET_RATE:
                converted, _ = audioop.ratecv(content, sampwidth, n_channels, framerate, AUDIO_TARGET_RATE, None)
                content = converted
                framerate = AUDIO_TARGET_RATE

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as new_wav:
                new_wav.setnchannels(n_channels)
                new_wav.setsampwidth(sampwidth)
                new_wav.setframerate(framerate)
                new_wav.writeframes(content)
            
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:audio/wav;base64,{encoded}"
            
    except Exception as e:
        print(f"  Error optimizing audio {filepath}: {e}")
        return None

print("Reading source HTML...")
with open(SOURCE_HTML, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Embed & Optimize Images
print("Embedding and optimizing images (JPG 50%, Max 800px)...")
def replace_image_url(match):
    path = match.group(1)
    local_path = path.replace('/', os.sep)
    if os.path.exists(local_path):
        b64 = optimize_image_to_base64(local_path)
        if b64: return f'imageUrl: "{b64}"'
        else: return match.group(0)
    return match.group(0)

content = re.sub(r'imageUrl: "([^"]+)"', replace_image_url, content)

# 2. Embed Background
if os.path.exists("bg.png"):
    print("Embedding bg.png...")
    bg_b64 = optimize_image_to_base64("bg.png")
    if bg_b64:
        content = content.replace("url(bg.png)", f"url({bg_b64})")
        content = content.replace("'bg.png'", f"'{bg_b64}'")

# 3. Embed & Optimize Audios
print(f"Embedding and optimizing audios ({AUDIO_TARGET_RATE}Hz Mono)...")
audio_library = {}
if os.path.exists(AUDIOS_DIR):
    for filename in os.listdir(AUDIOS_DIR):
        if filename.endswith(".wav"):
            full_path = os.path.join(AUDIOS_DIR, filename)
            b64 = optimize_audio_to_base64(full_path)
            if b64:
                audio_library[filename] = b64

audio_lib_json = json.dumps(audio_library) # Compact JSON (no indent)
injection_point = "// --- STORY DATA (Mapping to Extracted PDF Pages) ---"
content = content.replace(injection_point, f"const audioFiles = {audio_lib_json};\n\n{injection_point}")

# 4. Modify Audio Logic
new_line = """
                // WIX ULTRA LITE VERSION
                const filename = lang === 'es' ? `audio${idStr}_es.wav` : `audio${idStr}.wav`;
                const audioSrc = audioFiles[filename];
"""
target_line_part = "const audioSrc = lang === 'es' ? `audios/audio${idStr}_es.wav` : `audios/audio${idStr}.wav`;"
if target_line_part in content:
    content = content.replace(target_line_part, new_line)

print(f"Writing {OUTPUT_HTML}...")
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! Ultra Lite bundle created.")
