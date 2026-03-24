import json
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Apartment, PriceHistory
from scraper import scrape_apartment_details

app = Flask(__name__)

# Register a custom Jinja filter to parse JSON strings
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value)
    except:
        return []

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apartments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super_secret_key' # In production, use os.urandom or a .env file

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    apartments = Apartment.query.order_by(Apartment.date_added.desc()).all()
    return render_template('index.html', apartments=apartments)

@app.route('/apartment/<int:apt_id>')
def apartment_detail(apt_id):
    apt = Apartment.query.get_or_404(apt_id)
    return render_template('detail.html', apt=apt)

@app.route('/add', methods=['POST'])
def add_apartment():
    urls_text = request.form.get('url')
    if not urls_text:
        flash('Please provide at least one URL.', 'error')
        return redirect(url_for('index'))

    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    if not urls:
        flash('Please provide valid URLs.', 'error')
        return redirect(url_for('index'))

    added_count = 0
    new_urls = []
    
    for url in urls:
        existing = Apartment.query.filter_by(original_url=url).first()
        if existing:
            continue
        new_apt = Apartment(original_url=url)
        db.session.add(new_apt)
        added_count += 1
        new_urls.append(url)
    
    db.session.commit()

    if added_count == 0:
        flash('No new apartments were added (they might already exist).', 'info')
        return redirect(url_for('index'))

    flash(f'{added_count} apartment(s) added! Scraping details in background...', 'success')

    from threading import Thread
    def scrape_new_urls(urls_to_scrape):
        with app.app_context():
            for u in urls_to_scrape:
                apt = Apartment.query.filter_by(original_url=u).first()
                if apt:
                    success, data = scrape_apartment_details(u)
                    if success:
                        update_apartment_with_data(apt, data)
                    elif data.get('blocked'):
                        apt.title = 'Blocked by anti-bot challenge (open manually)'
                        apt.resolved_url = data.get('resolved_url', apt.resolved_url)
                        db.session.commit()
    
    Thread(target=scrape_new_urls, args=(new_urls,)).start()

@app.route('/refresh/<int:apt_id>')
def refresh_apartment(apt_id):
    apt = Apartment.query.get_or_404(apt_id)
    success, data = scrape_apartment_details(apt.original_url)
    if success:
        update_apartment_with_data(apt, data)
        flash(f'Refreshed details for {apt.original_url}', 'success')
    else:
        if data.get('blocked'):
            apt.title = apt.title or 'Blocked by anti-bot challenge (open manually)'
            apt.resolved_url = data.get('resolved_url', apt.resolved_url)
            db.session.commit()
            flash('Source website blocked automated scraping for this listing. You can still open it manually.', 'warning')
            return redirect(url_for('index'))

        # Check if the error indicates unavailability
        if data.get('unavailable'):
            apt.is_available = False
            db.session.commit()
            flash(f'Apartment seems to be unavailable now.', 'warning')
        else:
            flash(f'Failed to refresh: {data.get("error")}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete/<int:apt_id>', methods=['POST'])
def delete_apartment(apt_id):
    apt = Apartment.query.get_or_404(apt_id)
    db.session.delete(apt)
    db.session.commit()
    flash('Apartment removed from tracking list.', 'success')
    return redirect(url_for('index'))

def update_apartment_with_data(apt, data):
    # Track price history if changed
    current_price = data.get('price')
    if current_price and current_price != apt.current_price:
        history = PriceHistory(apartment_id=apt.id, price=current_price)
        db.session.add(history)
        apt.current_price = current_price

    apt.title = data.get('title', apt.title)
    apt.room_count = data.get('room_count', apt.room_count)
    apt.size_sqm = data.get('size_sqm', apt.size_sqm)
    apt.location = data.get('location', apt.location)
    apt.picture_url = data.get('picture_url', apt.picture_url)
    apt.is_available = True # If scraped successfully, it must be available
    
    if data.get('price'):
        apt.listing_type = 'rent' if data.get('price') < 10000 else 'buy'
    
    # Store the resolved URL if provided by scraper (e.g., following redirects from Rheinpfalz to Immowelt)
    apt.resolved_url = data.get('resolved_url', apt.resolved_url)

    db.session.commit()

from apscheduler.schedulers.background import BackgroundScheduler

def update_all_apartments():
    with app.app_context():
        apartments = Apartment.query.all()
        for apt in apartments:
            try:
                success, data = scrape_apartment_details(apt.original_url)
                if success:
                    update_apartment_with_data(apt, data)
                elif data.get('blocked'):
                    if not apt.title:
                        apt.title = 'Blocked by anti-bot challenge (open manually)'
                    apt.resolved_url = data.get('resolved_url', apt.resolved_url)
                    db.session.commit()
                elif data.get('unavailable'):
                    apt.is_available = False
                    db.session.commit()
            except Exception:
                # Keep processing remaining apartments even if one scrape fails.
                continue

scheduler = BackgroundScheduler()
scheduler.add_job(func=update_all_apartments, trigger="interval", hours=12)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
