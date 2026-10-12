#!/usr/bin/env python3
"""Code-only AI ouija board.

Press SPACE to start talking, press SPACE again to stop. Whisper turns your
voice into text, an LLM answers as a spirit, and the board flashes the reply
one letter at a time.

Run:      python ouija.py            (voice)
          python ouija.py --typed    (type questions in the terminal, no mic)
Install:  pip install pygame numpy sounddevice faster-whisper anthropic
Optional: export ANTHROPIC_API_KEY=...   (without it, the spirit gives canned answers)
"""
import math
import os
import queue
import random
import re
import sys
import threading
import time

import numpy as np
import pygame
import difflib

TYPED = "--typed" in sys.argv
SAMPLE_RATE = 16000
LLM_MODEL = "claude-haiku-4-5-20251001"
SYSTEM_PROMPT = (
    "You are a spirit speaking through an ouija board. Reply in one to four words, "
    "uppercase letters only, no punctuation. You may answer YES, NO or GOODBYE. "
    "Be cryptic, brief and eerie. Never explain yourself."
)
CANNED = ["YES", "NO", "MAYBE", "ASK AGAIN", "BEWARE", "GOODBYE"]
WORDS = ("YES", "NO", "GOODBYE")
FAQ = {
    ("10 years from now will i be happy", "ten years from now will i be happy", "will i be happy in 10 years"): "MOSTLY YES",
    ("will i get a job",): "SOON",
    ("tell me something about the afterlife",): "NOT EMPTY",
    ("will my parents see me succeed",): "THEY WILL SEE",
    ("who are you",): "WE ARE MANY",
    ("do you enjoy being dead",): "QUIET HERE",
    ("are you there",): "HERE",
    ("how did you die",): "I FORGET",
    ("am i in danger",): "NO",
    ("what should i invest in in the next 10 years", "what should i invest in in the next ten years"): "PEOPLE",
    ("am i gonna get married", "am i going to get married", "will i get married"): "YES",
    ("what do you like to eat",): "SALT",
    ("what makes you laugh",): "YOU",
    ("are you happy",): "SOMETIMES",
    ("how will i die", "when will i die", "how when will i die"): "NOT TODAY",
    ("whos going to win the superbowl", "who is going to win the super bowl", "who will win the superbowl"): "RED",
}
FAQ_LOOKUP = {q: a for qs, a in FAQ.items() for q in qs}


def faq_answer(question):
    q = re.sub(r"[^a-z0-9 ]", "", question.lower()).strip()
    match = difflib.get_close_matches(q, FAQ_LOOKUP, n=1, cutoff=0.7)
    return FAQ_LOOKUP[match[0]] if match else None

# board layout (later: the same keys map to plotter X/Y)
def build_layout():
    pos = {}

    def arc(chars, y0):
        for i, c in enumerate(chars):
            t = i / (len(chars) - 1)
            pos[c] = (150 + 800 * t, y0 - 80 * math.sin(math.pi * t))

    arc("ABCDEFGHIJKLM", 340)
    arc("NOPQRSTUVWXYZ", 470)
    for i, c in enumerate("1234567890"):
        pos[c] = (200 + i * 78, 580)
    pos["YES"], pos["NO"], pos["GOODBYE"] = (200, 110), (900, 110), (550, 660)
    return pos


LAYOUT = build_layout()


# shared state
class State:
    status = "loading..."
    heard = ""
    lit = None  # key currently lit


S = State()
jobs = queue.Queue()
whisper = None
client = None


# pipeline steps
def transcribe(audio):
    segments, _ = whisper.transcribe(audio, language="en")
    return " ".join(s.text for s in segments).strip()


def ask_spirit(question):
    hardcoded = faq_answer(question)
    if hardcoded:
        return hardcoded

    global client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return random.choice(CANNED)
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    msg = client.messages.create(
        model=LLM_MODEL, max_tokens=40, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    return msg.content[0].text


def clean(text):
    text = re.sub(r"[^A-Z0-9 ]", "", text.upper())
    return re.sub(r"\s+", " ", text).strip() or "NO"


def move_to(key):
    """Light up a key. On the real board this becomes: send G-code to the plotter."""
    S.lit = key


def spell(text):
    time.sleep(1.5)
    if text in WORDS:
        move_to(text)
        time.sleep(2.5)
        move_to(None)
        return
    for ch in text:
        if ch == " ":
            time.sleep(0.8)
            continue
        move_to(ch)
        time.sleep(random.uniform(0.8, 1.2))
        move_to(None)
        time.sleep(random.uniform(0.3, 0.6))


def worker():
    global whisper
    if not TYPED:
        from faster_whisper import WhisperModel
        whisper = WhisperModel("base.en", compute_type="int8")
    S.status = "type a question in the terminal" if TYPED else "press SPACE and ask"
    while True:
        job = jobs.get()
        try:
            S.status = "listening to the other side..."
            question = job if isinstance(job, str) else transcribe(job)
            S.heard = question
            if not question:
                S.status = "nothing heard, try again"
                continue
            reply = clean(ask_spirit(question))
            S.status = "the spirit speaks..."
            spell(reply)
        except Exception as e:  # keep the board alive if the network or mic hiccups
            S.heard = f"error: {e}"
        S.status = "type a question in the terminal" if TYPED else "press SPACE and ask"


def typed_input():
    while True:
        jobs.put(input("ask the spirit> "))


# recording
chunks, stream = [], None


def start_recording():
    global stream
    import sounddevice as sd
    chunks.clear()
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            callback=lambda d, f, t, s: chunks.append(d.copy()))
    stream.start()
    S.status = "recording... press SPACE to stop"


def stop_recording():
    global stream
    stream.stop()
    stream.close()
    stream = None
    if not chunks:
        return
    audio = np.concatenate(chunks)[:, 0]
    if len(audio) > SAMPLE_RATE // 2:  # ignore clips under half a second
        jobs.put(audio)


# display
def draw(screen, font, small):
    screen.fill((20, 18, 26))
    for key, (x, y) in LAYOUT.items():
        lit = key == S.lit
        color = (255, 210, 110) if lit else (110, 100, 130)
        img = font.render(key, True, color)
        screen.blit(img, img.get_rect(center=(x, y)))
    for text, y, color in ((f"you: {S.heard}", 30, (160, 150, 180)),
                           (S.status, 690, (120, 180, 170))):
        img = small.render(text, True, color)
        screen.blit(img, img.get_rect(center=(550, y)))
    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((1100, 720))
    pygame.display.set_caption("ouija")
    font = pygame.font.SysFont("georgia", 44)
    small = pygame.font.SysFont("helvetica", 24)
    threading.Thread(target=worker, daemon=True).start()
    if TYPED:
        threading.Thread(target=typed_input, daemon=True).start()
    clock = pygame.time.Clock()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                os._exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE and not TYPED:
                if stream is not None:
                    stop_recording()
                elif S.status.startswith("press SPACE"):
                    start_recording()
        draw(screen, font, small)
        clock.tick(60)


if __name__ == "__main__":
    main()