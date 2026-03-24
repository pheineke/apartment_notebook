from app import app, db, Apartment

def init_db():
    with app.app_context():
        db.create_all()
        # If no apartments, read links.txt
        if Apartment.query.count() == 0:
            print("Database empty. Initializing from links.txt...")
            try:
                with open('links.txt', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('Mieten') and not line.startswith('Kaufen'):
                            print(f"Adding {line}")
                            apt = Apartment(original_url=line)
                            db.session.add(apt)
                    db.session.commit()
            except FileNotFoundError:
                print("links.txt not found. Starting with empty database.")
        print("Database initialized.")

if __name__ == '__main__':
    init_db()
