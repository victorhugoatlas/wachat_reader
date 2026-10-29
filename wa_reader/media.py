import mimetypes, urllib.parse, base64, os

KIND_MAP = {
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image",
    ".webp": "sticker", ".mp4": "video", ".mov": "video",
    ".3gp": "video", ".webm": "video",
    ".opus": "audio", ".m4a": "audio", ".mp3": "audio",
    ".ogg": "audio", ".aac": "audio", ".wav": "audio",
}

def media_kind(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if filename.startswith("STK-") and ext == ".webp":
        return "sticker"
    return KIND_MAP.get(ext, "doc")

def media_mime(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    corrections = {
        ".opus": "audio/ogg",
        ".m4a": "audio/mp4",
        ".webp": "image/webp",
        ".mov": "video/quicktime",
    }
    if ext in corrections:
        return corrections[ext]
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"

def converter_base64(caminho: str) -> str:
    mime = media_mime(os.path.basename(caminho))
    with open(caminho, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"

def caminho_relativo(pasta_chat: str, arquivo: str, pasta_html: str) -> str:
    base = os.path.dirname(pasta_chat) if os.path.basename(pasta_chat) else pasta_chat
    rel = os.path.relpath(os.path.join(pasta_chat, arquivo), pasta_html)
    rel = rel.replace("\\", "/")
    return urllib.parse.quote(rel, safe="/")
