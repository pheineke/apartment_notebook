from app import app; from models import db, Apartment; from scraper import scrape_apartment_details
with app.app_context():
    for a in Apartment.query.all():
        if 'immobilienscout24.de' in a.original_url:
            print('Scraping', a.id)
            if 'block' in str(a.title).lower():
                print('Is literally blocked in title')
            success, data = scrape_apartment_details(a.original_url)
            if success:
                a.title = data.get('title')
                a.current_price = data.get('price')
                a.room_count = data.get('room_count')
                a.size_sqm = data.get('size_sqm')
                a.is_available = True
                db.session.commit()
                print('SUCCESS')
            else: print('FAIL', data)
