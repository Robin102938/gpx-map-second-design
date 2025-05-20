import io, math
import gpxpy, streamlit as st
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont

# ——— Konfiguration ———
MAX_SPEED_M_S   = 10      # >36 km/h filtern
MIN_DT_S        = 1       # mind. 1 s
MAX_PTS_DISPLAY = 2000    # Sampling-Limit
# Karte etwas kleiner für mehr Footer
MAP_W, MAP_H    = 2480, 3000
PAD_HORIZ       = 200     # horizontaler Seitenrand
PAD_VERT        = 40      # vertikaler Abstand
BOTTOM_EXTRA    = 300     # zusätzlicher Unterkante-Puffer

st.set_page_config(layout="wide")
st.title("🏃‍ GPX-Map Generator – Print-Ready")

# ——— Farbauswahl (Sidebar) ———
st.sidebar.header("🎨 Farb-Settings")
color_swatches = {
    "⬛": "#000000", "⬜": "#FFFFFF",
    "🟩": "#00FF00", "🟥": "#FF0000",
    "🟦": "#0000FF", "🟨": "#FFFF00",
    "🟪": "#FF00FF", "🟧": "#FFA500"
}
def choose_color_grid(label, default_hex):
    st.sidebar.text(label)
    options = list(color_swatches.keys())
    options.append("❓")
    default_key = next((k for k,v in color_swatches.items() if v==default_hex), "⬛")
    idx = options.index(default_key) if default_key in options else 0
    choice = st.sidebar.radio("", options, index=idx, key=f"radio_{label}")
    if choice == "❓":
        return st.sidebar.color_picker(f"Custom {label}", default_hex)
    return color_swatches[choice]
route_color        = choose_color_grid("Streckenfarbe", "#000000")
route_shadow_color = choose_color_grid("Schattenfarbe der Strecke", "#CCCCCC")
start_color        = choose_color_grid("Startpunkt-Farbe", "#00b300")
end_color          = choose_color_grid("Zielpunkt-Farbe", "#e60000")
footer_bg_color    = choose_color_grid("Footer Hintergrund", "#FFFFFF")
footer_text_color  = choose_color_grid("Footer Haupttext", "#000000")
footer_meta_color  = choose_color_grid("Footer Metatext", "#555555")

# ——— Kartenstil (Sidebar) ———
st.sidebar.header("🗺 Kartenstil")
map_style = st.sidebar.selectbox(
    "Kartenstil auswählen",
    ["CartoDB Positron (Light)", "CartoDB Dark Matter", "OpenStreetMap Standard"]
)
if map_style == "CartoDB Positron (Light)":
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
elif map_style == "CartoDB Dark Matter":
    TILE = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
else:
    TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# ——— Eingaben ———
gpx_file    = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
event_name  = st.text_input("Name des Laufs / Events")
run_date    = st.date_input("Datum des Laufs")
distance_opt = st.selectbox(
    "Distanz auswählen",
    ["5 km", "10 km", "21,0975 km", "42,195 km", "Andere…"]
)
if distance_opt == "Andere…":
    custom_dist = st.text_input("Eigene Distanz (z.B. '15 km')")
    distance = custom_dist.strip() or distance_opt
else:
    distance = distance_opt
city     = st.text_input("Stadt")
bib_no   = st.text_input("Startnummer (ohne #)")
runner   = st.text_input("Dein Name")
duration = st.text_input("Zeit (HH:MM:SS)")

