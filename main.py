import os
import uuid
from fastapi import UploadFile, File
from fastapi import FastAPI
from pydantic import BaseModel
from ai.agent import run_agent
from models import User as UserModel, Ticket as TicketModel, AuditLog
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from authorization import (
    require_permission as authorization_require_permission,
    require_same_department as authorization_require_same_department
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_db, create_tables
from authorization import can_access_ticket, ROLE_PERMISSIONS
from contextlib import asynccontextmanager
from security import (
    verify_password,
    create_access_token,
    verify_access_token
)

security= HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

UPLOAD_DIR = "data/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(lifespan= lifespan)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    status: str

class LoginRequest(BaseModel):
    username:str
    password: str

class AssignTicketRequest(BaseModel):
    assignee_username: str

class TicketCreate(BaseModel):
    title: str
    description: str

class TicketStatusRequest(BaseModel):
    status: str 

class AIChatRequest(BaseModel):
    message: str

class User(BaseModel):
    username: str
    role: str
    department:str

test_user= User(
    username= "employee01",
    role= "employee",
    department= "sales"
)

@app.get("/")
def root():
    return {"message": "Enterprise AI Operations Agent is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/login")
def login(request: LoginRequest,db: Session= Depends(get_db)):
    user= db.query(UserModel).filter(
        UserModel.username == request.username
    ).first()
    if user is None:
       raise HTTPException(
           status_code= 401,
           detail= "Invalid username or password"
       )
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code= 401,
            detail= "Invalid username or password"
        )
    access_token = create_access_token({
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "department": user.department
    })

    return {
        "access_token": access_token,
        "toekn_type": "bearer"
    }

def get_current_user(
        credentials: HTTPAuthorizationCredentials= Depends(security)
):
    token= credentials.credentials

    try:
        payload= verify_access_token(token)

    except Exception:
        raise HTTPException(
            status_code= 401,
            detail= "Invalid or expired token"
        )
    return payload

@app.get("/profile")
def profile(current_user: dict= Depends(get_current_user)):
    return {
        "username": current_user["sub"],
        "role": current_user["role"],
        "department": current_user["department"]
    }

@app.get("/admin")
def admin_dashboard(
    current_user: dict= Depends(
        authorization_require_permission("user:manage", get_current_user)
    )
):
    return {
        "message": "welcome to the admin dashboard",
        "username": current_user["sub"],
        "role": current_user["role"]

    }

@app.get("/tickets")
def get_tickets(
    current_user: dict= Depends(get_current_user),
    db: Session= Depends(get_db)
):
    user = db.query(UserModel).filter(
        UserModel.username == current_user["sub"]
    ).first()
    
    if current_user["role"] == "admin":
        tickets = db.query(TicketModel).all()

    elif current_user["role"] == "manager":
        tickets = db.query(TicketModel).filter(
            TicketModel.department == user.department
        ).all()

    else:
        tickets = db.query(TicketModel).filter(
            TicketModel.owner_id == user.id
        ).all()

    return {
        "username": current_user["sub"],
        "role": current_user["role"],
        "tickets": [
            {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "owner_id": ticket.owner_id,
                "department": ticket.department

            }
            for ticket in tickets
        ]
    }

@app.post("/chat")
def chat(
    request: AIChatRequest,
    current_user: dict = Depends(get_current_user)
):
    print("CHAT ENDPOINT HIT")
    print("MESSAGE:", request.message)
    print("USER:", current_user)

    response = run_agent(
        request.message,
        current_user
    )

    print("AGENT RESPONSE:", response)

    return {
        "username": current_user["sub"],
        "response": response
    }

@app.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: int,
    current_user:dict= Depends(get_current_user),
    db: Session= Depends(get_db)
):
    ticket= db.query(TicketModel).filter(
        TicketModel.id== ticket_id
    ).first()

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail= "Ticket not found"
        )

    if not can_access_ticket(current_user, ticket):
        raise HTTPException(
            status_code=403,
            detail= "You are not authorized to access this ticket"
        )

    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "owner_id": ticket.owner_id,
        "department": ticket.department
    }

@app.post("/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    request: AssignTicketRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(TicketModel).filter(
        TicketModel.id == ticket_id
    ).first()

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )
    
    assignee = db.query(UserModel).filter(
        UserModel.username == request.assignee_username
    ).first()

    if assignee is None:
        raise HTTPException(
            status_code=404,
            detail="Assignee not found"
        )

    permission = ROLE_PERMISSIONS.get(
        current_user.get("role"),
        set()
    )

    if "ticket:assign" not in permission:
        raise HTTPException(
            status_code=403,
            detail="Permission required: ticket:assign"
        )

    if current_user.get("role") != "admin":
        if current_user.get("department") != ticket.department:
            raise HTTPException(
                status_code=403,
                detail="Access restricted to your department"
            )
    if current_user.get("role") != "admin":
        if assignee.department != ticket.department:
            raise HTTPException(
                status_code=403,
                detail="Assignee must belong to the ticket department"
            )
        
    ticket.assignee_id= assignee.id

    db.commit()
    db.refresh(ticket)

    return {
        "message": "Ticket assigned successfully",
        "ticket": ticket.id,
        "assignee": assignee.username,
        "department": ticket.department
    }

