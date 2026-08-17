from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id= Column(Integer, primary_key= True, index= True)
    username= Column(String, unique= True, index= True, nullable= False)
    password_hash= Column(String, nullable= False)
    role= Column(String, nullable= False)
    department= Column(String, nullable= False)

    tickets= relationship(
        "Ticket",
        foreign_keys= "Ticket.owner_id",
        back_populates= "owner"
    )

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    owner_id= Column(Integer, ForeignKey("users.id"), nullable= False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    department = Column(String, nullable=False)
    status = Column(
        String,
        nullable=False,
        default="open"
    )

    owner= relationship(
        "User",
        foreign_keys= [owner_id],
        back_populates="tickets"
    )

    assignee= relationship(
        "User",
        foreign_keys= [assignee_id]
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    previous_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)