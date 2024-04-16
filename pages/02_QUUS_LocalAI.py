from langchain.prompts import ChatPromptTemplate
from langchain.document_loaders import UnstructuredFileLoader
from langchain.embeddings import CacheBackedEmbeddings, OllamaEmbeddings, OpenAIEmbeddings
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.storage import LocalFileStore
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain.vectorstores.faiss import FAISS
from langchain.chat_models import ChatOllama
from langchain.callbacks.base import BaseCallbackHandler
import streamlit as st
from langserve import RemoteRunnable
from langchain_core.runnables.schema import StreamEvent
import os

st.set_page_config(
    page_title="쿠스AI",
    page_icon="🔒",
)

openaikey = st.secrets["OPENAI_API_KEY"]
ip = st.secrets["Langserve_endpoint"]
LANGSERVE_ENDPOINT = f"http://{ip}/chat/c/N4XyA"

class ChatCallbackHandler(BaseCallbackHandler):
    message = ""

    def on_llm_start(self, *args, **kwargs):
        self.message_box = st.empty()

    def on_llm_end(self, *args, **kwargs):
        save_message(self.message, "ai")

    def on_llm_new_token(self, token, *args, **kwargs):
        self.message += token
        self.message_box.markdown(self.message)


# llm = ChatOllama(
#     model="mistral:latest",
#     temperature=0.1,
#     streaming=True,
#     callbacks=[
#         ChatCallbackHandler(),
#     ],
# )

llm = RemoteRunnable(LANGSERVE_ENDPOINT)


# @st.cache_data(show_spinner="Embedding file...")
# def embed_file(file):
#     file_content = file.read()
#     file_path = f"./.cache/private_files/{file.name}"
#     with open(file_path, "wb") as f:
#         f.write(file_content)
#     cache_dir = LocalFileStore(f"./.cache/private_embeddings/{file.name}")
#     splitter = CharacterTextSplitter.from_tiktoken_encoder(
#         separator="\n",
#         chunk_size=600,
#         chunk_overlap=100,
#     )
#     loader = UnstructuredFileLoader(file_path)
#     docs = loader.load_and_split(text_splitter=splitter)
#     embeddings = OllamaEmbeddings(model="mistral:latest")
#     cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embeddings, cache_dir)
#     vectorstore = FAISS.from_documents(docs, cached_embeddings)
#     retriever = vectorstore.as_retriever()
#     return retriever


@st.cache_data(show_spinner="Embedding file...")
def embed_file(file):
    file_content = file.read()
    file_path = f"./.cache/private_files/{file.name}"
    os.makedirs(file_path, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(file_content)
    cache_dir = LocalFileStore(f"./.cache/private_embeddings/{file.name}")
    os.makedirs(cache_dir.path, exist_ok=True)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "(?<=\. )", " ", ""],
        length_function=len,
    )
    loader = UnstructuredFileLoader(file_path)
    docs = loader.load_and_split(text_splitter=splitter)
    embeddings = OpenAIEmbeddings()
    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embeddings, cache_dir)
    vectorstore = FAISS.from_documents(docs, cached_embeddings)
    retriever = vectorstore.as_retriever()
    return retriever


def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})


def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)


def paint_history():
    for message in st.session_state["messages"]:
        send_message(
            message["message"],
            message["role"],
            save=False,
        )


def format_docs(docs):
    return "\n\n".join(document.page_content for document in docs)


prompt = ChatPromptTemplate.from_template(
    """Answer the question using ONLY the following context and not your training data. If you don't know the answer just say you don't know. DON'T make anything up.
    
    Context: {context}
    Question:{question}
    """
)


st.title("쿠스AI")

st.markdown(
    """
Welcome!
            
Use this chatbot to ask questions to an AI about your files!

Upload your files on the sidebar.
"""
)

with st.sidebar:
    file = st.file_uploader(
        "Upload a .txt .pdf or .docx file",
        type=["pdf", "txt", "docx"],
    )

if file:
    retriever = embed_file(file)
    send_message("I'm ready! Ask away!", "ai", save=False)
    paint_history()
    message = st.chat_input("Ask anything about your file...")
    if message:
        send_message(message, "human")
        chain = (
            {
                "context": retriever | RunnableLambda(format_docs),
                "question": RunnablePassthrough(),
            }
            | prompt
            | llm
        )
        with st.chat_message("ai"):
            chain.invoke(message)


else:
    st.session_state["messages"] = []
