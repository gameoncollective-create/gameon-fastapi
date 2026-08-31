
# main.py
from fastapi import FastAPI, HTTPException, Depends, status, Form, Request, Header
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import bcrypt
import secrets
import os
import csv
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURATION
# ============================================
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Add it in Render's Environment tab before starting the app.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PORT = int(os.getenv('PORT', 5002))

app = FastAPI(title="GameOn Collective API", version="1.0.0")

# CORS
ALLOWED_ORIGINS = [
    "https://gameoncollective.com",
    "https://www.gameoncollective.com",
]

ADMIN_KEY = os.getenv("ADMIN_KEY")

def verify_admin(x_admin_key: Optional[str] = Header(None)):
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Not authorized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session"
)

# Templates
templates = Jinja2Templates(directory="templates")

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# ============================================
# PYDANTIC MODELS
# ============================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    tier: str
    created_at: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    tier: str = "free"

class APIKeyGenerate(BaseModel):
    email: str
    tier: str = "standard"

# ============================================
# CSV LOADING FUNCTIONS
# ============================================

def load_csv(filename: str) -> List[Dict]:
    """Load data from CSV file"""
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                for key, value in row.items():
                    if key in ['id', 'team_id', 'goals', 'assists', 'appearances', 
                               'played', 'won', 'drawn', 'lost', 'gd', 'points', 
                               'gf', 'ga', 'position']:
                        try:
                            row[key] = int(value) if value else 0
                        except ValueError:
                            row[key] = 0
                    elif key in ['player_rating']:
                        try:
                            row[key] = float(value) if value else 0.0
                        except ValueError:
                            row[key] = 0.0
                data.append(row)
        print(f"✅ Loaded {len(data)} records from {filename}")
        return data
    except FileNotFoundError:
        print(f"⚠️ File not found: {filename}")
        return []
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return []

