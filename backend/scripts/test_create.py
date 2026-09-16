import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, event
from app.db.session import Base
import app.db.models

db_file = "C:/Users/charmi/AppData/Local/Temp/talkwiseai.db"

if os.path.exists(db_file):
    try:
        os.remove(db_file)
    except Exception:
        pass

engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=OFF")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA page_size=65536")
    cursor.execute("PRAGMA max_page_count=2147483646")
    cursor.close()

Base.metadata.create_all(engine)
print("SUCCESS: Tables created on", db_file)
