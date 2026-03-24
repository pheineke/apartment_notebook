from app import app; from models import db, Apartment; from collections import defaultdict
with app.app_context():
 apts=Apartment.query.all()
 dupes=defaultdict(list)
 for a in apts: dupes[(a.current_price, a.size_sqm, a.room_count)].append(a)
 print('Duplicates:')
 for k,v in dupes.items():
  if len(v)>1:
   print(f'Match: Price={k[0]}, Size={k[1]}, Rooms={k[2]}')
   for a in v:
    print(f'  ID: {a.id} URL: {a.original_url}')
