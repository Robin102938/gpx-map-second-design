import io, math
import gpxpy, streamlit as st
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont

# ——— Konfiguration ———
MAX_SPEED_M_S   = 10      # maximal erlaubte Geschwindigkeit (m/s)
MIN_DT_S        = 1       # minimale Zeitdifferenz (s)
MAX_PTS_DISPLAY = 2000    # Sampling-Limit

# Postergrößen (Quadratische Karte)
POSTER_W = 2480
POSTER_H = 3800  # erhöht für mehr Footer-Platz
MAP_SIZE = 2480  # quadratisch
PAD = 200        # Innenabstand

st.set_page_config(layout="wide")
st.title("GPX Map Poster – Square Design")

# ——— Sidebar Einstellungen ———
st.sidebar.header("🎨 Farben & Stil")
route_color        = st.sidebar.color_picker("Streckenfarbe", "#FF5500")
route_shadow_color = st.sidebar.color_picker("Schattenfarbe", "#CCCCCC")
start_color        = st.sidebar.color_picker("Startpunkt", "#00AA00")
end_color          = st.sidebar.color_picker("Zielpunkt", "#CC0000")
map_style = st.sidebar.selectbox(
    "Kartenstil",
    ["CartoDB Positron (Light)", "CartoDB Dark Matter", "OSM Standard"]
)

# Tile-Template je Stil
if map_style == "CartoDB Positron (Light)":
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
elif map_style == "CartoDB Dark Matter":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
else:
    TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# ——— Input ———
gpx_file   = st.file_uploader("GPX-Datei hochladen", type="gpx")
event_name = st.text_input("Name des Laufs (z. B. Berlin Marathon)")
run_date   = st.date_input("Datum")

distance_opt = st.selectbox("Distanz", ["5 km","10 km","21,0975 km","42,195 km","Andere…"])
if distance_opt == "Andere…":
    distance = st.text_input("Eigene Distanz (z.B. '15 km')")
else:
    distance = distance_opt

runner = st.text_input("Name des Läufers")
bib_no = st.text_input("Startnummer (# automatisch davor)")
duration = st.text_input("Zeit (HH:MM:SS)")

