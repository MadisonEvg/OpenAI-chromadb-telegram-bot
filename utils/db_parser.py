import os
import json
import re
from models.models import ResidentialComplex, Apartment, Session
from logger_config import logger

def clean_text(text):
    text = text.replace('\u00A0', ' ')  # nbsp
    text = text.replace('\u202F', ' ')  # narrow nbsp
    text = text.replace('\u2060', '')   # word joiner
    text = text.replace('\u200e', '')   # ltr mark
    
    text = re.sub(r'[^\x20-\x7E]', '', text)  # Убираем все не-ASCII символы (кроме пробела)
    
    return text

def extract_price(price_str):
    match = re.search(r'([\d\s]+)', clean_text(price_str))
    if match:
        try:
            return int(match.group(1).replace(" ", "").replace("\xa0", ""))
        except ValueError as e:
            return None
    return None

def extract_square_meters(apartment_type):
    match = re.search(r'(\d+)\s*м²', apartment_type)
    return float(match.group(1)) if match else None

def extract_rooms(apartment_type):
    lower = apartment_type.lower().replace(" ", "")
    if "однокомна" in lower or "одонкомнатная" in lower:
        return 1
    if "двухкомна" in lower:
        return 2
    if "трехкомн" in lower or "трёх" in lower:
        return 3
    if "четырехко" in lower:
        return 4
    if "пятикомнат" in lower:
        return 5
    if "студия" in lower or "студия" in lower:
        return 0
    return None

def parse_apartment_data(apartment):
    size_sqm = extract_square_meters(apartment["apartment_type"])
    num_rooms = extract_rooms(apartment["apartment_type"])
    price = extract_price(apartment["price"]) if "price" in apartment else None
    if price:
        price = int(str(price).replace(" ", ""))

    return {
        "apartment_type": apartment["apartment_type"],
        "price": price,
        "size_sqm": size_sqm,
        "num_rooms": int(num_rooms) if num_rooms is not None else None
    }
    
def parse_json_files(directory="knowledge_files"):
    session = Session()
    
    session.query(Apartment).delete()
    session.query(ResidentialComplex).delete()
    session.commit()
    
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            complex_obj = ResidentialComplex(
                complex_name=data.get("complex_name"),
                area=data.get("area"),
                general_texts=data.get("general_texts", "")
            )
            session.add(complex_obj)
            session.flush()  # Получаем ID для связки

            for apt in data.get("apartments_with_prices", []):
                apt_data = parse_apartment_data(apt)
                apartment = Apartment(
                    apartment_type=apt_data["apartment_type"],
                    price=apt_data["price"],
                    size_sqm=apt_data["size_sqm"],
                    num_rooms=apt_data["num_rooms"],
                    complex_id=complex_obj.id
                )
                session.add(apartment)

    session.commit()
    session.close()
    logger.info("Данные успешно загружены в БД.")


import re

def parse_filter_text(text: str, complex_names=None):
    params = {
        "complex_search": None,
        "city": None,
        "area": None,
        "complex_search_phrase": None,
        "complex_names": None,
        "num_rooms": None,
        "min_square": None,
        "max_square": None,
        "min_price": None,
        "max_price": None,
        "sort_price": None,
        "isfilter": True,
        "limit": 3,
    }
    if complex_names:
        params["complex_names"] = complex_names

    for line in text.strip().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if value == "" or value == "пусто":
            continue
        if key == "комнат":
            params["num_rooms"] = [int(n.strip()) for n in value.split(",")]
        elif key == "минимальная площадь":
            params["min_square"] = int(value)
        elif key == "максимальная площадь":
            params["max_square"] = int(value)
        elif key == "минимальная цена":
            params["min_price"] = int(value)
        elif key == "максимальная цена":
            params["max_price"] = int(value)
        elif key == "город":
            params["city"] = value
        elif key == "район" and value is not None and value.lower() == "неправильный район":
            params["isfilter"] = False
            params["area"] = None
        elif key == "район":
            params["area"] = value.lower()
        elif key == "жк" and value is not None:
            params["complex_names"] = [n.strip() for n in value.split(",")]
        elif key == "поиск жк":
            params["complex_search"] = True if value == "да" else False
        elif key == "весь список":
            params["limit"] = None if value == "да" else 3
        elif key == "фраза для поиска жк":
            params["complex_search_phrase"] = value
        elif key == "сортировка цены":
            if value in ["asc", "desc"]:
                params["sort_price"] = value

    return params