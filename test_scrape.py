from scraper import scrape_apartment_details

url1 = "https://www.kleinanzeigen.de/s-anzeige/1-zimmer-wohnung-ab-01-06-2026-zu-vermieten-naehe-uni/3349797378-203-5473"
url2 = "https://www.immobilienscout24.de/expose/161718612"
url3 = "https://immo.rheinpfalz.de/immobilien/2-zimmer-wohnung-mit-balkon-in-ruhiger-wohnlage-von-kaiserslautern-GMSFSN"

def run_test():
    for u in [url1, url2, url3]:
        print(f"Testing {u}")
        success, data = scrape_apartment_details(u)
        print("Success:", success)
        print("Data:", data)
        print("-" * 50)

if __name__ == "__main__":
    run_test()