def save_csv(filename: str, data: List[Dict], fieldnames: List[str]):
    """Save data to CSV file"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ Saved {len(data)} records to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")
        return False

# ============================================
# LOAD DATA FROM CSV FILES
# ============================================

print("📂 Loading data from CSV files...")

# Load teams
all_teams_data = load_csv('data/teams.csv')
premier_teams = [t for t in all_teams_data if t.get('league') == 'Premier']
nsl_teams = [t for t in all_teams_data if t.get('league') == 'NSL']

# Load division teams
division_one_zone_a = load_csv('data/division_one_zone_a.csv')
division_one_zone_b = load_csv('data/division_one_zone_b.csv')

# Load players
players = load_csv('data/players.csv')

# Load featured players
featured_players = load_csv('data/featured_players.csv')

# Load standings
premier_standings = load_csv('data/standings_premier.csv')
nsl_zone_a_standings = load_csv('data/standings_nsl_zone_a.csv')
nsl_zone_b_standings = load_csv('data/standings_nsl_zone_b.csv')

# Load GPS data (includes vest assignments)
gps_data = load_csv('data/gps_data.csv')

# If GPS data doesn't exist, use defaults
if not gps_data:
    print("⚠️ No GPS data found, using defaults")
    gps_data = [
        {"player_id": 7, "player_name": "Monica Nakamu", "position": "Forward", "vest_number": 1,
         "total_distance_km": "TBD", "max_speed_kmh": "TBD", "sprints": "TBD", 
         "work_rate_percent": "TBD", "avg_heart_rate": "TBD", "status": "pending_vest"},
        {"player_id": 8, "player_name": "Cynthia Atieno", "position": "Forward", "vest_number": 2,
         "total_distance_km": "TBD", "max_speed_kmh": "TBD", "sprints": "TBD", 
         "work_rate_percent": "TBD", "avg_heart_rate": "TBD", "status": "pending_vest"},
        {"player_id": 3, "player_name": "Vivian Shiyonzo Khayati", "position": "Midfielder", "vest_number": 3,
         "total_distance_km": "TBD", "max_speed_kmh": "TBD", "sprints": "TBD", 
         "work_rate_percent": "TBD", "avg_heart_rate": "TBD", "status": "pending_vest"},
        {"player_id": 4, "player_name": "Yvonne Kavere Idagiza", "position": "Defender", "vest_number": 1,
         "total_distance_km": "TBD", "max_speed_kmh": "TBD", "sprints": "TBD", 
         "work_rate_percent": "TBD", "avg_heart_rate": "TBD", "status": "pending_vest"},
        {"player_id": 1, "player_name": "Lucy Kisaga Agisa", "position": "Goalkeeper", "vest_number": 2,
         "total_distance_km": "TBD", "max_speed_kmh": "TBD", "sprints": "TBD", 
         "work_rate_percent": "TBD", "avg_heart_rate": "TBD", "status": "pending_vest"},
        {"player_id": 2, "player_name": "Wilfrida Ouko Seda", "position": "Goalkeeper", "vest_number": 3,
         "total_distance_km": "TBD", "max_speed_kmh": "TBD", "sprints": "TBD", 
         "work_rate_percent": "TBD", "avg_heart_rate": "TBD", "status": "pending_vest"}
    ]

gps_sessions = [
    {
        "id": 1,
        "date": "Coming June 2026",
        "match": "First GPS tracking session",
        "vests_used": 3,
        "players_tracked": 6,
        "status": "upcoming"
    }
]

print(f"✅ Loaded {len(players)} players")
print(f"✅ Loaded {len(premier_teams)} Premier League teams")
print(f"✅ Loaded {len(nsl_teams)} NSL teams")
print(f"✅ Loaded {len(featured_players)} featured players")
print(f"✅ Loaded {len(gps_data)} GPS-tracked players")

# ============================================
# USER DATABASE (In-memory)
# ============================================
users_db: Dict[str, Dict] = {}
api_keys: Dict[str, Dict] = {}

# ============================================
# AUTHENTICATION FUNCTIONS
# ============================================
def get_user_by_email(email: str):
    for user_id, user_data in users_db.items():
        if user_data["email"] == email:
            return user_id, user_data
    return None, None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ============================================
# AUTHENTICATION ROUTES
# ============================================
@app.post("/register")
async def register(user_data: UserCreate):
    user_id, existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user_data.password)
    user_id = str(len(users_db) + 1)
    users_db[user_id] = {
        "email": user_data.email,
        "password_hash": hashed_password,
        "tier": "free",
        "created_at": datetime.now().isoformat()
    }
    return {"message": "User created successfully", "user_id": user_id}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_id, user_data = get_user_by_email(form_data.username)
    if not user_data or not pwd_context.verify(form_data.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id, "email": user_data["email"], "tier": user_data.get("tier", "free")},
        expires_delta=access_token_expires
    )
    
    user_out = UserOut(id=user_id, email=user_data["email"], tier=user_data.get("tier", "free"), created_at=user_data.get("created_at"))
    return Token(access_token=access_token, token_type="bearer", user=user_out)

# ============================================
# HTML ROUTES
# ============================================
@app.get("/", response_class=HTMLResponse)
async def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    user_id, user_data = get_user_by_email(email)
    if user_data and pwd_context.verify(password, user_data["password_hash"]):
        request.session["user_id"] = user_id
        request.session["user_email"] = user_data["email"]
        request.session["user_tier"] = user_data.get("tier", "free")
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    user_id, existing_user = get_user_by_email(email)
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})
    
    hashed_password = pwd_context.hash(password)
    user_id = str(len(users_db) + 1)
    users_db[user_id] = {
        "email": email,
        "password_hash": hashed_password,
        "tier": "free",
        "created_at": datetime.now().isoformat()
    }
    return RedirectResponse(url="/login", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    return templates.TemplateResponse("subscribe.html", {"request": request})

# ============================================
# TEAM ROUTES
# ============================================
@app.get("/team/{team_id}", response_class=HTMLResponse)
async def team_profile(request: Request, team_id: int):
    all_teams = premier_teams + nsl_teams + division_one_zone_a + division_one_zone_b
    team = next((t for t in all_teams if int(t["id"]) == team_id), None)
    
    if not team:
        return HTMLResponse("Team not found", status_code=404)
    
    team_players = [p for p in players if int(p.get("team_id", 0)) == team_id]
    
    players_by_position = {
        "Goalkeeper": [],
        "Defender": [],
        "Midfielder": [],
        "Forward": []
    }
    
    for player in team_players:
        pos = player.get("position", "Unknown")
        if "Goalkeeper" in pos or "GK" in pos:
            players_by_position["Goalkeeper"].append(player)
        elif "Defender" in pos:
            players_by_position["Defender"].append(player)
        elif "Midfielder" in pos:
            players_by_position["Midfielder"].append(player)
        elif "Forward" in pos or "Striker" in pos:
            players_by_position["Forward"].append(player)
        else:
            players_by_position["Midfielder"].append(player)
    
    # Check standings
    standing = next((s for s in premier_standings if s["team"] == team["name"]), None)
    if not standing:
        standing = next((s for s in nsl_zone_a_standings if s["team"] == team["name"]), None)
    if not standing:
        standing = next((s for s in nsl_zone_b_standings if s["team"] == team["name"]), None)
    
    return templates.TemplateResponse("team-profile.html", {
        "request": request,
        "team": team,
        "players": team_players,
        "players_by_position": players_by_position,
        "standing": standing
    })

# ============================================
# PLAYER ROUTES
# ============================================
@app.get("/player/{player_id}", response_class=HTMLResponse)
async def player_profile(request: Request, player_id: int):
    player = next((p for p in players if int(p["id"]) == player_id), None)
    featured = next((p for p in featured_players if int(p["id"]) == player_id), None)
    
    if not player and not featured:
        return HTMLResponse("Player not found", status_code=404)
    
    gps = next((g for g in gps_data if int(g["player_id"]) == player_id), None)
    
    team = None
    if player:
        all_teams = premier_teams + nsl_teams + division_one_zone_a + division_one_zone_b
        team = next((t for t in all_teams if int(t["id"]) == int(player.get("team_id", 0))), None)
    
    return templates.TemplateResponse("player.html", {
        "request": request,
        "player": player,
        "featured": featured,
        "gps": gps,
        "team": team
    })

# ============================================
# API ROUTES - TEAMS
# ============================================
@app.get("/api/premier/teams")
async def get_premier_teams():
    return premier_teams

@app.get("/api/nsl/teams")
async def get_nsl_teams():
    return nsl_teams

@app.get("/api/division-one/zone-a/teams")
async def get_zone_a_teams():
    return division_one_zone_a

@app.get("/api/division-one/zone-b/teams")
async def get_zone_b_teams():
    return division_one_zone_b

# ============================================
# API ROUTES - PLAYERS
# ============================================
@app.get("/api/players")
async def get_all_players():
    return players

@app.get("/api/featured-players")
async def get_featured_players():
    return featured_players

@app.get("/api/player/{player_id}")
async def get_player(player_id: int):
    player = next((p for p in players if int(p["id"]) == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    gps = next((g for g in gps_data if int(g["player_id"]) == player_id), None)
    all_teams = premier_teams + nsl_teams + division_one_zone_a + division_one_zone_b
    team = next((t for t in all_teams if int(t["id"]) == int(player.get("team_id", 0))), None)
    
    return {
        "player": player,
        "team": team,
        "gps": gps
    }

# ============================================
# API ROUTES - STANDINGS
# ============================================
@app.get("/api/premier/standings")
async def get_premier_standings():
    return premier_standings

@app.get("/api/nsl/standings")
async def get_nsl_standings():
    return {"zone_a": nsl_zone_a_standings, "zone_b": nsl_zone_b_standings}

# ============================================
# API ROUTES - SEARCH
# ============================================
@app.get("/api/search")
async def search(q: Optional[str] = ""):
    query = q.lower() if q else ""
    results = []
    
    # Search teams
    for team in premier_teams + nsl_teams + division_one_zone_a + division_one_zone_b:
        if query in team['name'].lower() or query in team.get('city', '').lower():
            results.append({
                "type": "team",
                "id": team['id'],
                "name": team['name'],
                "city": team.get('city', ''),
                "league": "Premier League" if team in premier_teams else "NSL" if team in nsl_teams else "Division One"
            })
    
    # Search players
    for player in players:
        if query in player['name'].lower():
            results.append({
                "type": "player",
                "id": player['id'],
                "name": player['name'],
                "position": player.get('position', ''),
                "team_id": player.get('team_id')
            })
    
    return {"query": query, "results": results[:20], "count": len(results)}

# ============================================
# API ROUTES - GPS
# ============================================
@app.get("/api/gps/sessions")
async def get_gps_sessions():
    return gps_sessions

@app.get("/api/gps/data")
async def get_all_gps_data():
    return gps_data

@app.get("/api/gps/status")
async def get_gps_status():
    return {
        "total_vests": 3,
        "total_players": len(gps_data),
        "status": "fundraising",
        "message": "GPS tracking starting June 2026",
        "players_ready": gps_data,
        "next_session": "First tracking session - June 2026"
    }

# ============================================
# API ROUTES - SCOUT SCORE
# ============================================
@app.get("/api/scout-score/{player_id}")
async def scout_score(player_id: int):
    player = next((p for p in players if int(p["id"]) == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    goals = int(player.get("goals", 0))
    assists = int(player.get("assists", 0))
    appearances = int(player.get("appearances", 0))
    rating = float(player.get("player_rating", 0))
    
    # Calculate scout score out of 100
    score = 0
    if appearances > 0:
        goals_per_game = goals / appearances
        assists_per_game = assists / appearances
        score += min(goals_per_game * 30, 30)
        score += min(assists_per_game * 20, 20)
        score += min((appearances / 20) * 20, 20)
    score += min((rating / 10) * 30, 30)
    scout_score = round(score)
    
    if scout_score >= 70:
        label = "⭐ HIGH POTENTIAL"
        recommendation = "Strong candidate for scouting. Consistent performer with notable output."
    elif scout_score >= 45:
        label = "📈 DEVELOPING TALENT"
        recommendation = "Shows promise. Monitor over next 5 matches for full assessment."
    else:
        label = "🔍 NEEDS MORE DATA"
        recommendation = "Limited data available. More appearances needed for accurate evaluation."
    
    return {
        "player_id": player_id,
        "player_name": player["name"],
        "scout_score": scout_score,
        "score_label": label,
        "recommendation": recommendation,
        "breakdown": {
            "goals_contribution": round(min((goals / max(appearances, 1)) * 30, 30), 1),
            "assists_contribution": round(min((assists / max(appearances, 1)) * 20, 20), 1),
            "appearances_contribution": round(min((appearances / 20) * 20, 20), 1),
            "rating_contribution": round(min((rating / 10) * 30, 30), 1)
        }
    }

# ============================================
# API ROUTES - COMPARE
# ============================================
@app.get("/api/compare")
async def compare_players(player1: Optional[int] = None, player2: Optional[int] = None):
    if not player1 or not player2:
        raise HTTPException(status_code=400, detail="Please provide player1 and player2 query params")
    
    p1 = next((p for p in players if int(p["id"]) == player1), None)
    p2 = next((p for p in players if int(p["id"]) == player2), None)
    
    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="One or both players not found")
    
    all_teams = premier_teams + nsl_teams + division_one_zone_a + division_one_zone_b
    team1 = next((t for t in all_teams if int(t["id"]) == int(p1.get("team_id", 0))), {"name": "Unknown"})
    team2 = next((t for t in all_teams if int(t["id"]) == int(p2.get("team_id", 0))), {"name": "Unknown"})
    gps1 = next((g for g in gps_data if int(g["player_id"]) == player1), None)
    gps2 = next((g for g in gps_data if int(g["player_id"]) == player2), None)
    
    return {
        "comparison": {
            "player1": {
                "id": p1["id"],
                "name": p1["name"],
                "position": p1.get("position", ""),
                "team": team1["name"],
                "goals": int(p1.get("goals", 0)),
                "assists": int(p1.get("assists", 0)),
                "appearances": int(p1.get("appearances", 0)),
                "rating": float(p1.get("player_rating", 0)),
                "top_speed": gps1["max_speed_kmh"] if gps1 else "N/A",
                "distance": gps1["total_distance_km"] if gps1 else "N/A"
            },
            "player2": {
                "id": p2["id"],
                "name": p2["name"],
                "position": p2.get("position", ""),
                "team": team2["name"],
                "goals": int(p2.get("goals", 0)),
                "assists": int(p2.get("assists", 0)),
                "appearances": int(p2.get("appearances", 0)),
                "rating": float(p2.get("player_rating", 0)),
                "top_speed": gps2["max_speed_kmh"] if gps2 else "N/A",
                "distance": gps2["total_distance_km"] if gps2 else "N/A"
            }
        }
    }

# ============================================
# API ROUTES - API KEY GENERATION
# ============================================
@app.post("/api/generate-key")
async def generate_api_key(data: APIKeyGenerate):
    if not data.email or '@' not in data.email:
        raise HTTPException(status_code=400, detail="Valid email required")
    
    if data.tier not in ['standard', 'pro']:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    # Check if email already has a key
    for key, info in api_keys.items():
        if info['email'] == data.email:
            return {
                "success": True,
                "api_key": key,
                "tier": info['tier'],
                "message": "Existing key returned"
            }
    
    new_key = f"goc_{data.tier}_{secrets.token_hex(16)}"
    api_keys[new_key] = {
        "email": data.email,
        "tier": data.tier,
        "created_at": datetime.now().isoformat(),
        "requests": 0
    }
    return {
        "success": True,
        "api_key": new_key,
        "tier": data.tier,
        "email": data.email,
        "message": f"API key generated for {data.tier} plan"
    }

@app.get("/api/keys")
async def list_keys(_: None = Depends(verify_admin)):
  return {"total_keys": len(api_keys), "keys": list(api_keys.keys())}
# ============================================
# ADMIN - EXPORT DATA
# ============================================
@app.get("/admin/export-players-csv")
async def export_players_csv(_: None = Depends(verify_admin)):
    if not players:
        raise HTTPException(status_code=404, detail="No players data available")
    
    fieldnames = ['id', 'name', 'position', 'league', 'team_id', 'goals', 'assists', 'appearances', 'player_rating']
    
    output = []
    output.append(','.join(fieldnames))
    for player in players:
        row = [str(player.get(field, '')) for field in fieldnames]
        output.append(','.join(row))
    
    csv_content = '\n'.join(output)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=players_{datetime.now().strftime('%Y%m%d')}.csv"}
    
    )


# ============================================
# RUN SERVER
# ============================================
import os

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
