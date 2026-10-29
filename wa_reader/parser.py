from __future__ import annotations
import re, os, unicodedata, logging
from datetime import datetime
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)

INVIS = re.compile(r"[\u200e\u200f\u202a-\u202e\ufeff]+")

PATTERNS = {
    "ios": re.compile(
        r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}),\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s+(.*)$"
    ),
    "android_24h": re.compile(
        r"^(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s+-\s+(.*)$"
    ),
    "android_12h": re.compile(
        r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),\s+(\d{1,2}):(\d{2})\s+([AaPp])[a-z.]*\s*([Mm])[a-z.]*\s+-\s+(.*)$"
    ),
    "android_2digitos": re.compile(
        r"^(\d{1,2})/(\d{1,2})/(\d{2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s+-\s+(.*)$"
    ),
}

EDITED_SUFFIXES = ("<mensagem editada>", "<this message was edited>", "mensagem editada", "this message was edited")
DELETED_PHRASES = ("você apagou esta mensagem", "esta mensagem foi apagada", "you deleted this message", "this message was deleted")
MEDIA_OMITTED = ("<mídia oculta>", "<media omitted>", "<multimedia omitido>", "imagem ocultada")


@dataclass
class Message:
    dt: datetime
    author: str | None
    text: str
    attachment: str | None
    kind: str  # text, system, media_omitted, deleted
    edited: bool = False


def _clean_line(line: str) -> str:
    return INVIS.sub("", line).rstrip()


def _parse_date(day: int, month: int, year: int) -> datetime:
    # assume dd/mm; if ambiguous handled by caller
    if year < 100:
        year += 2000
    return datetime(year, month, day)


def _disambiguate(d1: int, d2: int) -> tuple[int, int]:
    # if first > 12 => d1 is day, d2 is month; if second > 12 => d2 is day, d1 is month; else dd/mm
    if d1 > 12:
        return d1, d2
    if d2 > 12:
        return d2, d1
    return d1, d2  # default dd/mm


def detect_format(lines: list[str]) -> str:
    best = ("", 0)
    counts = {}
    for name, pat in PATTERNS.items():
        counts[name] = sum(1 for ln in lines if pat.match(_clean_line(ln)))
    best_name = max(counts, key=counts.get)
    return best_name if counts[best_name] > 0 else "ios"


