from dotenv import load_dotenv
load_dotenv()

import html
import os
import streamlit as st

from utils.audio_processor import process_input
from core.transcriber import transcribe_all_with_segments
from core.summarize import summarize, generate_title
from core.moment_search import index_video, find_moments, fmt_time, youtube_link
from core.pdf_export import summary_to_pdf

st.set_page_config(page_title="Video Summarizer", page_icon="🎬", layout="wide")

UPLOAD_DIR = "uploads_tmp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PANEL_HEIGHT = 540

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@600;700&display=swap');

.stApp { background: #f7f8fa; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.8rem; padding-bottom: 1rem; max-width: 1500px; }

.hero-title, .page-title {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    line-height: 1.15;
    color: #111827;
}
.hero-title { font-size: 2.8rem; margin: 1.5rem 0 .6rem; }
.page-title { font-size: 1.7rem; padding-top: .2rem; }
.hero-sub { font-size: 1.05rem; color: #6b7280; margin-bottom: 1rem; }

.chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1rem; }
.chip, .chip.pink, .chip.amber, .chip.teal {
    display: inline-block;
    padding: .15rem .7rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: .85rem;
    background: #e8f0fe;
    color: #1d4ed8;
}

button[kind="primary"], button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {
    background: #2563eb;
    border: 0;
    color: #fff;
    font-weight: 600;
}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover,
[data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
    background: #1d4ed8;
    color: #fff;
}

button[data-baseweb="tab"] { font-weight: 600; }
[data-baseweb="tab-highlight"] { background: #2563eb; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; border-color: #e5e7eb; background: #ffffff; }

[data-testid="stVideo"], [data-testid="stVideo"] iframe, [data-testid="stVideo"] video {
    border-radius: 12px;
}
[data-testid="stVideo"] { border: 1px solid #e5e7eb; }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }
</style>
""",
    unsafe_allow_html=True,
)

DEFAULTS = {
    "ready": False,
    "segments": [],
    "col": None,
    "title": "",
    "summary": "",
    "pdf": b"",
    "source": "",
    "player": None,
    "start": 0,
    "autoplay": False,
    "nonce": 0,
    "results": [],
    "current_q": "",
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def reset():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def on_search():
    query = st.session_state.q_input.strip()
    if query and st.session_state.col is not None:
        st.session_state.results = find_moments(st.session_state.col, query)
        st.session_state.current_q = query


def set_start(sec):
    st.session_state.start = int(sec)
    st.session_state.autoplay = True
    st.session_state.nonce += 1


def show_player():
    options = {"start_time": st.session_state.start, "autoplay": st.session_state.autoplay}
    try:
        st.video(st.session_state.player, key=f"player_{st.session_state.nonce}", **options)
    except TypeError:
        st.video(st.session_state.player, **options)


def chip(text, color=""):
    return f'<span class="chip {color}">{html.escape(text)}</span>'


def process(source, language, player, label):
    try:
        with st.status("Working on your video...", expanded=True) as status:
            st.write("Extracting audio...")
            chunks = process_input(source)

            st.write("Transcribing...")
            segments = transcribe_all_with_segments(chunks, language=language.lower())
            transcript = " ".join(s["text"] for s in segments)

            st.write("Indexing topics...")
            col = index_video(segments)

            st.write("Writing the summary...")
            title = generate_title(transcript)
            summary = summarize(transcript)
            pdf = summary_to_pdf(title, summary, source=label)

            status.update(label="Done", state="complete", expanded=False)
    except Exception as e:
        st.error(f"Could not process this video: {e}")
        return

    st.session_state.update(
        ready=True,
        segments=segments,
        col=col,
        title=title,
        summary=summary,
        pdf=pdf,
        source=label,
        player=player,
        start=0,
        autoplay=False,
        nonce=0,
        results=[],
        current_q="",
    )
    st.rerun()


if not st.session_state.ready:
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            '<div class="hero-title">Video Summarizer</div>'
            '<div class="hero-sub">Turn any video into a summary, then jump straight to the topics you care about.</div>'
            '<div class="chips">'
            + chip("Summary")
            + chip("Jump to any topic", "pink")
            + chip("Timestamped transcript", "teal")
            + chip("PDF export", "amber")
            + "</div>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            language = st.radio(
                "Spoken language",
                ["English", "Hinglish"],
                horizontal=True,
                help="English uses Whisper on your machine. Hinglish uses Sarvam AI and translates to English.",
            )

            tab_url, tab_file = st.tabs(["YouTube link", "Upload a file"])

            with tab_url:
                url = st.text_input(
                    "YouTube link",
                    placeholder="https://www.youtube.com/watch?v=...",
                    label_visibility="collapsed",
                )
                if st.button("Summarize", key="go_url", type="primary", disabled=not url.strip()):
                    process(url.strip(), language, url.strip(), url.strip())

            with tab_file:
                f = st.file_uploader(
                    "Video or audio",
                    type=["mp4", "mkv", "mov", "webm", "mp3", "wav", "m4a"],
                    label_visibility="collapsed",
                )
                if f and st.button("Summarize", key="go_file", type="primary"):
                    path = os.path.join(UPLOAD_DIR, f.name)
                    data = f.getvalue()
                    with open(path, "wb") as out:
                        out.write(data)
                    process(path, language, data, f.name)
    st.stop()

head, action = st.columns([6, 1])
head.markdown('<div class="page-title">Video Summarizer</div>', unsafe_allow_html=True)
action.button("New video", on_click=reset, use_container_width=True)

left, right = st.columns([3, 2], gap="large")

with left:
    show_player()
    duration = fmt_time(st.session_state.segments[-1]["end"]) if st.session_state.segments else "0:00"
    st.markdown(
        chip(f"Playing from {fmt_time(st.session_state.start)}", "teal")
        + " "
        + chip(f"{duration} long", "amber"),
        unsafe_allow_html=True,
    )

with right:
    tab_sum, tab_jump, tab_tx = st.tabs(["Summary", "Jump to a topic", "Transcript"])

    with tab_sum:
        with st.container(height=PANEL_HEIGHT - 60, border=False):
            st.markdown(f"#### {st.session_state.title}")
            st.markdown(st.session_state.summary)
        st.download_button(
            "Download as PDF",
            data=st.session_state.pdf,
            file_name="summary.pdf",
            mime="application/pdf",
        )

    with tab_jump:
        with st.form("jump", border=False):
            st.text_input(
                "Topic",
                key="q_input",
                placeholder="Type a topic, for example: pricing",
                label_visibility="collapsed",
            )
            st.form_submit_button("Find in video", on_click=on_search)

        with st.container(height=PANEL_HEIGHT - 110, border=False):
            if st.session_state.current_q:
                st.markdown(
                    "Best matches for " + chip(st.session_state.current_q, "pink"),
                    unsafe_allow_html=True,
                )
            for i, m in enumerate(st.session_state.results):
                with st.container(border=True):
                    st.markdown(
                        chip(fmt_time(m["start"]), "amber") + " " + html.escape(m["text"][:220]) + "...",
                        unsafe_allow_html=True,
                    )
                    c1, c2 = st.columns(2)
                    c1.button(
                        f"Play from {fmt_time(m['start'])}",
                        key=f"play_{i}",
                        on_click=set_start,
                        args=(m["start"],),
                    )
                    if st.session_state.source.startswith("http"):
                        c2.link_button("Open on YouTube", youtube_link(st.session_state.source, m["start"]))

    with tab_tx:
        with st.container(height=PANEL_HEIGHT, border=False):
            lines = [
                chip(fmt_time(s["start"]), "teal") + " " + html.escape(s["text"])
                for s in st.session_state.segments
            ]
            st.markdown("<br><br>".join(lines), unsafe_allow_html=True)