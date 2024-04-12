import os
from fastapi import FastAPI, Form, Request, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine, SessionLocal
from sqlalchemy.orm import Session
import models
from pydantic import BaseModel

from models import User
import bcrypt

from models import Likes

from starlette.middleware.sessions import SessionMiddleware

# 여기서 데이터베이스 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# session middleware 설치
app.add_middleware(SessionMiddleware, secret_key="secret_key")

abs_path = os.path.dirname(os.path.realpath(__file__))

# html 템플릿 객체 생성
# templates = Jinja2Templates(directory="templates")
templates = Jinja2Templates(directory=f"{abs_path}/templates")

# static 폴더(정적파일 폴더)를 app에 연결
# app.mount("/static", StaticFiles(directory=f"static"))
app.mount("/static", StaticFiles(directory=f"{abs_path}/static"))

# Dependency Injection(의존성 주임을 위한 함수)
# yield :  FastAPI가 함수 실행을 일시 중지하고 DB 세션을 호출자에게 반환하도록 지시


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get('user_id')

    if not user_id:
        return templates.TemplateResponse("login.html", {"request": request, "error": "로그인이 필요한 세션입니다"})

    todos = db.query(models.Todo).order_by(models.Todo.likes.desc())

    if not todos:
        todos = []  # Make sure todos is always a list, not an integer

    return templates.TemplateResponse("index.html",
                                      {"request": request,
                                       "todos": todos,
                                       "user_id": user_id})


@app.post("/add")
def add(req: Request, title: str = Form(...), img: str = Form(None), db: Session = Depends(get_db)):
    user_id = req.session.get('user_id')
    # Todo 객체 생성
    new_todo = models.Todo(task=title, img=img, uid=user_id)
    # DB테이블에 create
    db.add(new_todo)
    # db 트랜젝션 완료
    db.commit()
    url = app.url_path_for("home")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


# 수정할 todo 클릭했을 때
@app.get("/update/{todo_id}")
def update(req: Request, todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    print(todo.completed)
    todo.completed = not todo.completed
    db.commit()
    url = app.url_path_for("home")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

# todo 삭제


@app.get("/delete/{todo_id}")
def delete(todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    db.delete(todo)
    db.commit()
    url = app.url_path_for("home")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

#좋아요
@app.get("/like/{todo_id}")
def add(req: Request, todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    todo.likes = todo.likes + 1
    db.commit()
    url = app.url_path_for("home")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

@app.post("/like/{todo_id}")
def like_todo(todo_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="User not logged in")
    # 해당 todo_id를 가진 Todo 객체를 찾습니다.
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    # 해당 유저가 이미 해당 Todo를 좋아요 했는지 확인합니다.
    existing_like = db.query(Likes).filter(Likes.todo_id == todo_id, Likes.liked_user == user_id).first()
    # 이미 좋아요를 한 경우에는 좋아요 수만 증가시킵니다.
    if existing_like:
        existing_like.liked_count += 1
    else:
        # 좋아요를 기록하기 위해 Likes 테이블에 새로운 레코드를 추가합니다.
        new_like = Likes(todo_id=todo_id, liked_user=user_id, liked_count=1)
        db.add(new_like)
    # 해당 Todo의 좋아요 수를 1 증가시킵니다.
    todo.likes += 1
    # 변경사항을 커밋합니다.
    db.commit()
    # 홈 페이지로 리다이렉트합니다.
    return RedirectResponse(url=app.url_path_for("home"), status_code=status.HTTP_303_SEE_OTHER)

#----------이 밑으로 회원---------
class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


@app.post("/signup/")
def create_user(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(
            status_code=400, detail="Username already registered")
    new_user = User(username=username,
                    password=get_password_hash(password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login/")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == username).first()

    # 인증된 사용자 없음
    if not db_user or not verify_password(password, db_user.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "잘못된 아이디 혹은 비밀번호 입니다ㅠ"})

    # 로그인 성공시 session 에 사용자 정보(user_id) 담아서 보내줌
    request.session['user_id'] = db_user.id

    print(db_user.id)
    
    todos = db.query(models.Todo).order_by(models.Todo.likes.desc())

    if not todos:
        todos = []  # Make sure todos is always a list, not an integer


    return templates.TemplateResponse("index.html", {"request": request,
                                                     "user_id": db_user.id,
                                                     "todos" : todos})


@app.get("/like/{todo_id}/list")
def get_like_list(todo_id: int, db: Session = Depends(get_db)):
    # 해당 todo_id를 가진 Todo 객체를 찾습니다.
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    # 해당 Todo에 대한 좋아요 리스트를 불러옵니다.
    like_list = db.query(Likes).filter(Likes.todo_id == todo_id).all()
    return {"todo_id": todo_id, "like_list": like_list}

# 로그아웃 기능
@app.post("/logout/")
def logout(request: Request):
    request.session.pop('user_id', None)

    return templates.TemplateResponse("login.html", {"request": request})




# 로그인 페이지
@app.get("/login")
def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 회원가입 페이지


@app.get("/signup")
def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})