# ——— Poster erzeugen ———
if st.button("Poster erstellen") and gpx_file and event_name and runner and duration:
    # 1) GPX parse + Filter
    gpx = gpxpy.parse(gpx_file)
    pts_raw = [(pt.longitude, pt.latitude, pt.time)
               for tr in gpx.tracks for seg in tr.segments for pt in seg.points]
    if len(pts_raw) < 2:
        st.error("Kein Track gefunden.")
        st.stop()
    # Filtern schneller Ausreißer
    def hav(a,b):
        lon1,lat1,lon2,lat2 = map(math.radians,(a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))
    clean=[pts_raw[0]]
    for a,b,t in zip(pts_raw, pts_raw[1:], pts_raw[1:]):
        dist = hav(a,b)
        dt = (b[2]-a[2]).total_seconds()
        if dt>=MIN_DT_S and dist/dt <= MAX_SPEED_M_S:
            clean.append(b)
    coords=[(lon,lat) for lon,lat,_ in clean]
    # Sampling
    if len(coords)>MAX_PTS_DISPLAY:
        step = len(coords)//MAX_PTS_DISPLAY+1
        coords = coords[::step]

    # 2) Karte quadratisch rendern
    m = StaticMap(MAP_SIZE, MAP_SIZE, url_template=TILE)
    m.add_line(Line(coords, color=route_shadow_color, width=16))
    m.add_line(Line(coords, color=route_color, width=6))
    m.add_marker(CircleMarker(coords[0], start_color, 30))
    m.add_marker(CircleMarker(coords[-1], end_color, 30))
    map_img = m.render(zoom=14)

    # 3) Poster Canvas
    poster = Image.new("RGB", (POSTER_W, POSTER_H), "white")
    # Schrift
    try:
        f_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
        f_sub   = ImageFont.truetype("DejaVuSans.ttf", 80)
        f_meta  = ImageFont.truetype("DejaVuSans.ttf", 100)
    except:
        f_title = f_sub = f_meta = ImageFont.load_default()
    draw = ImageDraw.Draw(poster)

    y = PAD
    # Titel
    title = event_name.upper()
    bbox = draw.textbbox((0,0), title, font=f_title)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((POSTER_W-tw)/2, y), title, font=f_title, fill="#000")
    y += th + 50  # mehr Abstand zwischen Titel und Datum
    # Datum darunter
    date_str = run_date.strftime('%d %B %Y')
    bbox_d = draw.textbbox((0,0), date_str, font=f_sub)
    dw, dh = bbox_d[2]-bbox_d[0], bbox_d[3]-bbox_d[1]
    draw.text(((POSTER_W-dw)/2, y), date_str, font=f_sub, fill="#333")
    y += dh + PAD

    # Map in Mitte
    poster.paste(map_img, ((POSTER_W-MAP_SIZE)//2, y))
    y += MAP_SIZE + PAD

                # Footer-Zeilen im neuen Layout
    # Laufender Name + Bibnummer rechtsbündig (fett)
    try:
        f_bold_meta = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
    except:
        f_bold_meta = f_meta
    line1 = f"{runner.upper()}   #{bib_no.strip()}"
    bbox1 = draw.textbbox((0,0), line1, font=f_bold_meta)
    w1, h1 = bbox1[2]-bbox1[0], bbox1[3]-bbox1[1]
    x1 = POSTER_W - PAD - w1
    draw.text((x1, y), line1, font=f_bold_meta, fill="#000000")
    # mehr Abstand vor Unterstreichung
    y += h1 + 50
    # Unterstreichung
    draw.line((PAD, y, POSTER_W-PAD, y), fill="#000000", width=3)
    y += 40
    # Distanz & Zeit untereinander, rechtsbündig, mit kleiner Schrift
    try:
        f_val = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
        f_lbl = ImageFont.truetype("DejaVuSans.ttf", 60)
    except:
        f_val = f_lbl = ImageFont.load_default()
    # Distanz rechtsbündig
    val1 = distance
    bbox_val1 = draw.textbbox((0,0), val1, font=f_val)
    wv1, hv1 = bbox_val1[2]-bbox_val1[0], bbox_val1[3]-bbox_val1[1]
    x_val = POSTER_W - PAD - wv1
    draw.text((x_val, y), val1, font=f_val, fill="#000000")
    # km-Label darunter
    unit1 = "km" if "km" in distance.lower() else "mi"
    bbox_lbl1 = draw.textbbox((0,0), unit1, font=f_lbl)
    wlbl1, hlbl1 = bbox_lbl1[2]-bbox_lbl1[0], bbox_lbl1[3]-bbox_lbl1[1]
    draw.text((x_val, y+hv1+10), unit1, font=f_lbl, fill="#333333")
    # Zeit rechtsbündig
    val2 = duration
    bbox_val2 = draw.textbbox((0,0), val2, font=f_val)
    wv2, hv2 = bbox_val2[2]-bbox_val2[0], bbox_val2[3]-bbox_val2[1]
    x_time = POSTER_W - PAD - wv2
    draw.text((x_time, y), val2, font=f_val, fill="#000000")
    # TIME-Label darunter
    unit2 = "TIME"
    bbox_lbl2 = draw.textbbox((0,0), unit2, font=f_lbl)
    wlbl2, hlbl2 = bbox_lbl2[2]-bbox_lbl2[0], bbox_lbl2[3]-bbox_lbl2[1]
    draw.text((x_time, y+hv2+10), unit2, font=f_lbl, fill="#333333")
    # 4) Download
    buf = io.BytesIO(); poster.save(buf, format="PNG")
    st.download_button("Download Poster", buf.getvalue(), file_name="poster.png", mime="image/png")
    buf = io.BytesIO(); poster.save(buf, format="PNG")
    st.download_button("Download Poster", buf.getvalue(), file_name="poster.png", mime="image/png")
    buf = io.BytesIO(); poster.save(buf, format="PNG")
    st.download_button("Download Poster", buf.getvalue(), file_name="poster.png", mime="image/png")
