# Video Summarizer

## What it does

Video Summarizer turns a YouTube video or a recording into a summary, a searchable timestamped transcript and a downloadable PDF. You can type a topic and jump straight to the moment it is discussed in the video.

## Features

- **Two input types:** paste a YouTube link or upload a video or audio file (mp4, mkv, mov, webm, mp3, wav, m4a)
- **English and Hinglish:** English is transcribed with Whisper running locally, Hinglish with Sarvam AI, which translates it to English while transcribing
- **Summary:** long transcripts are split into chunks, each chunk is summarized, and the partial summaries are merged into one final summary
- **Jump to a topic:** type a topic to find where it is discussed, then play the video from that timestamp
- **Timestamped transcript:** every segment with its start time
- **PDF export:** download the summary as a formatted PDF

## Flow

```
YouTube link / file
   -> yt-dlp + pydub: extract audio, convert to WAV, split into 10-minute chunks
   -> Whisper (English) or Sarvam AI (Hinglish): transcribe each chunk into timestamped segments
   -> segment times are shifted by chunk offsets so they match the full video
   -> Groq LLM through LangChain: summarize each chunk, then merge into a final summary
   -> sentence-transformers + ChromaDB: embed ~500-character transcript windows for topic search
   -> ReportLab: export the summary as PDF
```

## Tech stack

| Area | Tools |
|---|---|
| UI | Streamlit |
| Audio | yt-dlp, pydub, ffmpeg |
| Speech to text | OpenAI Whisper (local), Sarvam AI |
| LLM | Groq (openai/gpt-oss-120b) through LangChain |
| Search | sentence-transformers (all-MiniLM-L6-v2), ChromaDB |
| PDF | ReportLab |

## Limitations

- Runs locally. YouTube blocks requests from cloud server IPs, so link downloads are unreliable on free hosting.
- Whisper on a CPU is slow for long videos.
- Hinglish timestamps are accurate to about 25 seconds, because Sarvam processes audio in short pieces.
- The PDF uses a default font, so non-Latin scripts are not supported.
