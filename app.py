import io
import math
import os
import streamlit as st
import gpxpy
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ——— Konfiguration ———
MAX_SPEED_M_S   = 10      # maximal erlaubte Geschwindigkeit (m/s)
MIN_DT_S        = 1       # minimale Zeitdifferenz (s)
MAX_PTS_DISPLAY = 2000    # Sampling-Limit

# Postergrößen für Vienna-Style
POSTER_W = 2480
POSTER_H = 3508  # A4 Verhältnis bei 300dpi
MAP_SIZE = 2000  # quadratische Karte, kleiner als Posterbreite
BORDER_SIZE = 100  # Rahmendicke

# Neue Funktion zur dynamischen Anpassung der Schriftgröße
def get_dynamic_font_size(text, max_width, font_name, start_size=140, min_size=60):
    """
    Bestimmt die optimale Schriftgröße für einen Text, damit er in die maximale Breite passt
    """
    size = start_size
    
    # Versuche die angegebene Schriftart zu laden
    try:
        test_font = ImageFont.truetype(font_name + "-Bold.ttf", size)
    except:
        try:
            test_font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except:
            return min_size  # Fallback bei Problemen mit Schriftarten
            
    # Testbild für Messungen erstellen
    test_img = Image.new("RGB", (1, 1), "white")
    test_draw = ImageDraw.Draw(test_img)
    
    # Schriftgröße reduzieren bis Text passt
    while size > min_size:
        try:
            test_font = ImageFont.truetype(font_name + "-Bold.ttf", size)
        except:
            try:
                test_font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
            except:
                break
                
        bbox = test_draw.textbbox((0, 0), text, font=test_font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            break
            
        size -= 5  # Schrittweise verkleinern
        
    return size

# Streamlit Konfiguration
st.set_page_config(layout="wide")

st.title("GPX Map Poster – Vienna Style")

# ——— Sidebar Einstellungen ———
st.sidebar.header("🎨 Farben & Stil")

# Erstelle Info-Container für Kartenstile
st.sidebar.markdown("---")
with st.sidebar.expander("📚 Kartenstil-Informationen"):
    st.markdown("""
    ### Verfügbare Kartenstile:
    
    #### Basis-Stile:
    - **Vienna Dark Blue**: Dunkler Stil - perfekt für Nachtläufe und Vienna-Style
    - **OSM Standard**: Standard OpenStreetMap-Stil
    
    #### CartoDB:
    - **CartoDB Dark Matter**: Eleganter, dunkler Stil
    - **CartoDB Positron**: Heller, minimalistischer Stil
    
    #### Thunderforest:
    - **Thunderforest Outdoors**: Detaillierte Outdoor-Karte, gut für Trails
    - **Thunderforest Landscape**: Landschaftsansicht mit Höhendetails
    - **Thunderforest Transport**: Karte mit Fokus auf Verkehrswege
    
    #### Spezial-Stile:
    - **OpenTopoMap**: Topographische Karte mit Höhenlinien
    - **CyclOSM**: Für Radfahrer optimierter Stil
    - **OSM HOT**: Humanitarian OpenStreetMap Style
    
    #### ESRI:
    - **ESRI WorldStreetMap**: Detaillierte Straßenkarte
    - **ESRI WorldTopoMap**: Topographische Weltkarte
    - **ESRI WorldImagery**: Satellitenbilder
    """)

inner_bg_color = st.sidebar.color_picker("Innere Hintergrundfarbe", "#F0F0F0")  # Hellgrau
route_color = st.sidebar.color_picker("Streckenfarbe", "#FFD700")  # Gold für Vienna
start_color = st.sidebar.color_picker("Startpunkt", "#FF8C00")  # Orange
end_color = st.sidebar.color_picker("Zielpunkt", "#FF8C00")  # Orange

# Neue Option für Anpassung der Zoom-Stufe
st.sidebar.header("🗺️ Karteneinstellungen")
map_zoom = st.sidebar.slider("Zoom-Stufe", 10, 18, 14)

map_style = st.sidebar.selectbox(
    "Kartenstil",
    [
        "Vienna Dark Blue", 
        "CartoDB Dark Matter", 
        "CartoDB Positron (Light)", 
        "OSM Standard", 
        "Thunderforest Outdoors", 
        "Thunderforest Landscape", 
        "Thunderforest Transport",
        "OpenTopoMap",
        "CyclOSM", 
        "OSM HOT", 
        "ESRI WorldStreetMap", 
        "ESRI WorldTopoMap", 
        "ESRI WorldImagery"
    ]
)

pace_calculation = st.sidebar.checkbox("Pace berechnen (min/km)", value=True)

# Extra Einstellungen
map_opacity = st.sidebar.slider("Karte Transparenz", 0, 100, 100) / 100
route_width = st.sidebar.slider("Streckendicke", 2, 15, 8)
point_size = st.sidebar.slider("Punkt-Größe", 10, 50, 30)

# Tile-Template je Stil
if map_style == "Vienna Dark Blue":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    map_base_color = "#1A237E"  # Dunkelblau für Vienna Style
elif map_style == "CartoDB Dark Matter":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    map_base_color = "#121212"
elif map_style == "CartoDB Positron (Light)":
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    map_base_color = "#F5F5F5"
elif map_style == "Thunderforest Outdoors":
    TILE = "https://tile.thunderforest.com/outdoors/{z}/{x}/{y}.png?apikey=6170aad10dfd42a38d4d8c709a536f38"
    map_base_color = "#F2F2F2"
elif map_style == "Thunderforest Landscape":
    TILE = "https://tile.thunderforest.com/landscape/{z}/{x}/{y}.png?apikey=6170aad10dfd42a38d4d8c709a536f38"
    map_base_color = "#F5F5F5"
elif map_style == "Thunderforest Transport":
    TILE = "https://tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey=6170aad10dfd42a38d4d8c709a536f38"
    map_base_color = "#F5F5F5"
elif map_style == "OpenTopoMap":
    TILE = "https://a.tile.opentopomap.org/{z}/{x}/{y}.png"
    map_base_color = "#F5F5F5"
elif map_style == "CyclOSM":
    TILE = "https://a.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png"
    map_base_color = "#F5F5F5"
elif map_style == "OSM HOT":
    TILE = "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"
    map_base_color = "#F5F5F5"
elif map_style == "ESRI WorldStreetMap":
    TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
    map_base_color = "#FFFFFF"
elif map_style == "ESRI WorldTopoMap":
    TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
    map_base_color = "#F5F5F5"
elif map_style == "ESRI WorldImagery":
    TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    map_base_color = "#000000"
else:
    TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    map_base_color = "#FFFFFF"

# ——— Input ———
st.sidebar.header("📸 Logo")
logo_file = st.sidebar.file_uploader("Marathon-Logo hochladen (optional)", type=["png", "jpg", "jpeg"])
logo_size = st.sidebar.slider("Logo-Größe (%)", 5, 30, 15)
logo_position = st.sidebar.selectbox(
    "Logo-Position", 
    ["Oben links", "Oben Mitte", "Oben rechts", "Unten links", "Unten Mitte", "Unten rechts"]
)

gpx_file = st.file_uploader("GPX-Datei hochladen", type="gpx")

event_name = st.text_input("Name des Laufs (z.B. Vienna City Marathon)", "VIENNA CITY MARATHON")

run_date = st.date_input("Datum")

distance_opt = st.selectbox(
    "Distanz", 
    ["5 km", "10 km", "21,0975 km", "42,195 km", "Andere…"]
)

if distance_opt == "Andere…":
    distance = st.text_input("Eigene Distanz (z.B. '15 km')")
else:
    distance = distance_opt

runner = st.text_input("Name des Läufers", "ATHLETE NAME")

bib_no = st.text_input("Startnummer (# automatisch davor)", "1234")

duration = st.text_input("Zeit (HH:MM:SS)", "00:00:00")

# ——— Poster erzeugen ———
if st.button("Poster erstellen") and gpx_file and event_name:
    # 1) GPX parse + Filter
    gpx = gpxpy.parse(gpx_file)
    pts_raw = [(pt.longitude, pt.latitude, pt.time)
               for tr in gpx.tracks for seg in tr.segments for pt in seg.points]
    if len(pts_raw) < 2:
        st.error("Kein Track gefunden.")
        st.stop()
    
    # Filtern schneller Ausreißer
    def hav(a, b):
        lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * 6371000 * math.asin(math.sqrt(h))
    
    clean = [pts_raw[0]]
    total_distance = 0
    for a, b in zip(pts_raw, pts_raw[1:]):
        dist = hav(a, b)
        dt = (b[2]-a[2]).total_seconds() if a[2] and b[2] else MIN_DT_S
        if dt >= MIN_DT_S and dist/dt <= MAX_SPEED_M_S:
            clean.append(b)
            total_distance += dist
    
    coords = [(lon, lat) for lon, lat, _ in clean]
    
    # Berechne Gesamtdistanz in km
    total_distance_km = total_distance / 1000
    
    # Für die Pace-Berechnung - korrigierte Version
    if pace_calculation and duration:
        # Parsen der Zeit
        try:
            h, m, s = map(int, duration.split(':'))
            total_seconds = h * 3600 + m * 60 + s
            # Berechne Pace in min/km mit korrekter Berechnung
            if total_distance_km > 0:
                pace_seconds = total_seconds / total_distance_km
                # Korrekte Umrechnung: Dezimalminuten in Minuten und Sekunden
                pace_min = int(pace_seconds // 60)
                pace_sec = int(pace_seconds % 60)
                
                # Format mit führenden Nullen
                pace_str = f"{pace_min:02d}:{pace_sec:02d}"
            else:
                pace_str = "00:00"
        except:
            pace_str = "00:00"
    else:
        pace_str = "00:00"
    
    # Sampling für Darstellung
    if len(coords) > MAX_PTS_DISPLAY:
        step = len(coords) // MAX_PTS_DISPLAY + 1
        coords = coords[::step]
    # 2) Karte rendern
    m = StaticMap(MAP_SIZE, MAP_SIZE, url_template=TILE)
    m.add_line(Line(coords, color=route_color, width=route_width))
    m.add_marker(CircleMarker(coords[0], start_color, point_size))
    m.add_marker(CircleMarker(coords[-1], end_color, point_size))
    map_img = m.render(zoom=map_zoom)
    
    # Transparenz der Karte anpassen, wenn gewünscht
    if map_opacity < 1.0:
        map_img.putalpha(int(255 * map_opacity))
        # Hintergrund für transparente Karte
        bg = Image.new("RGBA", (MAP_SIZE, MAP_SIZE), inner_bg_color)
        map_img = Image.alpha_composite(bg, map_img)
    
    # 3) Vienna-Style Poster erstellen
    # Weißer Rahmen außen
    poster = Image.new("RGB", (POSTER_W, POSTER_H), "white")
    draw = ImageDraw.Draw(poster)
    
    # Innere Fläche (benutzerdefinierte Farbe)
    inner_bg = Image.new("RGB", (POSTER_W - 2*BORDER_SIZE, POSTER_H - 2*BORDER_SIZE), inner_bg_color)
    poster.paste(inner_bg, (BORDER_SIZE, BORDER_SIZE))
    
    # Marathon-Logo einfügen, falls hochgeladen
    if logo_file is not None:
        try:
            # Logo laden und verarbeiten
            logo = Image.open(logo_file)
            
            # Größe basierend auf dem Prozentsatz der Posterbreite berechnen
            logo_width = int(POSTER_W * logo_size / 100)
            # Behalt das Seitenverhältnis bei
            logo_height = int(logo_width * logo.height / logo.width)
            
            # Logo resizen
            logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
            
            # Logo Position bestimmen
            padding = 50  # Abstand vom Rand
            if logo_position == "Oben links":
                logo_pos = (BORDER_SIZE + padding, BORDER_SIZE + padding)
            elif logo_position == "Oben Mitte":
                logo_pos = ((POSTER_W - logo_width) // 2, BORDER_SIZE + padding)
            elif logo_position == "Oben rechts":
                logo_pos = (POSTER_W - BORDER_SIZE - padding - logo_width, BORDER_SIZE + padding)
            elif logo_position == "Unten links":
                logo_pos = (BORDER_SIZE + padding, POSTER_H - BORDER_SIZE - padding - logo_height)
            elif logo_position == "Unten Mitte":
                logo_pos = ((POSTER_W - logo_width) // 2, POSTER_H - BORDER_SIZE - padding - logo_height)
            else:  # Unten rechts
                logo_pos = (POSTER_W - BORDER_SIZE - padding - logo_width, POSTER_H - BORDER_SIZE - padding - logo_height)
            
            # Falls das Logo einen Alphakanal hat, entsprechenden Hintergrund erstellen
            if logo.mode == 'RGBA':
                # Erstelle einen Hintergrund in der Farbe des inneren Hintergrunds
                bg = Image.new('RGB', logo.size, inner_bg_color)
                # Kombiniere Logo mit Hintergrund
                logo = Image.alpha_composite(bg.convert('RGBA'), logo)
                logo = logo.convert('RGB')
            
            # Logo auf das Poster einfügen
            poster.paste(logo, logo_pos)
            st.sidebar.success("Logo erfolgreich eingefügt!")
        except Exception as e:
            st.sidebar.error(f"Fehler beim Einfügen des Logos: {str(e)}")
    
    # Verfügbare Breite berechnen (mit Innenabstand)
    pad = 150  # Innenabstand
    available_width = POSTER_W - 2*BORDER_SIZE - 2*pad
    
    # Dynamische Schriftgröße für den Titel bestimmen
    title = event_name.upper()
    title_font_size = get_dynamic_font_size(title, available_width, "Arial", 140, 60)
    
    # Schriften laden mit dynamischer Größe für den Titel
    try:
        f_title = ImageFont.truetype("Arial-Bold.ttf", title_font_size)
        f_subtitle = ImageFont.truetype("Arial.ttf", 60)
        f_runner = ImageFont.truetype("Arial-Bold.ttf", 100)
        f_data = ImageFont.truetype("Arial-Bold.ttf", 80)
        f_unit = ImageFont.truetype("Arial.ttf", 40)
    except:
        try:
            f_title = ImageFont.truetype("DejaVuSans-Bold.ttf", title_font_size)
            f_subtitle = ImageFont.truetype("DejaVuSans.ttf", 60)
            f_runner = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
            f_data = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
            f_unit = ImageFont.truetype("DejaVuSans.ttf", 40)
        except:
            f_title = f_subtitle = f_runner = f_data = f_unit = ImageFont.load_default()
    
    # Positionen
    y = BORDER_SIZE + pad
    
    # Titel mit dynamischer Schriftgröße
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((POSTER_W-tw)/2, y), title, font=f_title, fill="#000000")
    y += th + 50  # Erhöhter Abstand zwischen Titel und Datum
    
    # Datum
    date_str = run_date.strftime('%d %B %Y').upper()
    bbox_d = draw.textbbox((0, 0), date_str, font=f_subtitle)
    dw, dh = bbox_d[2]-bbox_d[0], bbox_d[3]-bbox_d[1]
    draw.text(((POSTER_W-dw)/2, y), date_str, font=f_subtitle, fill="#333333")
    y += dh + 150  # Mehr Abstand nach dem Datum - erhöht von 40 auf 150
    
    # Map mit Zentrierung
    map_pos = ((POSTER_W - MAP_SIZE) // 2, y)
    poster.paste(map_img, map_pos)
    y += MAP_SIZE + 120  # Mehr Abstand nach der Karte - erhöht von 80 auf 120
    
    # Läufername und Nummer
    runner_text = runner.upper()
    bib_text = f"#{bib_no}"
    
    # Trennlinie
    draw.line((BORDER_SIZE + 100, y, POSTER_W - BORDER_SIZE - 100, y), fill="#000000", width=3)
    y += 40
    
    # Läufer-Text
    bbox_r = draw.textbbox((0, 0), runner_text, font=f_runner)
    rw, rh = bbox_r[2]-bbox_r[0], bbox_r[3]-bbox_r[1]
    draw.text(((POSTER_W-rw)/2, y), runner_text, font=f_runner, fill="#000000")
    y += rh + 35  # Erhöhter Abstand zwischen Name und Startnummer (von 25 auf 35)
    
    # Startnummer
    bbox_b = draw.textbbox((0, 0), bib_text, font=f_subtitle)
    bw, bh = bbox_b[2]-bbox_b[0], bbox_b[3]-bbox_b[1]
    draw.text(((POSTER_W-bw)/2, y), bib_text, font=f_subtitle, fill="#333333")
    y += bh + 100  # Mehr Abstand vor den Daten (von 80 auf 100)
    
    # Daten-Abschnitt im Vienna-Stil: drei Spalten mit mehr Abstand
    cols = 3
    col_width = (POSTER_W - 2*BORDER_SIZE - 2*pad) // cols
    
    # Laufwerte - KORREKTUR: "km" aus Distanzwert entfernen
    data = [
        (distance.replace(" km", ""), "KM", "#000000"),
        (duration, "TIME", "#000000"),
        (pace_str, "/KM", "#000000") if pace_calculation else ("", "", "#000000")
    ]
    
    for i, (value, unit, color) in enumerate(data):
        # Spalten-Position berechnen
        x = BORDER_SIZE + pad + i * col_width
        
        # Wert
        bbox_v = draw.textbbox((0, 0), value, font=f_data)
        vw, vh = bbox_v[2]-bbox_v[0], bbox_v[3]-bbox_v[1]
        draw.text((x + (col_width - vw) // 2, y), value, font=f_data, fill=color)
        
        # Einheit - mehr Abstand zum Wert
        bbox_u = draw.textbbox((0, 0), unit, font=f_unit)
        uw, uh = bbox_u[2]-bbox_u[0], bbox_u[3]-bbox_u[1]
        draw.text((x + (col_width - uw) // 2, y + vh + 20), unit, font=f_unit, fill="#333333")
    
    # Debug-Info zur dynamischen Schriftgröße anzeigen
    st.write(f"Dynamische Titelgröße: {title_font_size}px für '{title}'")
    
    # Karteninfos anzeigen
    st.write(f"Kartenstil: {map_style} | Zoom: {map_zoom} | Routenpunkte: {len(coords)}")
    
    # Logo-Info anzeigen wenn verwendet
    if logo_file:
        st.write(f"Logo: {logo_file.name} | Position: {logo_position} | Größe: {logo_size}%")
    
    # Vorschau anzeigen
    st.image(poster, caption="Vienna-Style GPX Poster")
    
    # Download-Button
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    st.download_button(
        "Poster herunterladen", 
        buf.getvalue(), 
        file_name=f"{event_name.replace(' ', '_')}_poster.png", 
        mime="image/png"
    )
