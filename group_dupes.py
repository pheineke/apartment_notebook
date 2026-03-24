from app import app; from models import db, Apartment; import json; from collections import defaultdict
with app.app_context():
 apts=Apartment.query.all()
 dupes=defaultdict(list)
 for a in apts: dupes[(a.current_price, a.size_sqm, a.room_count)].append(a)
 for k,v in dupes.items():
  if len(v)>1:
   # Keep the first one, move the others to other_links
   main_apt = v[0]
   links = []
   if main_apt.other_links:
       try: links = json.loads(main_apt.other_links)
       except: links = []
   for extra in v[1:]:
       links.append(extra.original_url)
       if extra.other_links:
           try:
               for l in json.loads(extra.other_links): links.append(l)
           except: pass
       db.session.delete(extra)
   main_apt.other_links = json.dumps(list(set(links)))
 db.session.commit()
 print('Dupes combined based on price/size/rooms')
