import re
from bs4 import BeautifulSoup

with open("jornada1.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("=" * 65)
print(" 🔬 ANÁLISIS DEL HTML REAL DE 106 KB ('jornada1.html')")
print("=" * 65)

# 1. Buscar iFrames dentro de la página real
iframes = soup.find_all('iframe')
print(f"1. iFrames encontrados: {len(iframes)}")
for i, f in enumerate(iframes):
    print(f"   > Frame {i+1}: name='{f.get('name')}' | id='{f.get('id')}' | src='{f.get('src')}'")

# 2. Buscar formularios y campos ocultos de ASP.NET
forms = soup.find_all('form')
print(f"\n2. Formularios <form>: {len(forms)}")
for form in forms:
    print(f"   > Form action='{form.get('action')}' | name='{form.get('name')}'")

# 3. Buscar cualquier función JavaScript de navegación (IrA, CargarJornada, Exec, etc.)
scripts = soup.find_all('script')
funciones_js = set()
for s in scripts:
    if s.text:
        matches = re.findall(r'function\s+([a-zA-Z0-9_]+)|([a-zA-Z0-9_]+_Exec)', s.text)
        for m in matches:
            fn = m[0] or m[1]
            if fn and len(fn) > 2:
                funciones_js.add(fn)

print(f"\n3. Funciones JS clave detectadas: {list(funciones_js)[:10]}")

# 4. Buscar nombres de los equipos de la Jornada 1 para verificar si el texto está presente
# Si la página incluye los nombres de los equipos pero no el parámetro 'CodPartido'
texto_pagina = soup.text
print(f"\n4. Longitud total del texto visible: {len(texto_pagina)} caracteres")