from app import app; from models import db, Apartment; from collections import defaultdict
with app.app_context():
 apts=Apartment.query.all()
 print('Total:', len(apts))
 for a in apts: a.title = a.title
