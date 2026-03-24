import sys; from app import app; from models import db, Apartment; from scraper import scrape_apartment_details; a = Apartment.query.get(int(sys.argv[1])); print('Scraping', a.id); ctx=app.app_context(); ctx.push(); success, data = scrape_apartment_details(a.original_url); 
if success:
 a.title = data.get('title'); a.current_price=data.get('price'); a.room_count=data.get('room_count'); a.size_sqm=data.get('size_sqm'); a.is_available=True; db.session.commit(); print('OK')
else: print('FAIL')
