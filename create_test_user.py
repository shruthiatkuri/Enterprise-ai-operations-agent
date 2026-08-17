from database import SessionLocal
from models import User
from security import hash_password

db= SessionLocal()

user= User(
    username= "manager01",
    password_hash= hash_password("test123"),
    role= "manager",
    department= "sales"
)

db.add(user)
db.commit()

print("manager01 created successfully")

db.close()