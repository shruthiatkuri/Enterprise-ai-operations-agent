from database import SessionLocal
from models import Ticket as TicketModel, User as UserModel, AuditLog
from authorization import can_access_ticket, ROLE_PERMISSIONS
import pandas as pd

TICKET_TOOL = {
    "type": "function",
    "function": {
        "name": "get_ticket_info",
        "description": "Get information about a specific support ticket.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ID of the ticket to retrieve."
                }
            },
            "required": ["ticket_id"]
        }
    }
}

MY_TICKETS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_my_tickets",
        "description": "Get all support tickets belonging to the authenticated user.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

ANALYZE_CSV_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_csv",
        "description": "Analyze a CSV file and return its row count, columns, and statistical summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the CSV file to analyze."
                }
            },
            "required": ["file_path"]
        }
    }
}

COMPARE_CSV_TOOL = {
    "type": "function",
    "function": {
        "name": "compare_csv",
        "description": "Compare two CSV files and return their row counts, columns, and common columns.",
        "parameters": {
            "type": "object",
            "properties": {
                "file1_path": {
                    "type": "string",
                    "description": "Path to the first CSV file."
                },
                "file2_path": {
                    "type": "string",
                    "description": "Path to the second CSV file."
                }
            },
            "required": [
                "file1_path",
                "file2_path"
            ]
        }
    }
}

def get_ticket_info(ticket_id: int, current_user: dict):
    db = SessionLocal()

    try:
        ticket = db.query(TicketModel).filter(
            TicketModel.id == ticket_id
        ).first()

        if ticket is None:
            return {
                "error": "Ticket not found"
            }
        owner = db.query(UserModel).filter(
            UserModel.id == ticket.owner_id
        ).first()


        role = current_user["role"]
        user_id = current_user["user_id"]
        department = current_user["department"]

        if role == "employee":

            if ticket.owner_id != user_id:
                return {
                    "error": "You are not authorized to access this ticket."
                }

        elif role == "manager":

            if ticket.department != department:
                return {
                    "error": "You are not authorized to access this ticket."
                }

        elif role == "admin":

            pass

        else:

            return {
                "error": "Invalid user role."
            }

        return {
            "ticket_id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "department": ticket.department,
            "owner_id": ticket.owner_id,
            "owner_username": owner.username if owner else None
        }
    finally:
        db.close()

def get_my_tickets(owner_id: int): 
    db = SessionLocal() 
    try: 
        tickets = db.query(TicketModel).filter( 
            TicketModel.owner_id == owner_id 
        ).all() 
        return [
            {
                "ticket_id": ticket.id, 
                "title": ticket.title, 
                "status": ticket.status, 
                "department": ticket.department 
            } for ticket in tickets 
        ] 
    finally: 
        db.close()

def update_ticket_status(
    ticket_id: int,
    new_status: str,
    current_user: dict
):
    db = SessionLocal()

    try:
        ticket = db.query(TicketModel).filter(
            TicketModel.id == ticket_id
        ).first()

        if ticket is None:
            return {
                "error": "Ticket not found"
            }

        role = current_user["role"]
        user_id = current_user["user_id"]
        department = current_user["department"]

        permission = ROLE_PERMISSIONS.get(
            role,
            set()
        )

        if "ticket:update_status" not in permission:
            return {
                "error": "Permission required: ticket:update_status"
            }

        if role != "admin":
            if ticket.department != department:
                return {
                    "error": "Access restricted to your department"
                }

        allowed_statuses = {
            "open",
            "in_progress",
            "resolved",
            "closed"
        }

        if new_status not in allowed_statuses:
            return {
                "error": "Invalid ticket status"
            }

        allowed_transitions = {
            "open": {"in_progress"},
            "in_progress": {"resolved"},
            "resolved": {"closed"},
            "closed": set()
        }

        if new_status not in allowed_transitions[ticket.status]:
            return {
                "error": (
                    f"Invalid status transition: "
                    f"{ticket.status} -> {new_status}"
                )
            }

        previous_status = ticket.status
        ticket.status = new_status

        audit_log = AuditLog(
            user_id=user_id,
            action="status_update",
            ticket_id=ticket.id,
            previous_value=previous_status,
            new_value=ticket.status
        )

        db.add(audit_log)

        db.commit()
        db.refresh(ticket)

        return {
            "ticket_id": ticket.id,
            "previous_status": previous_status,
            "status": ticket.status
        }

    finally:
        db.close()
        

UPDATE_STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "update_ticket_status",
        "description": "Update the status of a support ticket.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "The ID of the ticket to update."
                },
                "new_status": {
                    "type": "string",
                    "enum": [
                        "open",
                        "in_progress",
                        "resolved",
                        "closed"
                    ],
                    "description": "The new status for the ticket."
                }
            },
            "required": [
                "ticket_id",
                "new_status"
            ]
        }
    }
}

def analyze_csv(file_path: str):
    df = pd.read_csv(file_path)

    return {
        "rows": len(df),
        "columns": list(df.columns),
        "summary": df.describe(include="all").to_dict()
    }

def compare_csv(file1_path: str, file2_path: str):
    df1 = pd.read_csv(file1_path)
    df2 = pd.read_csv(file2_path)

    return {
        "file1_rows": len(df1),
        "file2_rows": len(df2),
        "file1_columns": list(df1.columns),
        "file2_columns": list(df2.columns),
        "common_columns": list(
            set(df1.columns) & set(df2.columns)
        )
    }