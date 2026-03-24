from app import app; from models import db, Apartment; from scraper import scrape_apartment_details; import os
ctx=app.app_context(); ctx.push(); 
for a in Apartment.query.all():
 if 'blocked' in str(a.title).lower() or a.title == 'None' or a.title == 'Unknown Title' or getattr(a, 'current_price', None) is None:
  print('Scraping', a.id, a.original_url); os.system('taskkill /f /im chrome.exe /t >nul 2>&1'); success, data=scrape_apartment_details(a.original_url);
  if success:
   a.title=data.get('title'); a.current_price=data.get('price'); a.room_count=data.get('room_count'); a.size_sqm=data.get('size_sqm'); a.is_available=True; db.session.commit(); print('OK')
