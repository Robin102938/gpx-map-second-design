# Erweiterte GP# Zusätzliche Statistik zur GPX-Datei berechnen
def calculate_gpx_stats(coords, total_distance_km, duration_str=None):
    """Berechnet erweiterte Statistiken aus GPX-Daten"""
    stats = {}
    
    # Höhendaten (wenn vorhanden)
    if len(gpx.tracks) > 0 and len(gpx.tracks[0].segments) > 0:
        try:
            # Gesamter Höhenanstieg/-abstieg
            elevation_data = [p.elevation for p in gpx.tracks[0].segments[0].points if p.elevation is not None]
            if elevation_data:
                # Höhenprofil
                stats['min_elevation'] = min(elevation_data)
                stats['max_elevation'] = max(elevation_data)
                
                # Gesamter Anstieg/Abstieg
                total_ascent = 0
                total_descent = 0
                for i in range(1, len(elevation_data)):
                    diff = elevation_data[i] - elevation_data[i-1]
                    if diff > 0:
                        total_ascent += diff
                    else:
                        total_descent += abs(diff)
                        
                stats['total_ascent'] = int(total_ascent)
                stats['total_descent'] = int(total_descent)
                stats['has_elevation'] = True
            else:
                stats['has_elevation'] = False
        except:
            stats['has_elevation'] = False
    else:
        stats['has_elevation'] = False
    
    # Durchschnittsgeschwindigkeit (wenn Dauer angegeben)
    if duration_str:
        try:
            h, m, s = map(int, duration_str.split(':'))
            total_hours = h + m/60 + s/3600
            stats['avg_speed'] = round(total_distance_km / total_hours, 1) if total_hours > 0 else 0
        except:
            stats['avg_speed'] = 0
    else:
        stats['avg_speed'] = 0
    
    return statsimport io, math

import gpxpy, streamlit as st

from datetime import datetime

from staticmap import StaticMap, Line, CircleMarker

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import matplotlib.pyplot as plt

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

st.set_page_config(layout="wide")

st.title("GPX Map Poster – Vienna Style")

# ——— Sidebar Einstellungen ———

# ——— Erweiterte Kartenkonfiguration ———
st.sidebar.header("🗺️ Erweiterte Kartenkonfiguration")

# Variable für benutzerdefinierte OSM-API-Keys
api_key_option = st.sidebar.checkbox("API-Key verwenden (für einige Kartenstile)", value=False)

if api_key_option:
    thunderforest_api = st.sidebar.text_input("Thunderforest API-Key (für Outdoors/Transport)", "6170aad10dfd42a38d4d8c709a536f38")
    jawg_api = st.sidebar.text_input("Jawg API-Key (für Jawg-Stile)", "community")
else:
    thunderforest_api = "6170aad10dfd42a38d4d8c709a536f38"  # Demo-Key mit Anfragelimit
    jawg_api = "community"  # Community-Demo-Key

# Füge die Option für benutzerdefinierte Tile-URL hinzu
custom_tile = st.sidebar.checkbox("Benutzerdefinierte Kartenquelle", value=False)

if custom_tile:
    custom_tile_url = st.sidebar.text_input(
        "Benutzerdefinierte Tile-URL (mit {x}, {y}, {z} Platzhaltern)",
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    )
    custom_bg_color = st.sidebar.color_picker("Hintergrundfarbe für benutzerdefinierte Karte", "#FFFFFF")

# ——— Farben & Stil ———
st.sidebar.header("🎨 Farben & Stil")

# ——— Zusätzliche Stile für das Poster ———
st.sidebar.header("🖼️ Poster-Stile")

poster_theme = st.sidebar.selectbox(
    "Poster-Thema",
    ["Vienna Classic", "Vienna Dark", "Marathon", "Trail Run", "Urban Run", "Custom"]
)

# Stil-Presets konfigurieren
if poster_theme == "Vienna Classic":
    inner_bg_color = "#F0F0F0"  # Hellgrau
    route_color = "#FFD700"     # Gold
    start_color = "#FF8C00"     # Orange
    end_color = "#FF8C00"       # Orange
    title_color = "#000000"     # Schwarz
    subtitle_color = "#333333"  # Dunkelgrau
    data_color = "#000000"      # Schwarz
    unit_color = "#333333"      # Dunkelgrau
elif poster_theme == "Vienna Dark":
    inner_bg_color = "#121212"  # Sehr dunkel
    route_color = "#FFD700"     # Gold
    start_color = "#FF8C00"     # Orange
    end_color = "#FF8C00"       # Orange
    title_color = "#FFFFFF"     # Weiß
    subtitle_color = "#BBBBBB"  # Hellgrau
    data_color = "#FFFFFF"      # Weiß
    unit_color = "#BBBBBB"      # Hellgrau
