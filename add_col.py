from app import app; from models import db; import sqlite3; 
with sqlite3.connect('instance/apartments.db') as conn:
    try: conn.execute('ALTER TABLE apartment ADD COLUMN other_links TEXT'); print('Column added');
    except Exception as e: print(e)
