from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Apartment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(500), unique=True, nullable=False)
    resolved_url = db.Column(db.String(500), nullable=True) # In case of redirects
    source = db.Column(db.String(50), nullable=True) # e.g., kleinanzeigen, immo24
    title = db.Column(db.String(200), nullable=True)
    current_price = db.Column(db.Float, nullable=True)
    room_count = db.Column(db.Float, nullable=True)
    size_sqm = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    picture_url = db.Column(db.String(500), nullable=True)
    other_links = db.Column(db.Text, nullable=True) # Stored as JSON list of URLs or comma-separated
    listing_type = db.Column(db.String(10), nullable=True) # 'rent' or 'buy'
    is_available = db.Column(db.Boolean, default=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    price_history = db.relationship('PriceHistory', backref='apartment', lazy=True, cascade="all, delete-orphan")

    def get_price_per_sqm(self):
        if self.current_price and self.size_sqm and self.size_sqm > 0:
            return round(self.current_price / self.size_sqm, 2)
        return None
        
    @property
    def clean_location(self):
        if not self.location:
            return 'Unknown'
        import re
        loc = self.location
        loc = loc.replace('Rheinland-Pfalz', '')
        # Remove PLZ (5 digits)
        loc = re.sub(r'\b\d{5}\b', '', loc)
        
        # Extract meaningful parts
        parts = []
        # split by comma, or hyphen if we want, but some have "Kaiserslautern-West" 
        # let's split by comma and ' - ' 
        for part in re.split(r',| - ', loc):
            p = part.strip()
            if p and p not in parts:
                parts.append(p)
                
        # To avoid duplicating 'Kaiserslautern', clean up parts
        clean_parts = []
        for p in parts:
            if p == 'Kaiserslautern':
                continue
            # sometimes "Kaiserslautern-West" -> keep
            clean_parts.append(p)
            
        if not clean_parts:
            return 'Kaiserslautern'
            
        return 'Kaiserslautern, ' + ', '.join(clean_parts)

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    apartment_id = db.Column(db.Integer, db.ForeignKey('apartment.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)