elif poster_theme == "Marathon":
    inner_bg_color = "#003366"  # Tiefblau
    route_color = "#FF4500"     # Orangerot
    start_color = "#FFFFFF"     # Weiß
    end_color = "#FFFFFF"       # Weiß
    title_color = "#FFFFFF"     # Weiß
    subtitle_color = "#DDDDDD"  # Hellgrau
    data_color = "#FFFFFF"      # Weiß
    unit_color = "#DDDDDD"      # Hellgrau
elif poster_theme == "Trail Run":
    inner_bg_color = "#2E4A2E"  # Waldgrün
    route_color = "#FFFF00"     # Gelb
    start_color = "#6EE06E"     # Hellgrün
    end_color = "#6EE06E"       # Hellgrün
    title_color = "#FFFFFF"     # Weiß
    subtitle_color = "#D0D0D0"  # Hellgrau
    data_color = "#FFFFFF"      # Weiß
    unit_color = "#D0D0D0"      # Hellgrau
elif poster_theme == "Urban Run":
    inner_bg_color = "#232323"  # Dunkelgrau
    route_color = "#00FFFF"     # Türkis
    start_color = "#FF00FF"     # Magenta
    end_color = "#FF00FF"       # Magenta
    title_color = "#FFFFFF"     # Weiß
    subtitle_color = "#CCCCCC"  # Hellgrau
    data_color = "#FFFFFF"      # Weiß
    unit_color = "#CCCCCC"      # Hellgrau
else:  # Custom
    st.sidebar.subheader("Benutzerdefinierte Farbeinstellungen")
    inner_bg_color = st.sidebar.color_picker("Innere Hintergrundfarbe", "#F0F0F0")
    route_color = st.sidebar.color_picker("Streckenfarbe", "#FFD700")
    start_color = st.sidebar.color_picker("Startpunkt", "#FF8C00")
    end_color = st.sidebar.color_picker("Zielpunkt", "#FF8C00")
    title_color = st.sidebar.color_picker("Titelfarbe", "#000000")
    subtitle_color = st.sidebar.color_picker("Untertitelfarbe", "#333333")
    data_color = st.sidebar.color_picker("Datenfarbe", "#000000")
    unit_color = st.sidebar.color_picker("Einheitenfarbe", "#333333")

map_style = st.sidebar.selectbox(
    "Kartenstil",
    [
        "Vienna Dark Blue", 
        "CartoDB Dark Matter", 
        "CartoDB Positron (Light)", 
        "OSM Standard",
        "Stamen Toner",
        "Stamen Watercolor",
        "Stamen Terrain",
        "Thunderforest Outdoors",
        "Thunderforest Transport",
        "Jawg Dark",
        "Jawg Light",
        "ESRI World Imagery"
    ]
)

# Zusätzliche Kartenstiloptionen
map_zoom = st.sidebar.slider("Karten-Zoom", 10, 16, 14)
line_width = st.sidebar.slider("Streckenbreite", 2, 15, 8)
marker_size = st.sidebar.slider("Markergröße", 10, 50, 30)

pace_calculation = st.sidebar.checkbox("Pace berechnen (min/km)", value=True)

# Tile-Template je Stil
# Erweiterte Auswahl von Kartenstilen mit ihren jeweiligen Base-Farben

if custom_tile:
    TILE = custom_tile_url
    map_base_color = custom_bg_color
elif map_style == "Vienna Dark Blue":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    map_base_color = "#1A237E"  # Dunkelblau für Vienna Style
elif map_style == "CartoDB Dark Matter":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    map_base_color = "#121212"
elif map_style == "CartoDB Positron (Light)":
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    map_base_color = "#F5F5F5"
elif map_style == "Stamen Toner":
    TILE = "https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png"
    map_base_color = "#000000"
elif map_style == "Stamen Watercolor":
    TILE = "https://stamen-tiles.a.ssl.fastly.net/watercolor/{z}/{x}/{y}.jpg"
    map_base_color = "#F5F5E9"
elif map_style == "Stamen Terrain":
    TILE = "https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png"
    map_base_color = "#EEEEEE"
elif map_style == "Thunderforest Outdoors":
    TILE = f"https://tile.thunderforest.com/outdoors/{{z}}/{{x}}/{{y}}.png?apikey={thunderforest_api}"
    map_base_color = "#C5E8FF"
