from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from supabase import create_client, Client
import bcrypt
from jose import jwt, JWTError
import os

# Import secure configuration
from secure_config import SUPABASE_CONFIG, JWT_CONFIG, SERVER_CONFIG, CORS_ORIGINS, DEMO_ACCOUNTS

# Configuration
SUPABASE_URL = SUPABASE_CONFIG["url"]
SUPABASE_KEY = SUPABASE_CONFIG["anon_key"]
JWT_SECRET = JWT_CONFIG["secret"]
JWT_ALGORITHM = JWT_CONFIG["algorithm"]

# Initialize FastAPI app
app = FastAPI(
    title="Scout Accelerator API",
    description="Backend API for Scout Accelerator platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Security
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str  # 'scout' or 'scoutmaster'
    troop_code: Optional[str] = None
    troop_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenData(BaseModel):
    user_id: str
    email: str
    role: str

# Request body models
class SignoffRequestBody(BaseModel):
    requirement_id: str

class ConferenceRequestBody(BaseModel):
    conference_type: str
    rank: str

class ApproveSignoffBody(BaseModel):
    signoff_id: str

class RejectSignoffBody(BaseModel):
    signoff_id: str
    reason: Optional[str] = None

class ScheduleConferenceBody(BaseModel):
    conference_id: str
    scheduled_date: str

class UpdateMemberBody(BaseModel):
    member_id: str
    updates: dict

class RemoveMemberBody(BaseModel):
    member_id: str

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(user_id=user_id, email=payload.get("email", ""), role=payload.get("role", ""))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ------------------------------------------------------------
# Static Frontend Serving
# ------------------------------------------------------------
# We serve the static HTML/CSS/JS files located in the ../frontend
# directory (relative to this backend folder). Mounting at the root
# path allows paths like "/css/style.css" or "/signin.html" to work
# exactly as they are written in the HTML templates.

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Resolve absolute path to the frontend folder
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

# Mount *after* all API routes but *before* any conflicting catch-alls
# so that API endpoints still take precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# Optional: expose the old JSON root at /api for quick health checks
@app.get("/api")
async def api_root():
    return {"message": "Scout Accelerator API is running!"}

@app.post("/auth/signup")
async def signup(user_data: UserCreate):
    try:
        # Check if user already exists
        existing_user = supabase.table('users').select('*').eq('email', user_data.email).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="User already exists")

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Handle role-specific logic
        if user_data.role == 'scoutmaster':
            if user_data.troop_code:
                # Joining existing troop
                troop = supabase.table('troops').select('*').eq('code', user_data.troop_code).execute()
                if not troop.data:
                    raise HTTPException(status_code=400, detail="Troop not found")
                troop_id = troop.data[0]['id']
            else:
                # Creating new troop
                import random
                troop_code = f"{user_data.troop_name.replace(' ', '').upper()[:3]}{random.randint(100, 999):03d}"
                new_troop = supabase.table('troops').insert({
                    'name': user_data.troop_name,
                    'code': troop_code,
                    'created_by': None,  # Will update after user creation
                    'eligible_signoff_rank': 'first_class'  # Default value
                }).execute()
                troop_id = new_troop.data[0]['id']
        else:
            # Scout joining troop
            troop = supabase.table('troops').select('*').eq('code', user_data.troop_code).execute()
            if not troop.data:
                raise HTTPException(status_code=400, detail="Troop not found")
            troop_id = troop.data[0]['id']

        # Create user
        new_user = supabase.table('users').insert({
            'full_name': user_data.full_name,
            'email': user_data.email,
            'password': hashed_password,
            'role': user_data.role,
            'troop_id': troop_id,
            'current_rank': 'unranked',
            'eligible_signoff_rank': 'first_class',
            'is_spl': False,
            'is_patrol_leader': False
        }).execute()

        user = new_user.data[0]

        # Update troop created_by if scoutmaster created troop
        if user_data.role == 'scoutmaster' and not user_data.troop_code:
            supabase.table('troops').update({'created_by': user['id']}).eq('id', troop_id).execute()

        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user['id'], "email": user['email'], "role": user['role']},
            expires_delta=access_token_expires
        )

        return {
            "message": "User created successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "full_name": user['full_name'],
                "email": user['email'],
                "role": user['role'],
                "troop_code": user_data.troop_code or troop_code
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(user_credentials: UserLogin):
    try:
        # Get user from database
        user_result = supabase.table('users').select('*').eq('email', user_credentials.email).execute()

        if not user_result.data:
            raise HTTPException(status_code=400, detail="Invalid email or password")

        user = user_result.data[0]

        # Verify password
        if not verify_password(user_credentials.password, user['password']):
            raise HTTPException(status_code=400, detail="Invalid email or password")

        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user['id'], "email": user['email'], "role": user['role']},
            expires_delta=access_token_expires
        )

        # Get troop info
        troop = supabase.table('troops').select('code, name').eq('id', user['troop_id']).execute()

        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "full_name": user['full_name'],
                "email": user['email'],
                "role": user['role'],
                "troop_code": troop.data[0]['code'] if troop.data else None,
                "troop_name": troop.data[0]['name'] if troop.data else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/dashboard/scout")