def parse_chat_file(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        lines_raw = f.read().splitlines()
    if not lines_raw:
        return
    cleaned = [_clean_line(ln) for ln in lines_raw]
    # detect
    first = [ln for ln in cleaned if ln.strip()][:50]
    fmt = detect_format(first)
    pat = PATTERNS[fmt]
    messages: list[Message] = []
    current_text = None
    for ln in cleaned:
        ln = ln.strip()
        if not ln:
            continue
        m = pat.match(ln)
        if m:
            if current_text is not None:
                # finalize previous
                pass  # handled below
            # parse new message
            if fmt == "ios":
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                day, month = _disambiguate(d, mo)
                dt = _parse_date(day, month, y)
                h, mi = int(m.group(4)), int(m.group(5))
                sec = int(m.group(6) or 0)
                rest = m.group(7)
                dt = dt.replace(hour=h, minute=mi, second=sec)
            elif fmt in ("android_24h", "android_12h", "android_2digitos"):
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                # 12h uses AM/PM; for datetime, PM adds 12 if hour <12? Actually regex doesn't capture AM/PM group in time directly for datetime construction.
                # For simplicity: if fmt==android_12h, check if AM/PM group (group 6?) indicates PM.
                # Actually for android_12h regex groups: 1=d,2=m,3=y,4=h,5=mi,6=AM/PM marker (P),7=AM/PM marker (M?) No, my regex is wrong for group count.
                # Instead, I'll use a simpler approach: parse manually for 12h by inspecting rest string? No.
                # Given time, I'll just handle 12h by checking original match groups carefully.
                # Reconstructing groups: for android_12h regex: (\d{1,2})/(\d{1,2})/(\d{2,4}),(\d{1,2}):(\d{2})\s+([AaPp])[a-z.]*\s*([Mm])[a-z.]*\s+-\s+(.*)
                # So group 4=hour, 5=min, rest=author:text.
                # Need AM/PM: group 6 and 7 are letters; if group 6 == 'P' or group 7 == 'P' (but my regex has ([AaPp]) then ([Mm]) ... group 6 = first letter, group 7 = M? Hmm.
                # Actually: ([AaPp]) catches P or A, ([Mm]) catches M. So group 6 = A/P, group 7 = M. Not direct PM indicator because A vs P is in group6.
                # To know PM: check if group6.upper() == 'P' -> PM (add 12 if h<12).
                day, month = _disambiguate(d, mo)
                dt = _parse_date(day, month, y)
                h = int(m.group(4)); mi = int(m.group(5))
                is_pm = m.group(6).upper() == 'P'
                if is_pm and h < 12: h += 12
                dt = dt.replace(hour=h, minute=mi)
            else:
                # should not reach
                pass
            rest = ln.split("] ", 1)[1] if fmt == "ios" else ln.split(" - ", 1)[1]
            # Actually for android patterns group 7 is rest? Let's count properly.
            # ios: 1=d,2=m,3=y,4=h,5=mi,6=sec,7=rest => rest=7
            # android_24h: 1=d,2=m,3=y,4=h,5=mi,6=sec,7=rest => rest=7 but sec optional; group6 could be sec or rest depending. Actually regex has (?::(\d{2}))? before \s+-\s+, so group6 is sec, group7 is rest.
            # android_12h: 1=d,2=m,3=y,4=h,5=mi,6=AP_letter,7=M_letter? Wait regex has ([AaPp])[a-z.]*\s*([Mm])[a-z.]*. Groups: 1=d,2=m,3=y,4=h,5=mi,6=A/P,7=M,8=rest.
            # android_2digitos: 1=d,2=m,3=y,4=h,5=mi,6=sec,7=rest.
            rest = m.group(8) if fmt == "android_12h" else m.group(7)
            # split author/text
            if ": " in rest:
                author, text = rest.split(": ", 1)
            else:
                author = None
                text = rest
            # system check: if no colon separator and text starts with lowercase or common system phrases, or if rest has no colon at all -> system? Actually task says no author -> system. If rest has no ": " split => author None.
            # Deleted / edited / media omitted processing on text
            edited = False
            kind = "text"
            attachment = None
            # check deleted
            txt_lower = text.lower()
            for p in DELETED_PHRASES:
                if p in txt_lower:
                    kind = "deleted"
                    text = ""
                    break
            if kind != "deleted":
                # edited
                edited_lower = text.lower()
                for s in EDITED_SUFFIXES:
                    if s in edited_lower or s.lower() in edited_lower:
                        edited = True
                        text = re.sub(re.escape(s) if False else s, "", text, flags=re.IGNORECASE)
                        text = text.replace("<Mensagem editada>", "").replace("<This message was edited>", "").strip()
                        text = re.sub(r"\s+", " ", text).strip()
                        break
                # media omitted
                for o in MEDIA_OMITTED:
                    if o.lower() in txt_lower:
                        kind = "media_omitted"
                        text = ""
                        break
            # attachment parsing
            if kind not in ("media_omitted", "deleted"):
                # iOS attached: <anexado: ARQ>
                ar = re.search(r"<anexado:\s*([^>]+)>", text, re.IGNORECASE)
                if ar:
                    attachment = ar.group(1).strip()
                    text = re.sub(r"<anexado:\s*[^>]+>", "", text, flags=re.IGNORECASE).strip()
                # Android attached patterns
                if not attachment:
                    # ARQ (arquivo anexado) / (file attached) / (archivo adjunto)
                    ar = re.search(r"(.+?)\s+\((arquivo anexado|file attached|archivo adjunto)\)", text, re.IGNORECASE)
                    if ar:
                        attachment = ar.group(1).strip()
                        text = re.sub(r"\s*\((arquivo anexado|file attached|archivo adjunto)\)", "", text, flags=re.IGNORECASE).strip()
            # remove edited markers cleanly
            for marker in ("<mensagem editada>", "<this message was edited>"):
                text = text.replace(marker, "").strip()
            current_text = text  # for continuation
            messages.append(Message(dt=dt, author=author, text=text or "", attachment=attachment, kind=kind, edited=edited))
            # if system (author is None) keep going
            # For continuation: if next line doesn't match, concatenate to previous text
        else:
            # continuation line
            if messages and messages[-1].kind not in ("media_omitted", "deleted"):
                messages[-1].text += "\n" + ln
    return messages


def participants(messages: list[Message]) -> list[str]:
    seen = []
    for m in messages:
        if m.author and m.author not in seen:
            seen.append(m.author)
    return seen
