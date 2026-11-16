import chromadb
from chromadb.utils import embedding_functions

_client = chromadb.EphemeralClient()
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
COLLECTION = "current_video"


def fmt_time(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def youtube_link(url: str, sec: float) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={int(sec)}s"


def build_windows(segments: list, max_chars: int = 500) -> list:
    windows, cur = [], None
    for s in segments:
        if cur is None:
            cur = {"start": s["start"], "end": s["end"], "text": s["text"]}
        else:
            cur["text"] += " " + s["text"]
            cur["end"] = s["end"]
        if len(cur["text"]) >= max_chars:
            windows.append(cur)
            cur = None
    if cur:
        windows.append(cur)
    return windows


def index_video(segments: list):
    try:
        _client.delete_collection(COLLECTION)
    except Exception:
        pass

    col = _client.create_collection(COLLECTION, embedding_function=_ef)
    windows = build_windows(segments)
    col.add(
        ids=[str(i) for i in range(len(windows))],
        documents=[w["text"] for w in windows],
        metadatas=[{"start": w["start"], "end": w["end"]} for w in windows],
    )
    return col


def find_moments(col, query: str, k: int = 3) -> list:
    res = col.query(query_texts=[query], n_results=k)
    moments = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        moments.append({"start": meta["start"], "end": meta["end"], "text": doc})
    return sorted(moments, key=lambda m: m["start"])