from sqlalchemy import Column, Integer, Boolean, String
from database import Base

class Todo(Base):
    __tablename__ = 'todos'

    id = Column(Integer, primary_key=True)
    task = Column(String(100))
    completed = Column(Boolean, default=False)
    likes = Column(Integer, default=0)
    img = Column(String(500), default="https://mblogthumb-phinf.pstatic.net/20160817_259/retspe_14714118890125sC2j_PNG/%C7%C7%C4%AB%C3%F2_%281%29.png?type=w800")
    uid = Column(Integer, default=0)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    password = Column(String(255))

class Likes(Base):
        __tablename__ = "likes"

        id = Column(Integer, primary_key=True)
        todo_id = Column(Integer)
        liked_user = Column(Integer)
        liked_count = Column(Integer)