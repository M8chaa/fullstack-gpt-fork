from langchain.storage import LocalFileStore
import streamlit as st
import subprocess
import math
from pydub import AudioSegment
import glob
import openai
import os
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import StrOutputParser
from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import CacheBackedEmbeddings, OpenAIEmbeddings

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

llm = ChatOpenAI(
    temperature=0.1,
)

has_transcript = os.path.exists("./.cache/podcast.txt")

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=800,
    chunk_overlap=100,
)

def embed_file(file_path):
    st.write(f"Loading and embedding file from path: {file_path}")
    try:
        cache_dir = LocalFileStore(f"./.cache/embeddings/{file_path}")
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=800,
            chunk_overlap=100,
        )
        loader = TextLoader(file_path)
        docs = loader.load_and_split(text_splitter=splitter)
        st.write(f"Number of documents loaded and split: {len(docs)}")
        if len(docs) == 0:
            st.write("No documents were loaded. Please check the file content.")
            return None
        embeddings = OpenAIEmbeddings()
        cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embeddings, cache_dir)
        vectorstore = FAISS.from_documents(docs, cached_embeddings)
        retriever = vectorstore.as_retriever()
        return retriever
    except Exception as e:
        st.write(f"Error loading and embedding file: {e}")
        raise

def transcribe_chunks(chunk_folder, destination):
    if has_transcript:
        st.write("Transcript already exists.")
        return
    st.write(f"Starting transcription of audio chunks from folder: {chunk_folder}")
    files = glob.glob(f"{chunk_folder}/*.mp3")
    files.sort()
    st.write(f"Found {len(files)} audio chunks for transcription.")
    for file in files:
        try:
            with open(file, "rb") as audio_file:
                st.write(f"Transcribing file: {file}")
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
                with open(destination, "a") as text_file:
                    text_file.write(transcript.text)
        except Exception as e:
            st.write(f"Error transcribing file {file}: {e}")
    st.write(f"Transcription completed. Transcript saved at {destination}")

def extract_audio_from_video(video_path):
    if has_transcript:
        st.write("Transcript already exists.")
        return
    audio_path = video_path.replace("mp4", "mp3")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        audio_path,
    ]
    try:
        st.write(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            st.write(f"Error in ffmpeg: {result.stderr}")
        else:
            st.write(f"ffmpeg output: {result.stdout}")
    except FileNotFoundError as e:
        st.write(f"ffmpeg not found: {e}")
    except Exception as e:
        st.write(f"Error running ffmpeg: {e}")
    return audio_path

def cut_audio_in_chunks(audio_path, chunk_size, chunks_folder):
    if has_transcript:
        st.write("Transcript already exists.")
        return
    st.write(f"Checking if audio file exists at {audio_path}")
    if not os.path.exists(audio_path):
        st.write(f"Audio file not found at {audio_path}")
        return
    st.write(f"Audio file found at {audio_path}")
    try:
        track = AudioSegment.from_mp3(audio_path)
        chunk_len = chunk_size * 60 * 1000
        chunks = math.ceil(len(track) / chunk_len)
        os.makedirs(chunks_folder, exist_ok=True)
        for i in range(chunks):
            start_time = i * chunk_len
            end_time = (i + 1) * chunk_len
            chunk = track[start_time:end_time]
            chunk.export(
                f"./{chunks_folder}/chunk_{i}.mp3",
                format="mp3",
            )
        st.write(f"Audio cut into {chunks} chunks, saved in {chunks_folder}")
    except Exception as e:
        st.write(f"Error cutting audio into chunks: {e}")

st.set_page_config(
    page_title="MeetingAI",
    page_icon="💼",
)

st.markdown(
    """
# MeetingAI
            
Welcome to MeetingGPT, upload a video and I will give you a transcript, a summary and a chat bot to ask any questions about it.

Get started by uploading a video file in the sidebar.
"""
)

with st.sidebar:
    video = st.file_uploader(
        "Video",
        type=["mp4", "avi", "mkv", "mov"],
    )

if video:
    chunks_folder = "./.cache/chunks"
    with st.status("Loading video...") as status:
        video_content = video.read()
        video_path = f"./.cache/{video.name}"
        audio_path = video_path.replace("mp4", "mp3")
        transcript_path = video_path.replace("mp4", "txt")
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        with open(video_path, "wb") as f:
            f.write(video_content)
        status.update(label="Extracting audio...")
        audio_path = extract_audio_from_video(video_path)
        status.update(label="Cutting audio segments...")
        cut_audio_in_chunks(audio_path, 10, chunks_folder)
        status.update(label="Transcribing audio...")
        transcribe_chunks(chunks_folder, transcript_path)

    transcript_tab, summary_tab, qa_tab = st.tabs(
        [
            "Transcript",
            "Summary",
            "Q&A",
        ]
    )

    with transcript_tab:
        if os.path.exists(transcript_path):
            with open(transcript_path, "r") as file:
                st.write(file.read())
        else:
            st.write("Transcript not found.")

    with summary_tab:
        start = st.button("Generate summary")
        if start:
            if os.path.exists(transcript_path):
                loader = TextLoader(transcript_path)
                docs = loader.load_and_split(text_splitter=splitter)
                st.write(f"Number of documents loaded and split: {len(docs)}")
                if len(docs) == 0:
                    st.write("No documents were loaded. Please check the file content.")
                else:
                    first_summary_prompt = ChatPromptTemplate.from_template(
                        """
                        Write a concise summary of the following:
                        "{text}"
                        CONCISE SUMMARY:                
                    """
                    )
                    first_summary_chain = first_summary_prompt | llm | StrOutputParser()
                    summary = first_summary_chain.invoke(
                        {"text": docs[0].page_content},
                    )
                    refine_prompt = ChatPromptTemplate.from_template(
                        """
                        Your job is to produce a final summary.
                        We have provided an existing summary up to a certain point: {existing_summary}
                        We have the opportunity to refine the existing summary (only if needed) with some more context below.
                        ------------
                        {context}
                        ------------
                        Given the new context, refine the original summary.
                        If the context isn't useful, RETURN the original summary.
                        """
                    )
                    refine_chain = refine_prompt | llm | StrOutputParser()
                    with st.status("Summarizing...") as status:
                        for i, doc in enumerate(docs[1:]):
                            status.update(label=f"Processing document {i+1}/{len(docs)-1} ")
                            summary = refine_chain.invoke(
                                {
                                    "existing_summary": summary,
                                    "context": doc.page_content,
                                }
                            )
                            st.write(summary)
                    st.write(summary)
            else:
                st.write("Transcript not found, please transcribe first.")

    with qa_tab:
        if os.path.exists(transcript_path):
            retriever = embed_file(transcript_path)
            if retriever:
                docs = retriever.invoke("do they talk about marcus aurelius?")
                st.write(docs)
        else:
            st.write("Transcript not found.")
