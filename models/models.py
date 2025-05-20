from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Создаём базовый класс
Base = declarative_base()

# Движок и фабрика сессий
engine = create_engine("sqlite:///complexes.db", echo=False)
Session = sessionmaker(bind=engine)

class Area(Base):
    __tablename__ = 'areas'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('areas.id'), nullable=True)
    
    # Связь многие-к-одному: у района один родитель
    parent = relationship(
        "Area",
        remote_side=[id],  # Указываем, что id — это ключ родительского района
        back_populates="microdistricts"
    )
    
    # Связь один-ко-многим: у района много микрорайонов
    microdistricts = relationship(
        "Area",
        back_populates="parent"
    )

class ResidentialComplex(Base):
    __tablename__ = 'residential_complexes'

    id = Column(Integer, primary_key=True)
    complex_name = Column(String, nullable=False)
    
    area_id = Column(Integer, ForeignKey('areas.id'), nullable=True)
    area = relationship("Area", back_populates="complexes")  # Добавляем обратную связь
    general_texts = Column(String, nullable=True)
    short_text = Column(String, nullable=True)
    city = Column(String, nullable=True, default="Владивосток")

    apartments = relationship("Apartment", back_populates="complex")

# Добавляем обратную связь для Area -> ResidentialComplex
Area.complexes = relationship(
    "ResidentialComplex",
    back_populates="area"
)

# Модель квартиры
class Apartment(Base):
    __tablename__ = 'apartments'

    id = Column(Integer, primary_key=True)
    apartment_type = Column(String, nullable=False)
    price = Column(Integer, nullable=True)
    size_sqm = Column(Float, nullable=True)
    num_rooms = Column(Integer, nullable=True)
    
    complex_id = Column(Integer, ForeignKey('residential_complexes.id'))
    complex = relationship("ResidentialComplex", back_populates="apartments")


# Создаём таблицы
Base.metadata.create_all(engine)