elif map_style == "Thunderforest Transport":
    TILE = f"https://tile.thunderforest.com/transport/{{z}}/{{x}}/{{y}}.png?apikey={thunderforest_api}"
    map_base_color = "#DDDDDD"
elif map_style == "Jawg Dark":
    TILE = f"https://tile.jawg.io/jawg-dark/{{z}}/{{x}}/{{y}}.png?access-token={jawg_api}"
    map_base_color = "#2D2D2D"
elif map_style == "Jawg Light":
    TILE = f"https://tile.jawg.io/jawg-light/{{z}}/{{x}}/{{y}}.png?access-token={jawg_api}"
    map_base_color = "#F5F5F5"
elif map_style == "ESRI World Imagery":
    TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    map_base_color = "#242424"
else:
    TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    map_base_color = "#FFFFFF"

# ——— Input ———

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
    
    # Für die Pace-Berechnung
    if pace_calculation and duration:
        # Parsen der Zeit
        try:
            h, m, s = map(int, duration.split(':'))
            total_seconds = h * 3600 + m * 60 + s
            # Berechne Pace in min/km
            if total_distance_km > 0:
                pace_seconds = total_seconds / total_distance_km
                pace_min = int(pace_seconds // 60)
                pace_sec = int(pace_seconds % 60)
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
    m.add_line(Line(coords, color=route_color, width=line_width))
    m.add_marker(CircleMarker(coords[0], start_color, marker_size))
    m.add_marker(CircleMarker(coords[-1], end_color, marker_size))
    map_img = m.render(zoom=map_zoom)
    
    # 3) Vienna-Style Poster erstellen
    # Weißer Rahmen außen
    poster = Image.new("RGB", (POSTER_W, POSTER_H), "white")
    draw = ImageDraw.Draw(poster)
    
    # Innere Fläche (benutzerdefinierte Farbe)
    inner_bg = Image.new("RGB", (POSTER_W - 2*BORDER_SIZE, POSTER_H - 2*BORDER_SIZE), inner_bg_color)
    poster.paste(inner_bg, (BORDER_SIZE, BORDER_SIZE))
    
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
    draw.text(((POSTER_W-tw)/2, y), title, font=f_title, fill=title_color)
    y += th + 50  # Erhöhter Abstand zwischen Titel und Datum
    
    # Datum
    date_str = run_date.strftime('%d %B %Y').upper()
    bbox_d = draw.textbbox((0, 0), date_str, font=f_subtitle)
    dw, dh = bbox_d[2]-bbox_d[0], bbox_d[3]-bbox_d[1]
    draw.text(((POSTER_W-dw)/2, y), date_str, font=f_subtitle, fill=subtitle_color)
    y += dh + 40
    
    # Map mit Zentrierung
    map_pos = ((POSTER_W - MAP_SIZE) // 2, y)
    poster.paste(map_img, map_pos)
    y += MAP_SIZE + 80
    
    # Läufername und Nummer
    runner_text = runner.upper()
    bib_text = f"#{bib_no}"
    
    # Trennlinie
    draw.line((BORDER_SIZE + 100, y, POSTER_W - BORDER_SIZE - 100, y), fill="#000000", width=3)
    y += 40
    
    # Läufer-Text
    bbox_r = draw.textbbox((0, 0), runner_text, font=f_runner)
    rw, rh = bbox_r[2]-bbox_r[0], bbox_r[3]-bbox_r[1]
    draw.text(((POSTER_W-rw)/2, y), runner_text, font=f_runner, fill=title_color)
    y += rh + 25  # Erhöhter Abstand zwischen Name und Startnummer
    
    # Startnummer
    bbox_b = draw.textbbox((0, 0), bib_text, font=f_subtitle)
    bw, bh = bbox_b[2]-bbox_b[0], bbox_b[3]-bbox_b[1]
    draw.text(((POSTER_W-bw)/2, y), bib_text, font=f_subtitle, fill=subtitle_color)
    y += bh + 80  # Mehr Abstand vor den Daten
    
    # Daten-Abschnitt im Vienna-Stil: drei Spalten mit mehr Abstand
    cols = 3
    col_width = (POSTER_W - 2*BORDER_SIZE - 2*pad) // cols
    
    # Laufwerte
    data = [
        (distance, "KM", data_color),
        (duration, "TIME", data_color),
        (pace_str, "/KM", data_color) if pace_calculation else ("", "", data_color)
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
        draw.text((x + (col_width - uw) // 2, y + vh + 20), unit, font=f_unit, fill=unit_color)
    
    # Debug-Info zur dynamischen Schriftgröße anzeigen
    st.write(f"Dynamische Titelgröße: {title_font_size}px für '{title}'")
    
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
