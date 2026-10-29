import os
from wa_reader.parser import parse_chat_file, detect_format, participants, Message

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

def test_ios_basic():
    msgs = list(parse_chat_file(os.path.join(FIX, "ios_chat.txt")))
    assert len(msgs) >= 5
    assert msgs[0].author == "Maria Silva"
    assert msgs[0].attachment == "IMG_20240312.jpg"

def test_detect_ios():
    lines = open(os.path.join(FIX, "ios_chat.txt")).read().splitlines()[:10]
    assert detect_format(lines) == "ios"

def test_multiline():
    msgs = list(parse_chat_file(os.path.join(FIX, "ios_chat.txt")))
    # last message should be continuation
    # simple check: some message contains newline
    texts = [m.text for m in msgs]
    assert any("\n" in t for t in texts)

def test_participants():
    msgs = list(parse_chat_file(os.path.join(FIX, "android_24h.txt")))
    assert "Maria Silva" in participants(msgs)