async def get_scout_dashboard(current_user: TokenData = Depends(get_current_user)):
    try:
        # Get user data with troop info
        user_data = supabase.table('users').select('*, troops!inner(name, code)').eq('id', current_user.user_id).execute()

        if not user_data.data:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_data.data[0]

        # Get requirements progress
        requirements = supabase.table('requirements').select('id, rank, description').eq('rank', user['current_rank']).execute()

        completed_requirements = supabase.table('user_requirements').select('requirement_id').eq('user_id', current_user.user_id).eq('completed_at', 'not.is', 'null').execute()

        completed_count = len(completed_requirements.data) if completed_requirements.data else 0
        total_count = len(requirements.data) if requirements.data else 0

        # Get ranks completed count
        ranks_query = supabase.table('requirements').select('rank').distinct().execute()
        all_ranks = [r['rank'] for r in ranks_query.data]
        ranks_completed = all_ranks.index(user['current_rank']) if user['current_rank'] in all_ranks else 0

        # Get recent activity
        recent_activity = supabase.table('signoff_requests').select('*, requirements!inner(description)').eq('user_id', current_user.user_id).order('created_at', desc=True).limit(3).execute()

        return {
            "user": {
                "name": user['full_name'],
                "troop_number": user['troops']['code'],
                "current_rank": user['current_rank'],
                "completed_requirements": completed_count,
                "total_requirements": total_count,
                "ranks_completed": ranks_completed,
                "eagle_progress": round((ranks_completed / len(all_ranks)) * 100, 1)
            },
            "recent_activity": [
                {
                    "type": "signoff_request" if activity['status'] == 'pending' else "signoff_approved",
                    "title": "Sign-off Request Pending" if activity['status'] == 'pending' else "Sign-off Approved",
                    "description": activity['requirements']['description'][:50] + "...",
                    "time": "Recently"
                } for activity in recent_activity.data
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/dashboard/scoutmaster")
async def get_scoutmaster_dashboard(current_user: TokenData = Depends(get_current_user)):
    try:
        # Get troop info
        troop_data = supabase.table('troops').select('*').eq('created_by', current_user.user_id).execute()

        if not troop_data.data:
            raise HTTPException(status_code=404, detail="Troop not found")

        troop = troop_data.data[0]

        # Get scoutmaster name
        scoutmaster = supabase.table('users').select('full_name').eq('id', current_user.user_id).execute()

        # Get troop members
        members = supabase.table('users').select('id, full_name, role, current_rank, is_spl, is_patrol_leader').eq('troop_id', troop['id']).execute()

        # Get pending signoffs
        pending_signoffs = supabase.table('signoff_requests').select('*, users!inner(full_name), requirements!inner(description, rank)').eq('status', 'pending').eq('handled_by_id', current_user.user_id).execute()

        # Get conference requests
        conferences = supabase.table('conferences').select('*, users!inner(full_name)').eq('status', 'pending').eq('handled_by_id', current_user.user_id).execute()

        # Get patrol count (create table if it doesn't exist)
        try:
            patrol_count = supabase.table('patrols').select('id', count='exact').eq('troop_id', troop['id']).execute()
        except Exception:
            patrol_count = {'count': 0}  # Default to 0 if table doesn't exist

        return {
            "troop": {
                "name": troop['name'],
                "code": troop['code'],
                "created_by_name": scoutmaster.data[0]['full_name'] if scoutmaster.data else 'Scoutmaster',
                "eligible_signoff_rank": troop.get('eligible_signoff_rank', 'first_class')
            },
            "stats": {
                "total_scouts": len([m for m in members.data if m['role'] == 'scout']) if members.data else 0,
                "active_patrols": patrol_count.get('count', 0),
                "pending_signoffs": len(pending_signoffs.data) if pending_signoffs.data else 0,
                "upcoming_events": 0  # TODO: Implement events
            },
            "pending_signoffs": [
                {
                    "id": signoff['id'],
                    "scout": signoff['users']['full_name'],
                    "requirement": signoff['requirements']['description'],
                    "rank": signoff['requirements']['rank'],
                    "time": "Recently"
                } for signoff in (pending_signoffs.data[:5] if pending_signoffs.data else [])
            ],
            "conference_requests": [
                {
                    "id": conf['id'],
                    "scout": conf['users']['full_name'],
                    "type": conf['type'],
                    "rank": conf['rank'],
                    "status": conf['status']
                } for conf in (conferences.data[:5] if conferences.data else [])
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/requirements/{rank}")
async def get_requirements_by_rank(rank: str, current_user: TokenData = Depends(get_current_user)):
    try:
        # Get requirements for the rank
        requirements = supabase.table('requirements').select('*').eq('rank', rank).order('order_num').execute()

        # Get user's completed requirements
        completed = supabase.table('user_requirements').select('requirement_id').eq('user_id', current_user.user_id).eq('completed_at', 'not.is', 'null').execute()

        completed_ids = [c['requirement_id'] for c in completed.data] if completed.data else []

        # Format requirements
        formatted_requirements = []
        for req in requirements.data:
            formatted_requirements.append({
                "id": req['id'],
                "description": req['description'],
                "lesson": req['lesson'],
                "order_num": req['order_num'],
                "completed": req['id'] in completed_ids
            })

        return {
            "rank": rank,
            "requirements": formatted_requirements
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/signoff-request")
async def create_signoff_request(body: SignoffRequestBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Check if request already exists
        existing = supabase.table('signoff_requests').select('*').eq('user_id', current_user.user_id).eq('requirement_id', body.requirement_id).eq('status', 'pending').execute()

        if existing.data:
            raise HTTPException(status_code=400, detail="Sign-off request already pending")

        # Get requirement info to find appropriate handler
        requirement = supabase.table('requirements').select('*').eq('id', body.requirement_id).execute()

        if not requirement.data:
            raise HTTPException(status_code=404, detail="Requirement not found")

        # Get user's troop info
        user_troop = supabase.table('users').select('troop_id, troops!inner(eligible_signoff_rank)').eq('id', current_user.user_id).execute()

        if not user_troop.data:
            raise HTTPException(status_code=404, detail="User troop not found")

        # Find eligible scoutmaster or patrol leader
        eligible_rank = user_troop.data[0]['troops']['eligible_signoff_rank']
        eligible_handlers = supabase.table('users').select('id').eq('troop_id', user_troop.data[0]['troop_id']).or_('role.eq.scoutmaster,is_spl.eq.true,is_patrol_leader.eq.true').execute()

        if not eligible_handlers.data:
            raise HTTPException(status_code=400, detail="No eligible sign-off handlers found")

        # Create signoff request
        new_request = supabase.table('signoff_requests').insert({
            'user_id': current_user.user_id,
            'requirement_id': body.requirement_id,
            'status': 'pending',
            'handled_by_id': eligible_handlers.data[0]['id']
        }).execute()

        return {
            "message": "Sign-off request created successfully",
            "request_id": new_request.data[0]['id']
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/conference-request")
async def create_conference_request(body: ConferenceRequestBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Get user's troop scoutmasters
        user_troop = supabase.table('users').select('troop_id').eq('id', current_user.user_id).execute()

        scoutmasters = supabase.table('users').select('id').eq('troop_id', user_troop.data[0]['troop_id']).eq('role', 'scoutmaster').execute()

        if not scoutmasters.data:
            raise HTTPException(status_code=400, detail="No scoutmasters available")

        # Create conference request
        new_conference = supabase.table('conferences').insert({
            'user_id': current_user.user_id,
            'type': body.conference_type,
            'rank': body.rank,
            'status': 'pending',
            'handled_by_id': scoutmasters.data[0]['id']
        }).execute()

        return {
            "message": f"{body.conference_type.replace('_', ' ').title()} request created successfully",
            "conference_id": new_conference.data[0]['id']
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Troop Management Endpoints
@app.post("/troop/approve-signoff")
async def approve_signoff(body: ApproveSignoffBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Get signoff request
        signoff = supabase.table('signoff_requests').select('*, requirements!inner(*)').eq('id', body.signoff_id).eq('handled_by_id', current_user.user_id).execute()

        if not signoff.data:
            raise HTTPException(status_code=404, detail="Sign-off request not found")

        signoff_data = signoff.data[0]

        # Update signoff status
        supabase.table('signoff_requests').update({'status': 'approved'}).eq('id', body.signoff_id).execute()

        # Mark requirement as completed
        supabase.table('user_requirements').insert({
            'user_id': signoff_data['user_id'],
            'requirement_id': signoff_data['requirement_id'],
            'completed_at': datetime.utcnow().isoformat()
        }).execute()

        return {"message": "Sign-off approved successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/troop/reject-signoff")
async def reject_signoff(body: RejectSignoffBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Update signoff status
        supabase.table('signoff_requests').update({'status': 'rejected'}).eq('id', body.signoff_id).execute()

        return {"message": "Sign-off rejected"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/troop/schedule-conference")
async def schedule_conference(body: ScheduleConferenceBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Update conference status
        supabase.table('conferences').update({
            'status': 'scheduled',
            'scheduled_date': body.scheduled_date
        }).eq('id', body.conference_id).eq('handled_by_id', current_user.user_id).execute()

        return {"message": "Conference scheduled successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/troop/members")
async def get_troop_members(current_user: TokenData = Depends(get_current_user)):
    try:
        # Get user's troop
        user_troop = supabase.table('users').select('troop_id').eq('id', current_user.user_id).execute()

        if not user_troop.data:
            raise HTTPException(status_code=404, detail="User troop not found")

        # Get all members
        members = supabase.table('users').select('id, full_name, email, role, current_rank, is_spl, is_patrol_leader').eq('troop_id', user_troop.data[0]['troop_id']).execute()

        return {"members": members.data or []}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/troop/update-member")
async def update_member(body: UpdateMemberBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Verify user has permission (is scoutmaster of the troop)
        user_troop = supabase.table('users').select('troop_id').eq('id', current_user.user_id).execute()
        member_troop = supabase.table('users').select('troop_id').eq('id', body.member_id).execute()

        if not user_troop.data or not member_troop.data or user_troop.data[0]['troop_id'] != member_troop.data[0]['troop_id']:
            raise HTTPException(status_code=403, detail="Permission denied")

        # Update member
        supabase.table('users').update(body.updates).eq('id', body.member_id).execute()

        return {"message": "Member updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/troop/remove-member")
async def remove_member(body: RemoveMemberBody, current_user: TokenData = Depends(get_current_user)):
    try:
        # Verify user has permission (is scoutmaster of the troop)
        user_troop = supabase.table('users').select('troop_id').eq('id', current_user.user_id).execute()
        member_troop = supabase.table('users').select('troop_id').eq('id', body.member_id).execute()

        if not user_troop.data or not member_troop.data or user_troop.data[0]['troop_id'] != member_troop.data[0]['troop_id']:
            raise HTTPException(status_code=403, detail="Permission denied")

        # Remove member (set troop_id to null)
        supabase.table('users').update({'troop_id': None}).eq('id', body.member_id).execute()

        return {"message": "Member removed from troop"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
        reload=SERVER_CONFIG["debug"]
    )
