import json
import logging
import chromadb
import httpx
from chromadb.errors import InvalidCollectionException
from config import Config
from utils.helpers import count_tokens
from models.conversation_manager import ConversationManager, Role
from openai import OpenAI
from pathlib import Path
from openai import AsyncOpenAI


class OpenAIClient:
    def __init__(self):
        transport = httpx.HTTPTransport(proxy=Config.PROXY_URL)
        sync_client = httpx.Client(transport=transport)
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            http_client=sync_client
        )
        
        self.model_gpt4o = Config.MODEL_GPT4O
        self.conversation_manager = ConversationManager()
        self.current_complexes = {}
        self.search_cache = {}
        

        self.chroma_client = chromadb.Client()
        try:
            self.knowledge_collection = self._load_or_create_collection("knowledge_embeddings")
            print("Коллекция 'knowledge_embeddings' успешно загружена.")
        except Exception as e:
            logging.error(f"Ошибка при инициализации коллекции: {e}")
            self.knowledge_collection = None
        self.load_knowledge_files()

    def _load_or_create_collection(self, collection_name):
        try:
            return self.chroma_client.get_collection(collection_name)
        except InvalidCollectionException:
            print(f"Коллекция '{collection_name}' не найдена, создаём новую.")
            return self.chroma_client.create_collection(collection_name)

    # def get_vladivostok_time(self):
    #     vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    #     vladivostok_time = datetime.now(vladivostok_tz)
    #     return vladivostok_time.strftime('%Y-%m-%d %H:%M:%S')

    def ask_openai(self, messages, model):
        try:
            chat_completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=200
            )
        except Exception as e:
            print(f"Error communicating with OpenAI: {e}")
            return "Произошла ошибка при обработке запроса.", 0, 0

        response_text = chat_completion.choices[0].message.content.strip()
        input_tokens, output_tokens = count_tokens(messages, response_text)
        print(f"Ответ от {model}: {response_text}")
        print(f"Входных токенов: {input_tokens}, Выходных токенов: {output_tokens}")
        return response_text, input_tokens, output_tokens

    def search_in_vector_db(self, query, complex_names=None):
        try:
            response = self.client.embeddings.create(input=query, model="text-embedding-3-large")
            query_embedding = response.data[0].embedding

            if complex_names:
                results = self.knowledge_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3,
                    where={"complex_name": {"$in": complex_names}}
                )
            else:
                results = self.knowledge_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3
                )

            if results and results["metadatas"]:
                documents = [meta["content"] for meta in results["metadatas"][0] if "content" in meta]
                return "\n".join(documents)
            return "Извините, информация не найдена."
        except Exception as e:
            print(f"Ошибка поиска в векторной базе данных: {e}")
            return "Произошла ошибка при обработке запроса."

    def extract_complex_name(self, text):
        text_lower = text.lower()
        known_complexes = {
            "7ya": ["7я", "жк 7я", "бам"],
            "Futurist1": ["futurist", "футурист", "жк футурист"],
            "Futurist2": ["futurist", "футурист", "жк футурист", "бам"],
            "Futurist3": ["futurist", "футурист", "жк футурист"],
            "Akvatoriya": ["акватория", "чуркин", "жк акватория"],
            "Eco_city": ["эко сити", "жк эко сити", "чуркин", "еко сити"],
            "Kashtanoviy": ["каштановый двор", "жк каштановый двор", "чуркин", "каштановый"],
            "Greenwood": ["greenwood", "жк greenwood", "жк гринвуд", "гринвуд", "нейбута"],
            "Amurskiy": ["amurskiy", "жк амурский", "амурский", "эгершельд"],
            "Andersen": ["andersen", "жк андерсен", "андерсен", "весенняя"],
            "Argument": ["argument", "жк аргумент", "аргумент", "артем"],
            "Ayaks": ["ayaks", "жк аякс", "аякс", "патрокл"],
            "Brusnika": ["brusnika", "жк брусника", "брусника", "сахарный ключ"],
            "CentralPark Dom1": ["centralpark dom1", "premium park", "централ парк", "премиум парк", "3-я рабочая",
                                 "третья рабочая", "рабочей", "третьей рабочей"],
            "CentralPark Dom2": ["centralpark dom2", "premium park", "централ парк", "премиум парк", "3-я рабочая",
                                 "третья рабочая", "рабочей", "третьей рабочей"],
            "Dneprovskiy": ["dneprovskiy", "жк днепровский", "днепровский", "бам"],
            "Dns_city": ["dns city", "днс", "днс сити", "жк днс", "поселок новый"],
            "Edelweiss": ["edelweiss", "жк эдельвес", "эдельвес", "жк едельвес", "едельвес", "чуркин"],
            "Filosofia": ["filosofia", "жк философия", "философия", "голубиная падь", "гоголя"],
            "Flagman": ["flagman", "жк флагман", "флагман", "снеговая падь"],
            "Format": ["format", "жк формат", "формат", "фармат", "зима южная"],
            "Fyord": ["fyord", "жк фьорд", "фьорд", "жк фьёрд", "фьёрд", "вторая речка", "второй речке", "вторяк"],
            "Garmoniya": ["garmoniya", "жк гармония", "гармония", "артем"],
            "Gavan": ["gavan", "жк гавань", "гавань", "чуркин"],
            "Gorizont": ["gorizont", "жк горизонт", "горизонт", "баляева"],
            "Greenhills": ["greenhills", "жк гринхилс", "гринхилс", "зеленый угол", "зелёный угол", "зеленого угла",
                           "зеленка", "зелёнка", "зеленк", "зелёнк"],
            "Istorichesky": ["istorichesky", "жк исторический", "исторический", "снеговая"],
            "Kaleidoscop": ["kaleidoscop", "жк калейдоскоп", "калейдоскоп", "колейдоскоп", "артем"],
            "Kurortniy1": ["kurortniy", "жк курортный", "курортный", "садгород"],
            "Klubniy": ["klubniy", "жк клубный", "клубный", "садгород"],
            "Kvartal_neibuta": ["kvartal_neibuta", "жк квартал найбута", "квартал найбута", "зеленый угол",
                                "зелёный угол", "зеленого угла", "зеленка", "зелёнк", "зеленк"],
            "Lisapark": ["lisapark", "жк лисапарк", "лисапарк", "лиса парк", "баляева"],
            "Meridiany_ulissa": ["мeridiany_ulissa", "жк меридианы", "меридианы", "чуркин"],
            "More": ["more", "жк море", "море", "первая речка", "кунгасный"],
            "Nahodka": ["nahodka", "жк находка", "находка", "спутник"],
            "Nebopark2": ["nebopark", "жк небопарк", "небопарк", "небо парк", "артем"],
            "Novozhilovo": ["novozhilovo", "жк новожилово", "новожилово", "патрокл"],
            "Novyegorizonty": ["klubniy", "жк новые горизонты", "новые горизонты", "горизонты", "первомайский",
                               "первомайском"],
            "Ostrogornyi": ["pobeda", "жк победа", "победа", "вторая речка", "второй речке", "вторяк"],
            "Pribrezhniy": ["pribrezhniy", "жк прибрежный", "прибрежный", "чайк"],
            "Sabaneeva125": ["sabaneeva125", "жк сабанеева", "Сабанеева", "сабанеев"],
            "Sady_makovskogo": ["sady_makovskogo", "жк сады маковского", "сады маковского", "седанк"],
            "Serdce_kvartala": ["serdce_kvartala", "жк сердце квартала", "сердце квартала", "зеленый угол",
                                "зелёный угол", "зеленого угла", "зеленка", "зелёнка", "нейбута", "зеленк", "зелёнк"],
            "Singapur": ["singapur", "жк сингапур", "сингапур", "зар"],
            "Solnechniygorod": ["solnechniygorod", "жк солнечный город", "солнечный город", "артем"],
            "Solyaris": ["solyaris", "жк солярис", "солярис", "салярис", "3-я рабочая",
                                 "третья рабочая", "рабочей", "третьей рабочей", "жигура"],
            "Supreme": ["supreme", "жк суприм", "суприм", "вторая речка", "второй речке", "вторяк"],
            "Tihvinskiy": ["tihvinskiy", "жк тихвинский", "тихвинский", "борисенк"],
            "Vesna4": ["vesna4", "весна", "весен"],
            "Vostochnyi_Dom102-103": ["восточный", "патрокл"],
            "Vostochnyi_Dom108": ["восточный"],
            "Yuzhniy": ["yuzhniy", "жк южный", "южный", "нейбута"],
            "Zaliv": ["zaliv", "жк залив", "залив", "академ"],
            "Zhuravli": ["zhuravli", "жк журавли", "садгород", "журавли"],
            "Zolotaya_dolina": ["zolotaya_dolina", "жк золотая долина", "золотая долина", "трудовое"],
            "Сhaika": ["chaika", "жк чайка", "чайка", "чайк"],
            "Сhernyahovskogo": ["chernyahovskogo", "жк черняховского", "черняховского", "ладыгин", "71 микрорайон"],




        }

        found_complexes = []
        for complex_name, aliases in known_complexes.items():
            if any(alias in text_lower for alias in aliases):
                found_complexes.append(complex_name)
        return found_complexes if found_complexes else None

    def set_current_complex(self, chat_id, complex_names):
        self.current_complexes[chat_id] = complex_names

    def get_current_complex(self, chat_id):
        return self.current_complexes.get(chat_id)

    def create_gpt4o_response(self, question, chat_id):
        self.conversation_manager.initialize_conversation(chat_id)
        # vladivostok_time = self.get_vladivostok_time()
        conversation_history = self.conversation_manager.get_history(chat_id)

        complex_names = self.extract_complex_name(question)

        if complex_names:
            self.set_current_complex(chat_id, complex_names)
        else:
            complex_names = self.get_current_complex(chat_id)

        if not complex_names and ("там" in question.lower() or "что есть" in question.lower()):
            clarification = "Уточните, о каком ЖК идёт речь?"
            self.conversation_manager.add_assistant_message(chat_id, clarification)
            return clarification, 0, 0

        cache_key = str(chat_id)
        vector_db_response = None
        if cache_key in self.search_cache:
            cached = self.search_cache[cache_key]
            if sorted(cached["complex_names"] or []) == sorted(complex_names or []):
                vector_db_response = cached["result"]
                print(f"Использован кэш для chat_id {chat_id} (ЖК: {complex_names})")
            else:
                print(f"Кэш не подошёл: список ЖК изменился для chat_id {chat_id}")

        if vector_db_response is None:
            vector_db_response = self.search_in_vector_db(question, complex_names=complex_names)
            self.search_cache[cache_key] = {
                "complex_names": complex_names,
                "result": vector_db_response
            }
            print(f"Выполнен новый поиск для chat_id {chat_id} (ЖК: {complex_names})")

        time_message_found = False
        # for msg in conversation_history:
        #     if msg['role'] == 'system' and 'Текущее время во Владивостоке' in msg['content']:
        #         msg['content'] = f"Текущее время во Владивостоке: {vladivostok_time}"
        #         time_message_found = True
        #         break
        # if not time_message_found:
        #     self.conversation_manager.add_message(chat_id, "system",
        #                                           f"Текущее время во Владивостоке: {vladivostok_time}")

        result_found = False
        for msg in conversation_history:
            if msg['role'] == 'system' and 'Результат поиска в базе знаний' in msg['content']:
                msg['content'] = f"Результат поиска в базе знаний:\n{vector_db_response}"
                result_found = True
                break
        if not result_found:
            self.conversation_manager.add_message(chat_id, Role.SYSTEM,
                                                  f"Результат поиска в базе знаний:\n{vector_db_response}")

        self.conversation_manager.add_user_message(chat_id, f"Пользователь задал вопрос:\n{question}")
        self.conversation_manager.trim_history(chat_id, max_tokens=Config.MAX_TOKENS)

        gpt4_response, input_tokens, output_tokens = self.ask_openai(
            self.conversation_manager.get_history(chat_id),
            model=self.model_gpt4o
        )

        self.conversation_manager.add_assistant_message(chat_id, gpt4_response)

        print(f"История диалога для chat_id {chat_id}:")
        for msg in self.conversation_manager.get_history(chat_id):
            print(f"{msg['role'].capitalize()}: {msg['content']}")
        print(f"Текущие ЖК: {self.get_current_complex(chat_id)}")

        return gpt4_response, input_tokens, output_tokens

    def load_knowledge_files(self):
        folder_path = Path("knowledge_files")
        for file in folder_path.glob("*.json"):
            self.read_and_embed(str(file), file.stem)

    def read_and_embed(self, file_path, source):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
                complex_name = document_data.get("complex_name", "Unknown")
                document_text = json.dumps(document_data, ensure_ascii=False)
                chunks = self.split_text_into_chunks(document_text)
                for i, chunk in enumerate(chunks):
                    response = self.client.embeddings.create(input=chunk, model="text-embedding-3-large")
                    embedding = response.data[0].embedding
                    self.knowledge_collection.add(
                        embeddings=[embedding],
                        metadatas=[{
                            "source": source,
                            "chunk_index": i,
                            "content": chunk,
                            "complex_name": complex_name
                        }],
                        ids=[f"{source}_chunk_{i}"]
                    )
                    print(f"Добавлен эмбеддинг для {source}, часть {i}, complex_name: {complex_name}")
        except Exception as e:
            print(f"Ошибка при создании эмбеддингов для {file_path}: {e}")

    def split_text_into_chunks(self, text: str, chunk_size: int = 2300) -> list:
        words = text.split()
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]