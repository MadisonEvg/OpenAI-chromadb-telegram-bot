from sqlalchemy import asc, desc
from sqlalchemy import or_, func
from models.models import Apartment, ResidentialComplex, Area, Session
from collections import defaultdict
from itertools import islice
from logger_config import logger
import re


def get_filtered_apartments(
    area=None,
    num_rooms=None,
    min_square=None,
    max_square=None,
    min_price=None,
    max_price=None,
    city=None,
    sort_price="asc",
    complex_names=None,
    isfilter=True,
):
    if isfilter == False:
        return "Для указанного района отсутствуют варианты!"
    session = Session()
    query = session.query(Apartment).join(Apartment.complex)
    query_ResidentialComplex = session.query(
        ResidentialComplex.short_text, 
        ResidentialComplex.city, 
        ResidentialComplex.area,
        Area.name.label("area_name")
    )
    query = query.filter(Apartment.price != None)
    complex_filtered = ""
    if num_rooms is not None:
        query = query.filter(Apartment.num_rooms.in_(num_rooms))
    if min_square is not None:
        query = query.filter(Apartment.size_sqm >= min_square)
    if max_square is not None:
        query = query.filter(Apartment.size_sqm <= max_square)
    if min_price is not None:
        query = query.filter(Apartment.price >= min_price)
    if max_price is not None:
        query = query.filter(Apartment.price <= max_price)

    if sort_price == "desc":
        query = query.order_by(desc(Apartment.price))
    else:
        query = query.order_by(asc(Apartment.price))
    
    if complex_names:
        query = query.filter(ResidentialComplex.complex_name.in_(complex_names))
    if city is not None:
        query = query.filter(ResidentialComplex.city == city)
        query_ResidentialComplex = query_ResidentialComplex.filter(ResidentialComplex.city == city)
    if area is not None:
        # area_name = "БАМ"
        # area = session.query(Area).filter(func.lower(Area.name) == area.lower()).first()
        area_obj = session.query(Area).filter(Area.name == area).first()
        if not area_obj:
            return "Результат промежуточного анализа запроса: /n нету квартир под ваши параметры."
        
        # Если это район (parent_id IS NULL), ищем комплексы в районе и его микрорайонах
        if area_obj.parent_id is None:
            query = query.join(Area, ResidentialComplex.area_id == Area.id).filter(
                or_(Area.id == area_obj.id, Area.parent_id == area_obj.id)
            )
            query_ResidentialComplex = query_ResidentialComplex.join(Area).filter(
                or_(Area.id == area_obj.id, Area.parent_id == area_obj.id)
            )
        # Если это микрорайон, ищем только комплексы с этим area_id
        else:
            query = query.filter(ResidentialComplex.area_id == area_obj.id)
            query_ResidentialComplex = query_ResidentialComplex.join(Area).filter(
                ResidentialComplex.area_id == area_obj.id
            )
            
        print(area_obj)
        # query_ResidentialComplex = query_ResidentialComplex.join(Area).filter(
        #     or_(Area.id == area.id, Area.parent_id == area.id)
        # )
        results = query_ResidentialComplex.all()
        complex_filtered = "Список ЖК в этом районе, но не факт что в них есть квартира: \n"
        complex_filtered += "\n".join(f"{r.short_text} ({r.city}, {r.area_name})" for r in results if r.short_text)
        print('complex_filtered: ', complex_filtered)
        print('---------------')

    print(str(query.statement.compile(compile_kwargs={"literal_binds": True})))
    
    apartments = query.all()
    if len(apartments) == 0:
        return "Результат промежуточного анализа запроса: /n нету квартир под ваши параметры."
    
    # Группировка по (complex_name, apartment_type, price)
    # grouped = defaultdict(list)
    # for apt in apartments:
    #     key = (apt.complex.complex_name, apt.apartment_type, apt.price)
    #     grouped[key].append({
    #         "square": apt.size_sqm,
    #         "num_rooms": apt.num_rooms,
    #     })
        
    grouped = defaultdict(list)
    for apt in apartments:
        key = (apt.complex.complex_name, apt.apartment_type, apt.price)
        grouped[key].append({
            "square": apt.size_sqm,
            "num_rooms": apt.num_rooms,
            "complex_text": apt.complex.general_texts,
        })
        
    first_three_dd = defaultdict(list, islice(grouped.items(), 3))
    result = []
    compResidentialComplex_set = set()
    # инфа по комлексам из трёх подходящих результатов, добавляем в другом месте!
    for (complex_name, apartment_type, price), apts in first_three_dd.items():
        result.append({
            "complex_name": complex_name,
            "apartment_type": apartment_type,
            "price": price,
        })
    #     compResidentialComplex_set.add(apts[0]['complex_text'])

    # Формируем результат
    # result = []
    # compResidentialComplex_set = set()
    # for (complex_name, apartment_type, price), apts in grouped.items()[:3]:
    #     result.append({
    #         "complex_name": complex_name,
    #         "apartment_type": apartment_type,
    #         "price": price,
    #     })
    #     compResidentialComplex_set.add(apts.general_texts)
        
    # return result

    # Формируем результат
    # first_three_dd = defaultdict(list, islice(grouped.items(), 3))
    # result = []
    compResidentialComplex_set = set()
    # инфа по комлексам из трёх подходящих результатов, добавляем в другом месте!
    for (complex_name, apartment_type, price), apts in first_three_dd.items():
        result.append({
            "complex_name": complex_name,
            "apartment_type": apartment_type,
            "price": price,
        })
        compResidentialComplex_set.add(f"{complex_name}: {apts[0]['complex_text']}")
    # results_str = "Промежуточный анализ запроса. Если вопрос по квартирам, наприиер, самая дешёвая или типа того, то лучше брать информацию из этого списка: /n "
    results_str = ""
    for apt in result[0:3]:
        results_str += f"{apt['apartment_type']} Цена: {apt['price']} ЖК: {apt['complex_name']}\n"
    results_str += "\n"
    
    logger.info("-------------------Варианты от промежуточного анализа диалога-----")
    logger.info(results_str)
    logger.info("------------------------------------------------------------------")
    for compResidentialComplex in compResidentialComplex_set:
        results_str += f"{compResidentialComplex}\n\n"
    results_str += complex_filtered
    complex_full_info = ""
    if complex_names is not None and len(complex_names) == 1:
        complex_full_info = format_complex_with_apartments(session, complex_names[0])
    # results_str += "конец. "
    return "Результат промежуточного анализа запроса: /n" + results_str + "/n" + complex_full_info


