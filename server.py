from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import sqlite3
import os
import random
import string
import json
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect

load_dotenv()

SECRET_KEY           = os.getenv("SECRET_KEY")
ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ── DB 초기화 ────────────────────────────────
def get_db():
    conn = sqlite3.connect("events.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn   = get_db()
    cursor = conn.cursor()

    # 병원 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT UNIQUE NOT NULL,
            code       TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 사용자 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'nurse',
            rooms       TEXT NOT NULL DEFAULT '',
            email       TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    """)

    # 이벤트 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            room        TEXT NOT NULL,
            type        TEXT NOT NULL,
            message     TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    """)

    # 설정 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            hospital_id INTEGER NOT NULL,
            key         TEXT NOT NULL,
            value       TEXT NOT NULL,
            PRIMARY KEY (hospital_id, key),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ── 병원 코드 생성 ───────────────────────────
def generate_hospital_code():
    return 'HOSP-' + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )

# ── JWT 토큰 ─────────────────────────────────
def create_token(data: dict):
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload     = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username    = payload.get("sub")
        role        = payload.get("role")
        rooms       = payload.get("rooms")
        hospital_id = payload.get("hospital_id")
        if username is None:
            raise HTTPException(status_code=401, detail="인증 실패")
        return {
            "username":    username,
            "role":        role,
            "rooms":       rooms,
            "hospital_id": hospital_id
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="토큰 만료 또는 오류")

