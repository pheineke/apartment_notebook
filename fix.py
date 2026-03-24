from app import app; from models import db, Apartment; from scraper import scrape_apartment_details; ctx=app.app_context(); ctx.push();
import warnings; warnings.filterwarnings('ignore')
apts = Apartment.query.all()
for a in apts:
    # If the item has a 'Blocked' title or if the price is weird (< 10) or Immoscout failed earlier
    if ' blocked' in (a.title or '').lower() or a.title == 'Blocked' or (a.picture_url and 'nopic' in a.picture_url) or a.current_price is None or a.current_price < 20 or not a.location:
        print(f'Updating {a.id}: {a.original_url}')
        success, data = scrape_apartment_details(a.original_url)
        if success:
            a.title = data.get('title')
            a.current_price = data.get('price')
            a.room_count = data.get('room_count')
            a.size_sqm = data.get('size_sqm')
            a.location = data.get('location')
            a.picture_url = data.get('picture_url')
            a.is_available = True
            db.session.commit()
            print('  -> Saved', a.title)
        else:
            print('  -> Failed', data)
