from datetime import datetime
import enum
from sqlalchemy.types import DateTime, Integer
from db.base import Base, TimestampMixin
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Enum, String, Text
from sqlalchemy.sql.schema import ForeignKey

class ReservationStatus(str, enum.Enum):
    RESERVED = "reserved"
    RELEASED = "released"
    
class Stock(Base, TimestampMixin):
    __tablename__ = "stock_inventory"
    __table_args__ = {"schema" : "inventory"}
    
    item_name : Mapped[str] = mapped_column(String(40))
    item_id : Mapped[str] = mapped_column(String(20), primary_key=True)
    unit_price: Mapped[int] = mapped_column()
    available_qnty: Mapped[int] = mapped_column()
    
class Reservation(Base, TimestampMixin):
    __tablename__ = "reservation"
    __table_args__ = {"schema" : "inventory"}

    order_id: Mapped[str] = mapped_column(String(20),  primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inventory.stock_inventory.item_id"))
    quantity: Mapped[int] = mapped_column()
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus),
        default=ReservationStatus.RESERVED
    )
    unit_price : Mapped[int] = mapped_column()
    total_price: Mapped[int] = mapped_column()


class OutboxMessage(Base, TimestampMixin):
    __tablename__ = "outbox_message"
    __table_args__ = {"schema": "inventory"}

    id : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(50))
    payload: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )