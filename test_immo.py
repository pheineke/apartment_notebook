import os; import time; from scraper import scrape_apartment_details
urls=['161718612','164962976','166497484','151890709','163842578','166189177','166442877','164923822','165728912','166299016','153311918','165594839']
for x in urls:
    os.system('taskkill /f /im chrome.exe /t >nul 2>&1'); os.system('taskkill /f /im chromedriver.exe /t >nul 2>&1'); time.sleep(1);
    u='https://www.immobilienscout24.de/expose/' + x
    print('----', x)
    res=scrape_apartment_details(u)
    if isinstance(res, tuple) and not res[0]: print('BLOCKED', res[1].get('error'))
    elif isinstance(res, dict) and 'blocked' in res: print('BLOCKED', res.get('error'))
    else: print('OK')
