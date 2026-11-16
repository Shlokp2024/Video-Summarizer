from dotenv import load_dotenv
load_dotenv()

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_llm():
    return init_chat_model("groq:openai/gpt-oss-120b")


def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,  
        chunk_overlap=0,    
    )
    return splitter.split_text(transcript)


def summarize(transcript: str) -> str:
    llm = get_llm()

    map_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert meeting summarizer. Summarize this part of a meeting "
         "transcript into concise bullet points. Capture decisions, action items, "
         "and key topics."),
        ("human", "{text}"),
    ])
    map_chain = map_prompt | llm | StrOutputParser()

    chunks = split_transcript(transcript)

    if len(chunks) == 1:
        return map_chain.invoke({"text": chunks[0]})

    chunk_summaries = map_chain.batch([{"text": c} for c in chunks])
    combined = "\n\n".join(chunk_summaries)

    combine_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert meeting summarizer. Combine these partial summaries into "
         "one final professional meeting summary in bullet points. Merge duplicate "
         "or repeated points into one."),
        ("human", "{text}"),
    ])
    combine_chain = combine_prompt | llm | StrOutputParser()
    return combine_chain.invoke({"text": combined})


def generate_title(transcript: str) -> str:
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Based on the meeting transcript, generate a short professional meeting "
         "title (max 8 words). Only return the title, nothing else."),
        ("human", "{text}"),
    ])
    title_chain = prompt | llm | StrOutputParser()
    return title_chain.invoke({"text": transcript[:2000]})