def format_complex_with_apartments(session: Session, complex_name: str) -> str:
    complex_obj = session.query(ResidentialComplex).filter_by(complex_name=complex_name).first()
    if not complex_obj:
        return f"Жилой комплекс '{complex_name}' не найден."

    result = []
    result.append(f"Жилой комплекс: {complex_obj.complex_name}")
    result.append(f"Город: {complex_obj.city or 'не указано'}")
    result.append(f"Район: {complex_obj.area or 'не указано'}")
    result.append(f"Краткое описание: {complex_obj.short_text or 'не указано'}")
    result.append(f"Полное описание: {complex_obj.general_texts or 'не указано'}")
    result.append(f"Количество квартир: {len(complex_obj.apartments)}")

    result.append("Квартиры:")
    for apt in complex_obj.apartments:
        apt_type = apt.apartment_type or "не указано"
        size = f"{apt.size_sqm:.1f} м²" if apt.size_sqm else "размер не указан"
        rooms = f"{apt.num_rooms} комн." if apt.num_rooms else "кол-во комнат не указано"
        price = f"{apt.price:,} ₽" if apt.price else "цена не указана"

        result.append(f" - {apt_type}, {rooms}, {size}, {price}")

    return "\n".join(result)


def get_complex_info_by_names(complex_name_list):
    session = Session()
    complexes = session.query(ResidentialComplex).filter(
        ResidentialComplex.complex_name.in_(complex_name_list)
    ).all()
    
    result_str = "\n".join(
        f"{c.complex_name}, {c.area or '—'}, {c.general_texts or '—'}"
        for c in complexes
    )
    return result_str

def extract_russian_names():
    session = Session()
    complexes = session.query(ResidentialComplex).all()
    name_mapping = {}

    # pattern = re.compile(r'ЖК\s*["«](.+?)["»]')
    pattern = re.compile(r'ЖК\s+([А-Яа-яЁёA-Za-z\s\-]+)')
    # pattern = re.compile(r'ЖК\s*(?:(["«»])?([А-Яа-яA-Za-zёЁ\s\-]+)\1?)')

    for c in complexes:
        if c.general_texts:
            match = pattern.search(c.general_texts)
            if match:
                russian_name = f'ЖК "{match.group(1)}"'
                name_mapping[c.complex_name] = russian_name
            else:
                name_mapping[c.complex_name] = "— не найдено —"
        else:
            name_mapping[c.complex_name] = "— нет текста —"

    return name_mapping