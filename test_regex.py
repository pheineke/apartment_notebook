import re
text = 'Wohnung 75 m² 129000  zum Kauf'
print(re.findall(r'(?:|EUR|Euro)', text, re.IGNORECASE))
print(re.findall(r'', text))
print([ord(c) for c in text])
