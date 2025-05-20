import io, math
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

st.set_page_config(layout="wide")
st.title("GPX Map Poster – Vienna Style")

# ——— Sidebar Einstellungen ———
st.sidebar.header("🎨 Farben & Stil")
inner_bg_color = st.sidebar.color_picker("Innere Hintergrundfarbe", "#F0F0F0")  # Hellgrau
route_color = st.sidebar.color_picker("Streckenfarbe", "#FFD700")  # Gold für Vienna
start_color = st.sidebar.color_picker("Startpunkt", "#FF8C00")  # Orange
end_color = st.sidebar.color_picker("Zielpunkt", "#FF8C00")  # Orange

map_style = st.sidebar.selectbox(
    "Kartenstil",
    ["Vienna Dark Blue", "CartoDB Dark Matter", "CartoDB Positron (Light)", "OSM Standard"]
)

pace_calculation = st.sidebar.checkbox("Pace berechnen (min/km)", value=True)

# Tile-Template je Stil
if map_style == "Vienna Dark Blue":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    map_base_color = "#1A237E"
elif map_style == "CartoDB Dark Matter":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    map_base_color = "#121212"
elif map_style == "CartoDB Positron (Light)":
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    map_base_color = "#F5F5F5"
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
    total_distance_km = total_distance / 1000
    
    if pace_calculation and duration:
        try:
            h, m, s = map(int, duration.split(':'))
            total_seconds = h * 3600 + m * 60 + s
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
    
    if len(coords) > MAX_PTS_DISPLAY:
        step = len(coords) // MAX_PTS_DISPLAY + 1
        coords = coords[::step]

    # 2) Karte rendern
    m = StaticMap(MAP_SIZE, MAP_SIZE, url_template=TILE)
    m.add_line(Line(coords, color=route_color, width=8))
    m.add_marker(CircleMarker(coords[0], start_color, 30))
    m.add_marker(CircleMarker(coords[-1], end_color, 30))
    map_img = m.render(zoom=14)
    
    # 3) Vienna-Style Poster erstellen
    poster = Image.new("RGB", (POSTER_W, POSTER_H), "white")
    draw = ImageDraw.Draw(poster)
    inner_bg = Image.new("RGB", (POSTER_W - 2*BORDER_SIZE, POSTER_H - 2*BORDER_SIZE), inner_bg_color)
    poster.paste(inner_bg, (BORDER_SIZE, BORDER_SIZE))

    # Schriften laden (feste Größen)
    try:
        f_title = ImageFont.truetype("Arial-Bold.ttf", 140)
        f_subtitle = ImageFont.truetype("Arial.ttf", 60)
        f_runner = ImageFont.truetype("Arial-Bold.ttf", 100)
        f_data = ImageFont.truetype("Arial-Bold.ttf", 80)
        f_unit = ImageFont.truetype("Arial.ttf", 40)
    except:
        f_title = ImageFont.load_default()
        f_subtitle = ImageFont.load_default()
        f_runner = ImageFont.load_default()
        f_data = ImageFont.load_default()
        f_unit = ImageFont.load_default()

    # Dynamische Schriftgröße nur für den Titel
    max_width = POSTER_W - 2 * BORDER_SIZE - 200
    base_size = 140
    try:
        font_size = base_size
        while font_size > 20:
            temp_font = ImageFont.truetype("Arial-Bold.ttf", font_size)
            if draw.textbbox((0, 0), event_name.upper(), font=temp_font)[2] <= max_width:
                f_title = temp_font
                break
            font_size -= 2
    except:
        pass

    # Positionen
    pad = 150
    y = BORDER_SIZE + pad

    # Titel zeichnen
    title = event_name.upper()
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((POSTER_W-tw)/2, y), title, font=f_title, fill="#000000")
    y += th + 50

    # Datum
    date_str = run_date.strftime('%d %B %Y').upper()
    bbox_d = draw.textbbox((0, 0), date_str, font=f_subtitle)
    dw, dh = bbox_d[2]-bbox_d[0], bbox_d[3]-bbox_d[1]
    draw.text(((POSTER_W-dw)/2, y), date_str, font=f_subtitle, fill="#333333")
    y += dh + 40

    # Map mit Zentrierung
    map_pos = ((POSTER_W - MAP_SIZE) // 2, y)
    poster.paste(map_img, map_pos)
    y += MAP_SIZE + 80

    # Läufername und Nummer etc. (unverändert)
    runner_text = runner.upper()
    bib_text = f"#{bib_no}"
    draw.line((BORDER_SIZE + 100, y, POSTER_W - BORDER_SIZE - 100, y), fill="#000000", width=3)
    y += 40
    bbox_r = draw.textbbox((0, 0), runner_text, font=f_runner)
    rw, rh = bbox_r[2]-bbox_r[0], bbox_r[3]-bbox_r[1]
    draw.text(((POSTER_W-rw)/2, y), runner_text, font=f_runner, fill="#000000")
    y += rh + 25
    bbox_b = draw.textbbox((0, 0), bib_text, font=f_subtitle)
    bw, bh = bbox_b[2]-bbox_b[0], bbox_b[3]-bbox_b[1]
    draw.text(((POSTER_W-bw)/2, y), bib_text, font=f_subtitle, fill="#333333")
    y += bh + 80

    cols = 3
    col_width = (POSTER_W - 2*BORDER_SIZE - 2*pad) // cols
    data = [
        (distance, "KM", "#000000"),
        (duration, "TIME", "#000000"),
        (pace_str, "/KM", "#000000") if pace_calculation else ("", "", "#000000")
    ]
    for i, (value, unit, color) in enumerate(data):
        x = BORDER_SIZE + pad + i * col_width
        bbox_v = draw.textbbox((0, 0), value, font=f_data)
        vw, vh = bbox_v[2]-bbox_v[0], bbox_v[3]-bbox_v[1]
        draw.text((x + (col_width - vw) // 2, y), value, font=f_data, fill=color)
        bbox_u = draw.textbbox((0, 0), unit, font=f_unit)
        uw, uh = bbox_u[2]-bbox_u[0], bbox_u[3]-bbox_u[1]
        draw.text((x + (col_width - uw) // 2, y + vh + 20), unit, font=f_unit, fill="#333333")

    # Vorschau und Download
    st.image(poster, caption="Vienna-Style GPX Poster")
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    st.download_button(
        "Poster herunterladen", 
        buf.getvalue(), 
        file_name=f"{event_name.replace(' ', '_')}_poster.png", 
        mime="image/png"
    )
