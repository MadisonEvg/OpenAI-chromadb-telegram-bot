import json
import logging
import chromadb
from datetime import datetime
from chromadb.errors import ChromaError
from config import Config
from pathlib import Path
from models.conversation_manager import ConversationManager, Role
from sentence_transformers import SentenceTransformer
from logger_config import logger
from utils.db_parser import parse_json_files, parse_filter_text
from models.query import get_filtered_apartments, get_complex_info_by_names
import json
import asyncio
import pickle


class ChromaDbClient:
    def __init__(self, openai_client):
        self.client = openai_client
        self.current_complexes = {}
        self.chroma_client = chromadb.Client()
        try:
            self.knowledge_collection = self._load_or_create_collection("knowledge_embeddings")
            logger.info("Коллекция 'knowledge_embeddings' успешно загружена.")
        except Exception as e:
            logging.error(f"Ошибка при инициализации коллекции: {e}")
            self.knowledge_collection = None
        # self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.load_knowledge_files()
        print('--end--')

    def _load_or_create_collection(self, collection_name):
        try:
            return self.chroma_client.get_collection(collection_name)
        except ChromaError:
            logger.error(f"Коллекция '{collection_name}' не найдена, создаём новую.")
            return self.chroma_client.create_collection(collection_name)
        except Exception as e:
            logger.error(f"Ошибка с коллекцией {e}")

    async def search_in_vector_db(self, query, city=None):
        try:
            # logger.info(f"----------vectorDB query: {query}")
            # query_embedding = self.embedding_model.encode(query).tolist()
            
            # response = await self.client.embeddings.create(input=query, model="text-embedding-3-large")
            response = await self.client.embeddings.create(input=query, model="text-embedding-3-large")
            query_embedding = response.data[0].embedding

            if city:
                results = self.knowledge_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=100,
                    where={"city": city}
                )
            else:
                results = self.knowledge_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=100
                )
            
            # Потом фильтруем сами
            final_results = []

            for doc, distance in zip(results["documents"][0], results["distances"][0]):
                print(doc, distance)
                if distance < 0.2:  # например, оставить только очень похожие
                    final_results.append(doc)
        
            logger.info("----------vectorDB result:")
            complex_names = []
            if results and results["metadatas"]:
                # documents = []
                for meta, distance in zip(results["metadatas"][0], results["distances"][0]):
                    # if "content" in meta and distance < 1.45:
                    data = json.loads(meta["content"])
                        # new_data = {}
                        # new_data['complex_name'] = data.get("complex_name")
                    complex_names.append(data.get("complex_name"))
                    print(data.get("complex_name"), distance)
                        # new_data['area'] = data.get("area")
                        # new_data['general_texts'] = data.get("general_texts")
                        # new_json_str = json.dumps(new_data, ensure_ascii=False)
                        # documents.append(new_json_str)
                documents = [meta["content"] for meta in results["metadatas"][0][0:3] if "content" in meta]
                # [complex_name.strip() for complex_name in complex_names]
                # [n.strip() for n in value.split(",")]
                return "Результат поиска в базе знаний запроса:/n"+"\n".join(documents), complex_names[0:3]
            return "Извините, информация не найдена."
        except Exception as e:
            logger.error(f"Ошибка поиска в векторной базе данных: {e}")
            return "Произошла ошибка при обработке запроса."
    
    def load_knowledge_files(self):
        folder_path = Path("knowledge_files")
        for file in folder_path.glob("*.json"):
            self.read_and_embed(str(file), file.stem)

    def read_and_embed(self, file_path, source):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
                complex_name = document_data.get("complex_name", "Unknown")
                city = document_data.get("city", "Unknown")
                document_text = json.dumps(document_data, ensure_ascii=False)
                chunks = self.split_text_into_chunks(document_text)
                for i, chunk in enumerate(chunks):
                    # CREATE AND DUMP TO FILE
                    # response = self.client.embeddings.create(input=chunk, model="text-embedding-3-large")
                    # response = asyncio.run(self.client.embeddings.create(input=chunk, model="text-embedding-3-large"))
                    # embedding = response.data[0].embedding
                    # with open(f"saved_embeddings/{source}.pkl", "wb") as f:
                    #     pickle.dump(embedding, f)
                        
                    embedding = None
                    with open(f"saved_embeddings/{source}.pkl", "rb") as f:
                        embedding = pickle.load(f)
                    
                    # if i > 0:
                    #     logger.info(i)
                    # embedding = self.embedding_model.encode(chunk).tolist()
                    self.knowledge_collection.add(
                        embeddings=[embedding],
                        metadatas=[{
                            "source": source,
                            "chunk_index": i,
                            "content": chunk,
                            "complex_name": complex_name,
                            "city": city
                        }],
                        ids=[f"{source}_chunk_{i}"]
                    )
                    logger.info(f"Добавлен эмбеддинг для {source}, часть {i}, complex_name: {complex_name}")
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддингов для {file_path}: {e}")

    def split_text_into_chunks(self, text: str, chunk_size: int = 2300) -> list:
        words = text.split()
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]