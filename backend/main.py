import json
from typing import Optional
import uuid
from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import urlencode
import os
import httpx
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel import select
from datetime import datetime, timezone, timedelta, time
from models.models import  Event, User, EventType
from sqlalchemy import Column, ForeignKey, Integer, String, Time, Enum as SAEnum
from sqlmodel import Session, select
from google.auth.transport.requests import Request as GoogleRequest
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from fastapi import Query


app = FastAPI()

load_dotenv()  

@app.on_event("startup")
def on_startup():
    init_db()
    
DATABASE_URL = "postgresql://neondb_owner:npg_RML4fxHwkJN0@ep-holy-feather-a1xpnx0i-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session
def init_db():
    SQLModel.metadata.create_all(engine)
    
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
    raise RuntimeError("Missing required Google OAuth environment variables")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"
CALENDAR_LIST_ENDPOINT = "https://www.googleapis.com/calendar/v3/users/me/calendarList"


app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    name: Optional[str]
    picture: Optional[str]
    
class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: EventType
    event_date: datetime
    task_time: time
    duration_minutes: Optional[int] = 60
    add_to_google: Optional[bool] = False


class EventRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    type: EventType
    event_date: datetime
    task_time: time
    duration_minutes: int
    is_synced: bool


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <a href="/login">Login with Google</a>
    """

# in response to frontend request for current user
@app.get("/api/me")
def get_current_user(request: Request):
    email = request.cookies.get("email")
    if not email:
        raise HTTPException(401, "Not logged in")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(404, "User not found")
        return {
            "id": str(user.user_id),
            "name": user.name,
            "email": user.email,
            "role": "student", 
        }


@app.get("/login")
def login():
    query_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/calendar",
        "access_type": "offline",
        "prompt": "consent",
        "hd": "northsouth.edu",
    }
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(query_params)}"
    return RedirectResponse(url)

@app.get("/logout")
def logout():
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    login_url = f"{frontend_url}/login"

    resp = RedirectResponse(url=login_url, status_code=302)
    # clear the cookie by setting empty value and expired date
    resp.delete_cookie(key="email")
    return resp

# gets all the permissions and user info, calendar list
@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")  # seconds

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to retrieve access token: {token_data}",
            )

        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(GOOGLE_USERINFO_ENDPOINT, headers=headers)
        userinfo = userinfo_response.json()
        email = userinfo.get("email")

        # ✅ Check domain restriction
        if not email or not email.endswith("@northsouth.edu"):
            return HTMLResponse(
                "<h2>Access denied</h2><p>You must login with a northsouth.edu email.</p>",
                status_code=403,
            )
            
        calendar_response = await client.get(CALENDAR_LIST_ENDPOINT, headers=headers)
        calendar_data = calendar_response.json()
        primary_calendar_id = None
        items = calendar_data.get("items", [])
        for cal in items:
            if cal.get("primary"):
                primary_calendar_id = cal["id"]
                break
        if not primary_calendar_id and items:
            primary_calendar_id = items[0]["id"]

        with Session(engine) as session:
            statement = select(User).where(User.email == email)
            db_user = session.exec(statement).first()

            expiry_time = None
            if expires_in:
                expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            if not db_user:
                # new user
                db_user = User(
                    email=email,
                    google_id=userinfo.get("id"),
                    google_access_token=access_token,
                    google_refresh_token=refresh_token,
                    token_expiry=expiry_time,
                    calendar_id=primary_calendar_id
            )
                session.add(db_user)
            else:
                # existing user -> update tokens
                db_user.google_access_token = access_token
                if refresh_token:  # Google may not return it every time
                    db_user.google_refresh_token = refresh_token
                db_user.token_expiry = expiry_time
                db_user.calendar_id = primary_calendar_id


            session.commit()
            session.refresh(db_user)
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        next_url = request.query_params.get("next") or f"{frontend_url}/"

        resp = RedirectResponse(next_url, status_code=302)
        resp.set_cookie(
            key="email",
            value=email,
            httponly=True,
            samesite="lax",  # allow cross-site navigation
            secure=False     # only use True in production with HTTPS
        )

        return resp

# creating event both in local DB and Google Calendar
@app.post("/api/events", response_model=EventRead)
def create_event(
    event: EventCreate,
    request: Request,
    db: Session = Depends(get_session)
):
    email = request.cookies.get("email")
    if not email:
        raise HTTPException(401, "Not logged in")

    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(404, "User not found")

    # create DB event
    new_event = Event(
        user_id=user.user_id,
        title=event.title,
        description=event.description,
        type=event.type,
        event_date=event.event_date,
        task_time=event.task_time,
        duration_minutes=event.duration_minutes,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # push to Google Calendar if requested
    if event.add_to_google and (user.google_access_token or user.google_refresh_token):
        try:
            creds = refresh_google_token(user, db)
            if not creds:
                creds = Credentials(
                token=user.google_access_token,
                refresh_token=user.google_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET
                )
            
            service = build("calendar", "v3", credentials=creds)

            start_dt = datetime.combine(
                event.event_date.date(), event.task_time
            )
            end_dt = start_dt + timedelta(minutes=event.duration_minutes or 60)

            g_event = {
                "summary": event.title,
                "description": event.description,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            }

            created = service.events().insert(
                calendarId=user.calendar_id or "primary", body=g_event
            ).execute()

            new_event.google_event_id = created["id"]
            new_event.is_synced = True
            db.commit()
            db.refresh(new_event)
        except Exception as e:
            print(f"Google Calendar sync failed: {e}")
    return new_event

@app.get("/api/events", response_model=list[EventRead])
def get_events(request: Request, db: Session = Depends(get_session)):
    email = request.cookies.get("email")
    if not email:
        raise HTTPException(401, "Not logged in")

    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(404, "User not found")

    events = db.exec(select(Event).where(Event.user_id == user.user_id)).all()
    return events


@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    email = request.cookies.get("email")
    if not email:
        raise HTTPException(401, "Not logged in")

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(401, "User not found")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{email} - Google Calendar</title>
        <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/main.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/main.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            #calendar {{ max-width: 900px; margin: 40px auto; }}
        </style>
    </head>
    <body>
        <h2>Welcome {email}</h2>
        <h3>Your Google Calendar</h3>
        <div id="calendar"></div>

        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var calendarEl = document.getElementById('calendar');
            var calendar = new FullCalendar.Calendar(calendarEl, {{
                initialView: 'dayGridMonth',
                headerToolbar: {{
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
                }},
                events: '/api/events',  // fetch live events
                eventClick: function(info) {{
                    info.jsEvent.preventDefault();
                    if (info.event.url) {{
                        window.open(info.event.url, '_blank');
                    }}
                }}
            }});
            calendar.render();
        }});
        </script>
    </body>
    </html>
    """

