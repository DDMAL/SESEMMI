from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings

embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.embedding_model,
    google_api_key=settings.llm_api_key,
)
