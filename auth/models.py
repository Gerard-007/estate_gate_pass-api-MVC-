from datetime import datetime
from mongoengine import Document, StringField, IntField, BooleanField, DateTimeField


class User(Document):
    fullname = StringField(required=True)
    email = StringField(required=True, unique=True)
    phone = StringField(required=True, max_length=11)
    status = StringField(default="Resident", choices=["Resident", "Admin", "Security"])
    password = StringField(required=False)
    is_active = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now())