def refresh_google_token(user: User, db: Session):
    if user.google_refresh_token:
        creds = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        
        if creds.expired:
            creds.refresh(GoogleRequest())
            user.google_access_token = creds.token
            user.token_expiry = creds.expiry
            db.commit()
        
        return creds
    return None


def fetch_google_events(access_token, refresh_token):
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/calendar"]
    )

    service = build("calendar", "v3", credentials=creds)

    now = datetime.utcnow().isoformat() + "Z"
    future = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=future,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events_result.get("items", [])



@app.get("/api/google/events")
def list_google_events(
    request: Request,
    db: Session = Depends(get_session),
    time_min: Optional[str] = Query(None, description="ISO string, e.g. 2025-01-01T00:00:00Z"),
    time_max: Optional[str] = Query(None, description="ISO string, e.g. 2025-01-31T23:59:59Z"),
) -> List[Dict[str, Any]]:
    """
    Returns normalized Google Calendar events for the current user between time_min and time_max.
    """
    email = request.cookies.get("email")
    if not email:
        raise HTTPException(401, "Not logged in")

    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(404, "User not found")

    creds = refresh_google_token(user, db)
    if not creds:
        # User hasn’t connected Google or no refresh token
        return []

    service = build("calendar", "v3", credentials=creds)

    # Defaults: show next 31 days if caller doesn’t pass range
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    if not time_min:
        time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not time_max:
        time_max = (now + timedelta(days=31)).isoformat()

    items = service.events().list(
        calendarId=user.calendar_id or "primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])

    # Normalize fields for the frontend
    normalized = []
    for ev in items:
        start = ev.get("start", {})
        end = ev.get("end", {})
        start_dt = start.get("dateTime") or start.get("date")  # all-day events have 'date'
        end_dt = end.get("dateTime") or end.get("date")

        normalized.append({
            "id": ev.get("id"),
            "title": ev.get("summary") or "(No title)",
            "start": start_dt,       # ISO string
            "end": end_dt,           # ISO string
            "htmlLink": ev.get("htmlLink"),
            "isAllDay": "date" in start,
          # you can add more fields as needed
        })
    return normalized
