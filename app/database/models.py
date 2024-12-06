from sqlalchemy import (
    BigInteger, DateTime, String, Integer, ForeignKey, Text, Time
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone, time


#
# Добавить в поездку поле с временем проездки
# Добавить в поездку поля с тексовым адресом для точки отправления и точки назначения
#

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__  = 'users'

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id =  mapped_column(BigInteger, nullable=False)
    us_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    notification_bufer: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    
    # Связь с таблицей Rides
    rides = relationship("Ride", back_populates="user", cascade="all, delete-orphan")
    
class Ride(Base):
    __tablename__  = 'rides'
    
    ride_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    arrival_time: Mapped[time] = mapped_column(Time, nullable=False)
    transport: Mapped[str] = mapped_column(String(20), nullable=False)
    notify_time_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    
    datetime_now_utc = datetime.now(timezone.utc)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.now(timezone.utc), nullable=True)
    
    
     # Внешний ключ к таблице User
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    # Связь с таблицей User
    user = relationship("User", back_populates="rides")
    

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

