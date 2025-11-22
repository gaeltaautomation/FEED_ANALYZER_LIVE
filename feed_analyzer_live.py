import streamlit as st    # Toto umožní použít webové rozhraní místo klasického inputu
import lxml.etree as ET   # Vaše XML knihovna
from collections import Counter, defaultdict  # Potřebné pro statistiky

# Funkce
#-------

# Funkce pro načtení souboru
# --------------------------
def nacti_xml_cesta(cesta):
    # Načti XML soubor ze zadané cesty
    return ET.parse(cesta)

# Funkce pro detekci rootu a produktu
# -----------------------------------
def detekuj_root_a_produkt(tree):
    # Získá root element a detekuje,
    # který podřízený element je pravděpodobně produkt (nejčastější)
    root = tree.getroot()
    root_tag = root.tag.split("}")[-1]

    # Spočítá výskyty
    counter = Counter()
    for elem in root:
        tag = elem.tag.split("}")[-1]
        counter[tag] += 1
    if not counter:
        raise ValueError("V XML nebyly nalezeny žádné potomky rootu")
    produkt_tag, pocet = counter.most_common(1)[0]
    return root_tag, produkt_tag, pocet

# Funkce pro tvorbu statistiky polí produktů
# ------------------------------------------
def statistika_poli(tree, produkt_tag):
    # Prochází všechny produkty a analyzuje obsazenost každého pole
    vyplneno = Counter()
    prazdno  = Counter()
    celkem_produkty = 0

    for produkt in tree.iterfind(f".//{produkt_tag}"):
        celkem_produkty += 1
        for polozka in produkt:
            pole = polozka.tag.split("}")[-1]
            text = (polozka.text or "").strip()
            if text:
                vyplneno[pole] += 1
            else:
                prazdno[pole] += 1

    return vyplneno, prazdno, celkem_produkty

# Funkce pro zápis reportu
# ------------------------
def zapis_report(soubor, root_tag, produkt_tag, pocet, vyplneno, prazdno, celkem_produkty):
    # Uloží hlavní info a statistiky do markdown souboru přes již otevřený soubor
    soubor.write("# Statistika XML feedu\n\n")
    soubor.write(f"- Root element: `{root_tag}`\n")
    soubor.write(f"- Produktový element: `{produkt_tag}`\n")
    soubor.write(f"- Počet produktů: `{celkem_produkty}`\n\n")
    soubor.write("## Obsazenost polí\n\n")
    vsechny_pole = set(vyplneno) | set(prazdno)
    for pole in sorted(vsechny_pole):
        plne = vyplneno.get(pole, 0)
        prazd = prazdno.get(pole, 0)
        procenta = 100 * plne / celkem_produkty if celkem_produkty else 0
        soubor.write(f"- `{pole}`: vyplněno {plne}/{celkem_produkty} ({procenta:.2f} %), prázdné {prazd}/{celkem_produkty}\n")

# --------------------------------------------------------------
# Funkce pro DETEKCI STRUKTURY VARIANT PRODUKTŮ
# Varianty detekujeme podle typických polí v každém produktu.
# --------------------------------------------------------------

# Funkce pro detekci variantních polí
# -----------------------------------
def najdi_variantni_pole(tree, produkt_tag):
    kandidati = set()
    for produkt in tree.iterfind(f".//{produkt_tag}"):
        for polozka in produkt:
            pole = polozka.tag.lower()
            if any(klic in pole for klic in ["group", "parent", "variant"]):
                kandidati.add(polozka.tag.split("}")[-1])
    return sorted(list(kandidati))

# Funkce pro analýzu variantních skupin
# -------------------------------------
def analyzuj_varianty(tree, produkt_tag, variantni_pole):
    skupiny = defaultdict(list)
    bez_varianty = []
    for produkt in tree.iterfind(f".//{produkt_tag}"):
        nalezeno = False
        for pole in variantni_pole:
            elem = produkt.find(pole)
            if elem is not None and elem.text and elem.text.strip():
                skupiny[elem.text.strip()].append(produkt)
                nalezeno = True
                break
        if not nalezeno:
            bez_varianty.append(produkt)
    return skupiny, bez_varianty