@app.delete("/tickets/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(TicketModel).filter(
        TicketModel.id == ticket_id
    ).first()

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    permission = ROLE_PERMISSIONS.get(
        current_user.get("role"),
        set()
    )

    if "ticket:delete" not in permission:
        raise HTTPException(
            status_code=403,
            detail="Permission required: ticket:delete"
        )

    db.delete(ticket)
    db.commit()

    return {
        "message": "Ticket deleted successfully",
        "ticket": ticket_id
    }

@app.delete("/tickets/{ticket_id}/assignee")
def unassign_ticket(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(TicketModel).filter(
        TicketModel.id == ticket_id
    ).first()

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    permission = ROLE_PERMISSIONS.get(
        current_user.get("role"),
        set()
    )

    if "ticket:assign" not in permission:
        raise HTTPException(
            status_code=403,
            detail="Permission required: ticket:assign"
        )

    if current_user.get("role") != "admin":
        if current_user.get("department") != ticket.department:
            raise HTTPException(
                status_code=403,
                detail="Access restricted to your department"
            )
    ticket.assignee_id = None

    db.commit()
    db.refresh(ticket)

    return {
        "message": "Ticket unassigned successfully",
        "ticket": ticket.id,
        "department": ticket.department
    }
@app.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    request: TicketStatusRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Find the ticket
    ticket = db.query(TicketModel).filter(
        TicketModel.id == ticket_id
    ).first()

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    # 2. Find the authenticated user from the database
    user = db.query(UserModel).filter(
        UserModel.username == current_user["sub"]
    ).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # 3. Check permission
    permission = ROLE_PERMISSIONS.get(
        current_user.get("role"),
        set()
    )

    if "ticket:update_status" not in permission:
        raise HTTPException(
            status_code=403,
            detail="Permission required: ticket:update_status"
        )

    # 4. Department restriction
    if current_user.get("role") != "admin":
        if current_user.get("department") != ticket.department:
            raise HTTPException(
                status_code=403,
                detail="Access restricted to your department"
            )

    # 5. Validate status value
    allowed_statuses = {
        "open",
        "in_progress",
        "resolved",
        "closed"
    }

    if request.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket status"
        )

    # 6. Validate status transition
    allowed_transitions = {
        "open": {"in_progress"},
        "in_progress": {"resolved"},
        "resolved": {"closed"},
        "closed": set()
    }

    if request.status not in allowed_transitions[ticket.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition: "
                   f"{ticket.status} -> {request.status}"
        )

    # 7. Remember the old status
    previous_status = ticket.status

    # 8. Update the ticket
    ticket.status = request.status

    # 9. Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        action="status_update",
        ticket_id=ticket.id,
        previous_value=previous_status,
        new_value=ticket.status
    )

    # 10. Save both changes in the same transaction
    db.add(audit_log)
    print(
        "AUDIT DEBUG:",
        audit_log.user_id,
        audit_log.action,
        audit_log.ticket_id,
        audit_log.previous_value,
        audit_log.new_value
    )
    db.commit()

    # 11. Refresh ticket from database
    db.refresh(ticket)

    return {
        "message": "Ticket status updated successfully",
        "ticket": ticket.id,
        "previous_status": previous_status,
        "status": ticket.status
    }

@app.get("/users")
def get_users(
    current_user: dict = Depends(
        authorization_require_permission("user:manage", get_current_user)
    )
):
    return {
        "message": "User management access granted",
        "username": current_user["sub"],
        "role": current_user["role"]
    }

def department_access(
    department: str,
    current_user: dict = Depends(get_current_user)
):
    return authorization_require_same_department(
        department,
        current_user
    )

@app.get("/department/{department}")
def get_department(
    department: str,
    current_user: dict = Depends(department_access)
):
    return {
        "message": "Department access granted",
        "username": current_user["sub"],
        "department": department
    }


@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )

    user_id = current_user["user_id"]

    user_upload_dir = os.path.join(
        UPLOAD_DIR,
        f"user_{user_id}"
    )

    os.makedirs(
        user_upload_dir,
        exist_ok=True
    )

    safe_filename = f"{uuid.uuid4()}.csv"

    file_path = os.path.join(
        user_upload_dir,
        safe_filename
    )

    contents = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    return {
        "message": "CSV uploaded successfully",
        "original_filename": file.filename,
        "stored_filename": safe_filename,
        "path": file_path
    }