# ——— Poster erzeugen ———
if st.button("Poster erzeugen") and gpx_file and event_name and runner and duration:
    # GPX parse
    gpx = gpxpy.parse(gpx_file)
    raw = [(pt.longitude, pt.latitude, pt.elevation, pt.time)
           for tr in gpx.tracks for seg in tr.segments for pt in seg.points
           if pt.time and pt.elevation is not None]
    if len(raw) < 2:
        st.error("Zu wenige valide GPX-Daten.")
        st.stop()
    # Ausreißer filtern
    def hav(a, b):
        lon1,lat1,lon2,lat2 = map(math.radians, (a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))
    clean = [raw[0]]
    for prev, curr in zip(raw, raw[1:]):
        dist = hav(prev, curr)
        dt = (curr[3] - prev[3]).total_seconds()
        if dt < MIN_DT_S or (dist / dt) > MAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean) < 2:
        st.error("Kein gültiger Track nach Filter.")
        st.stop()
    # Sampling
    pts = [(lon, lat) for lon, lat, _, _ in clean]
    if len(pts) > MAX_PTS_DISPLAY:
        step = len(pts) // MAX_PTS_DISPLAY + 1
        pts = pts[::step]
    # Karte rendern
    m = StaticMap(MAP_W, MAP_H, url_template=TILE)
    m.add_line(Line(pts, color=route_shadow_color, width=14))  # dünnerer Schatten
    m.add_line(Line(pts, color=route_color, width=8))         # dünnere Hauptlinie
    m.add_marker(CircleMarker(pts[0], start_color, 30))
    m.add_marker(CircleMarker(pts[-1], end_color, 30))
    map_img = m.render(zoom=14)
    st.image(map_img, use_container_width=True)
    # Footer dynamic font sizes
    base_size = 160
    max_width = MAP_W - 2 * PAD_HORIZ
    try:
        font_path_bold = "DejaVuSans-Bold.ttf"
        size = base_size
        f_event = ImageFont.truetype(font_path_bold, size)
        tmp_img = Image.new("RGB", (1,1)); tmp_draw = ImageDraw.Draw(tmp_img)
        ev_text = event_name.upper()
        bbox = tmp_draw.textbbox((0,0), ev_text, font=f_event)
        while (bbox[2] - bbox[0] > max_width) and size > 10:
            size -= 2
            f_event = ImageFont.truetype(font_path_bold, size)
            bbox = tmp_draw.textbbox((0,0), ev_text, font=f_event)
        f_info = ImageFont.truetype("DejaVuSans.ttf", 100)
        f_meta = ImageFont.truetype("DejaVuSans.ttf", 100)
    except:
        f_event = f_info = f_meta = ImageFont.load_default()
    top_line = event_name.upper()
    mid_line = city
    date_line = f"{run_date.strftime('%d.%m.%Y')} - {distance}"
    bot_line = f"#{bib_no.strip()} - {runner} - {duration}"
    tmp = Image.new('RGB', (1,1)); dtmp = ImageDraw.Draw(tmp)
    be = dtmp.textbbox((0,0), top_line, font=f_event)
    bm1 = dtmp.textbbox((0,0), mid_line, font=f_info)
    bm2 = dtmp.textbbox((0,0), date_line, font=f_info)
    bm3 = dtmp.textbbox((0,0), bot_line, font=f_meta)
    footer_h = (be[3]-be[1]) + PAD_VERT + (bm1[3]-bm1[1]) + PAD_VERT + 3 + PAD_VERT + (bm2[3]-bm2[1]) + PAD_VERT + (bm3[3]-bm3[1]) + BOTTOM_EXTRA
    poster = Image.new("RGB", (MAP_W, MAP_H + footer_h), footer_bg_color)
    poster.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(poster)
    y = MAP_H + PAD_VERT
    # Event
    w_e, h_e = be[2]-be[0], be[3]-be[1]
    draw.text(((MAP_W-w_e)/2, y), top_line, font=f_event, fill=footer_text_color)
    y += h_e + PAD_VERT
    # City
    w_c, h_c = bm1[2]-bm1[0], bm1[3]-bm1[1]
    draw.text(((MAP_W-w_c)/2, y), mid_line, font=f_info, fill=footer_meta_color)
    y += h_c + PAD_VERT
    # Separator
    draw.line((PAD_HORIZ, y, MAP_W-PAD_HORIZ, y), fill=footer_meta_color, width=3)
    y += PAD_VERT
    # Date-Line
    w_d, h_d = bm2[2]-bm2[0], bm2[3]-bm2[1]
    draw.text(((MAP_W-w_d)/2, y), date_line, font=f_info, fill=footer_meta_color)
    y += h_d + PAD_VERT
    # Bot-Line
    w_b, h_b = bm3[2]-bm3[0], bm3[3]-bm3[1]
    draw.text(((MAP_W-w_b)/2, y), bot_line, font=f_meta, fill=footer_text_color)
    # Download
    buf = io.BytesIO(); poster.save(buf, format="PNG")
    st.download_button(label="📥 Poster herunterladen", data=buf.getvalue(), file_name="running_poster.png", mime="image/png", key="poster_download")