def admin_only(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능")
    return user

# ── 병원 등록 API ────────────────────────────
class HospitalRegister(BaseModel):
    name:     str
    username: str
    password: str
    email:    str

@app.post("/register/hospital")
def register_hospital(data: HospitalRegister):
    conn   = get_db()
    cursor = conn.cursor()

    # 병원 이름 중복 확인
    cursor.execute("SELECT id FROM hospitals WHERE name = ?", (data.name,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="이미 등록된 병원 이름이에요")

    # 아이디 중복 확인
    cursor.execute("SELECT id FROM users WHERE username = ?", (data.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디예요")

    # 병원 코드 생성
    code = generate_hospital_code()
    while True:
        cursor.execute("SELECT id FROM hospitals WHERE code = ?", (code,))
        if not cursor.fetchone():
            break
        code = generate_hospital_code()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 병원 등록
    cursor.execute(
        "INSERT INTO hospitals (name, code, created_at) VALUES (?, ?, ?)",
        (data.name, code, timestamp)
    )
    hospital_id = cursor.lastrowid

    # 관리자 계정 생성
    hashed = pwd_context.hash(data.password)
    cursor.execute(
        "INSERT INTO users (hospital_id, username, password, role, rooms, email)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (hospital_id, data.username, hashed, "admin", "전체", data.email)
    )

    # 기본 설정 추가
    defaults = [
        ("report_interval", "weekly"),
        ("report_time",     "09:00"),
        ("report_day",      "monday"),
    ]
    for key, value in defaults:
        cursor.execute(
            "INSERT INTO settings (hospital_id, key, value) VALUES (?, ?, ?)",
            (hospital_id, key, value)
        )

    conn.commit()
    conn.close()

    return {
        "status":        "ok",
        "hospital_code": code,
        "message":       f"병원 코드: {code} — 요양사 가입 시 필요해요!"
    }

# ── 요양사 회원가입 API ──────────────────────
class NurseRegister(BaseModel):
    hospital_code: str
    username:      str
    password:      str
    email:         str

@app.post("/register/nurse")
def register_nurse(data: NurseRegister):
    conn   = get_db()
    cursor = conn.cursor()

    # 병원 코드 확인
    cursor.execute(
        "SELECT id FROM hospitals WHERE code = ?", (data.hospital_code,)
    )
    hospital = cursor.fetchone()
    if not hospital:
        conn.close()
        raise HTTPException(status_code=400, detail="유효하지 않은 병원 코드예요")

    # 아이디 중복 확인
    cursor.execute("SELECT id FROM users WHERE username = ?", (data.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디예요")

    hashed = pwd_context.hash(data.password)
    cursor.execute(
        "INSERT INTO users (hospital_id, username, password, role, rooms, email)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (hospital["id"], data.username, hashed, "nurse", "", data.email)
    )

    conn.commit()
    conn.close()
    return {"status": "ok"}

# ── 병실 카메라 등록 API ─────────────────────
class CameraRegister(BaseModel):
    hospital_code: str
    room:          str
    password:      str

@app.post("/register/camera")
def register_camera(data: CameraRegister):
    conn   = get_db()
    cursor = conn.cursor()

    # 병원 코드 확인
    cursor.execute(
        "SELECT id FROM hospitals WHERE code = ?", (data.hospital_code,)
    )
    hospital = cursor.fetchone()
    if not hospital:
        conn.close()
        raise HTTPException(status_code=400, detail="유효하지 않은 병원 코드예요")

    # 카메라 계정 아이디 = 병원코드_병실번호
    username = f"{data.hospital_code}_{data.room}"

    # 중복 확인
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="이미 등록된 병실이에요")

    hashed = pwd_context.hash(data.password)
    cursor.execute(
        "INSERT INTO users (hospital_id, username, password, role, rooms, email)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (hospital["id"], username, hashed, "camera", data.room, "")
    )

    conn.commit()
    conn.close()
    return {"status": "ok", "camera_id": username}

# ── 로그인 API ───────────────────────────────
@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ?", (form.username,)
    )
    user = cursor.fetchone()
    conn.close()

    if not user or not pwd_context.verify(form.password, user["password"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸어요")

    token = create_token({
        "sub":         user["username"],
        "role":        user["role"],
        "rooms":       user["rooms"],
        "hospital_id": user["hospital_id"],
    })
    return {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user["role"]
    }

# ── 내 정보 조회 API ─────────────────────────
@app.get("/me")
def get_me(user=Depends(get_current_user)):
    return user

# ── 사용자 관리 API ──────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str
    role:     str
    rooms:    str
    email:    str

@app.get("/users")
def get_users(user=Depends(admin_only)):
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, role, rooms, email FROM users"
        " WHERE hospital_id = ?",
        (user["hospital_id"],)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/users")
def create_user(u: UserCreate, user=Depends(admin_only)):
    hashed = pwd_context.hash(u.password)
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users"
            " (hospital_id, username, password, role, rooms, email)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user["hospital_id"], u.username, hashed, u.role, u.rooms, u.email)
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디예요")

@app.delete("/users/{user_id}")
def delete_user(user_id: int, user=Depends(admin_only)):
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM users WHERE id = ? AND hospital_id = ?",
        (user_id, user["hospital_id"])
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ── 이벤트 API ───────────────────────────────
class Event(BaseModel):
    room:          str
    type:          str
    message:       str
    hospital_code: str

@app.post("/event")
def create_event(event: Event):
    conn   = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM hospitals WHERE code = ?", (event.hospital_code,)
    )
    hospital = cursor.fetchone()
    if not hospital:
        conn.close()
        raise HTTPException(status_code=400, detail="유효하지 않은 병원 코드예요")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO events (hospital_id, room, type, message, timestamp)"
        " VALUES (?, ?, ?, ?, ?)",
        (hospital["id"], event.room, event.type, event.message, timestamp)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "timestamp": timestamp}

@app.get("/events")
def get_events(user=Depends(get_current_user)):
    conn   = get_db()
    cursor = conn.cursor()

    if user["role"] == "admin":
        cursor.execute(
            "SELECT * FROM events WHERE hospital_id = ?"
            " ORDER BY timestamp DESC LIMIT 50",
            (user["hospital_id"],)
        )
    else:
        rooms = user["rooms"].split(",")
        placeholders = ",".join("?" * len(rooms))
        cursor.execute(
            f"SELECT * FROM events WHERE hospital_id = ?"
            f" AND room IN ({placeholders})"
            f" ORDER BY timestamp DESC LIMIT 50",
            [user["hospital_id"]] + rooms
        )

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── 리포트 API ───────────────────────────────
@app.get("/reports")
def get_reports(user=Depends(get_current_user)):
    report_list = []
    base_path   = f"reports/{user['hospital_id']}"

    if os.path.exists(base_path):
        for month in sorted(os.listdir(base_path), reverse=True):
            month_path = f"{base_path}/{month}"
            if os.path.isdir(month_path):
                for filename in sorted(os.listdir(month_path), reverse=True):
                    if filename.endswith(".pdf"):
                        report_list.append({
                            "filename": filename,
                            "month":    month,
                            "url":      f"/reports/download/{user['hospital_id']}/{month}/{filename}"
                        })
    return report_list

@app.get("/reports/download/{hospital_id}/{month}/{filename}")
def download_report(
    hospital_id: int, month: str, filename: str,
    user=Depends(get_current_user)
):
    if user["hospital_id"] != hospital_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없어요")

    path = f"reports/{hospital_id}/{month}/{filename}"
    if os.path.exists(path):
        return FileResponse(
            path, media_type="application/pdf", filename=filename
        )
    raise HTTPException(status_code=404, detail="파일을 찾을 수 없어요")

@app.post("/reports/generate")
def generate_report_now(user=Depends(admin_only)):
    from utils.report import generate_report
    filename = generate_report(user["hospital_id"])
    return {"status": "ok", "filename": filename}

# ── 설정 API ────────────────────────────────
@app.get("/settings")
def get_settings(user=Depends(get_current_user)):
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT key, value FROM settings WHERE hospital_id = ?",
        (user["hospital_id"],)
    )
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

class Settings(BaseModel):
    report_interval: str
    report_time:     str
    report_day:      str

@app.post("/settings")
def save_settings(s: Settings, user=Depends(admin_only)):
    conn   = get_db()
    cursor = conn.cursor()
    for key, value in [
        ("report_interval", s.report_interval),
        ("report_time",     s.report_time),
        ("report_day",      s.report_day),
    ]:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (hospital_id, key, value)"
            " VALUES (?, ?, ?)",
            (user["hospital_id"], key, value)
        )
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ── 서버 상태 확인 ───────────────────────────
@app.get("/")
def health_check():
    return {"status": "서버 정상 작동 중"}

# ── WebSocket 연결 관리 ──────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# ── 카메라 WebSocket ─────────────────────────
@app.websocket("/ws/camera")
async def camera_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg  = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(
                    json.dumps({"type": "pong"})
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)