from dotenv import load_dotenv
load_dotenv()

from utils.audio_processor import process_input
from core.transcriber import transcribe_all_with_segments
from core.summarize import summarize, generate_title
from core.moment_search import index_video, find_moments, fmt_time, youtube_link
from core.pdf_export import summary_to_pdf

source = "https://www.youtube.com/watch?v=Lg-meK5IU8Q"
language = "english"
search_query = "what is the main topic?"


def main():
    chunks = process_input(source)

    segments = transcribe_all_with_segments(chunks, language=language)
    transcript = " ".join(s["text"] for s in segments)

    print("\n=== FIRST 5 SEGMENTS ===")
    for s in segments[:5]:
        print(f"[{fmt_time(s['start'])} - {fmt_time(s['end'])}] {s['text']}")

    title = generate_title(transcript)
    summary = summarize(transcript)
    print("\n=== TITLE ===")
    print(title)
    print("\n=== SUMMARY ===")
    print(summary)

    col = index_video(segments)
    print(f"\n=== MOMENTS FOR: {search_query!r} ===")
    for m in find_moments(col, search_query):
        print(fmt_time(m["start"]), youtube_link(source, m["start"]))
        print("   ", m["text"][:120])

    pdf_bytes = summary_to_pdf(title, summary, source=source)
    with open("summary.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("\nSaved summary.pdf")


if __name__ == "__main__":
    main()