import re
text='Wohnung 75 m2 129000 € zum Kauf'
print(re.search(r'(\d+(?:[.\s]\d{3})*(?:,\d{1,2})?)\s*(?:€|EUR|Euro)', text, re.IGNORECASE).groups())