# Funkce pro zápis statistiky variant do markdown reportu
# -------------------------------------------------------
def zapis_variantni_statistiku(soubor, variantni_pole, skupiny, bez_varianty):
    soubor.write(f"\n## Analýza variant\n\n")
    if not variantni_pole:
        soubor.write("Nebyla detekována žádná pole vhodná pro variantní skupiny.\n")
        return
    soubor.write(f"Při detekci variant byly nalezeny kandidátní tagy: {', '.join(variantni_pole)}\n\n")
    soubor.write(f"- Počet variantních skupin: {len(skupiny)}\n")
    soubor.write(f"- Průměrný počet variant na skupinu: {sum(len(v) for v in skupiny.values()) / len(skupiny) if skupiny else 0:.2f}\n")
    soubor.write(f"- Počet produktů bez variantního pole: {len(bez_varianty)}\n\n")
    soubor.write("### Největší variantní skupiny\n")
    pro_top = sorted(skupiny.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for group, produkty in pro_top:
        soubor.write(f"- skupina {group}: {len(produkty)} variant\n")

# Funkce pro detekci opakujících se hodnot v polích
# -------------------------------------------------
def detekuj_opakujici_se_hodnoty(tree, produkt_tag, threshold=10):
    # Pro každý tag vypíše hodnoty, které se vyskytují minimálně `threshold` krát
    hodnoty_pole = defaultdict(Counter)
    for produkt in tree.iterfind(f".//{produkt_tag}"):
        for polozka in produkt:
            pole = polozka.tag.split("}")[-1]
            hodnota = (polozka.text or "").strip()
            if hodnota:
                hodnoty_pole[pole][hodnota] += 1

    opakovane = {}
    for pole, counter in hodnoty_pole.items():
        vyskyty = {hodnota: count for hodnota, count in counter.items() if count >= threshold}
        if vyskyty:
            opakovane[pole] = vyskyty
    return opakovane

# Funkce pro zápis opakujících se hodnot do markdown reportu
# ----------------------------------------------------------
def zapis_opakujici_se_hodnoty(soubor, opakovane_hodnoty):
    soubor.write("\n## Pole s opakujícími se hodnotami\n\n")
    if not opakovane_hodnoty:
        soubor.write("Nebyly nalezeny žádné hodnoty, které by se v některém poli opakovaly alespoň 10×.\n")
        return
    for pole, hodnoty in opakovane_hodnoty.items():
        soubor.write(f"- **{pole}**:\n")
        for hodnota, count in sorted(hodnoty.items(), key=lambda x: -x[1]):
            soubor.write(f"    - '{hodnota}': {count}×\n")
        soubor.write("\n")
        
# Streamlit část pro nahrání souboru
#-----------------------------------

st.title("XML Feed Analyzer")  # Zobrazí nadpis v aplikaci
uploaded_file = st.file_uploader("Nahrajte XML soubor", type=["xml"])  # Uživatel nahraje XML soubor

# Pokud je soubor nahrán, tento blok se spustí
#----------------------------------------------

if uploaded_file:
    strom = ET.parse(uploaded_file)
    root_tag, produkt_tag, pocet = detekuj_root_a_produkt(strom)
    vyplneno, prazdno, celkem_produkty = statistika_poli(strom, produkt_tag)
    variantni_pole = najdi_variantni_pole(strom, produkt_tag)
    skupiny, bez_varianty = analyzuj_varianty(strom, produkt_tag, variantni_pole)
    opakovane_hodnoty = detekuj_opakujici_se_hodnoty(strom, produkt_tag)

    from io import StringIO
    f = StringIO()
    zapis_report(f, root_tag, produkt_tag, pocet, vyplneno, prazdno, celkem_produkty)
    zapis_variantni_statistiku(f, variantni_pole, skupiny, bez_varianty)
    zapis_opakujici_se_hodnoty(f, opakovane_hodnoty)
    vysledek = f.getvalue()

    st.markdown(vysledek)
else:
    st.info("Nejprve nahrajte XML soubor.")

