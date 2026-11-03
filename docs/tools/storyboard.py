"""Deseneaza storyboard-ul (schite) pentru documentul de la Tema 5.

python -I docs/tools/storyboard.py  ->  docs/storyboard/*.png
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "storyboard")
W, H = 960, 600
PAPER = (250, 247, 240)
INK = (45, 42, 38)
SOFT = (150, 144, 135)
OCHRE = (196, 132, 40)
GHOST = (170, 160, 150)
BLUE = (70, 110, 160)

rnd = random.Random(7)


def font(size, bold=False):
    names = ["segoeprb.ttf" if bold else "segoepr.ttf", "comic.ttf", "arial.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(os.path.join("C:/Windows/Fonts", n), size)
        except OSError:
            pass
    return ImageFont.load_default()


def jitter(p, a=1.6):
    return (p[0] + rnd.uniform(-a, a), p[1] + rnd.uniform(-a, a))


def line(d, a, b, col=INK, w=3, passes=2):
    # linie trasa de mana: doua treceri usor diferite, impartite in segmente
    for _ in range(passes):
        n = max(2, int(math.dist(a, b) / 40))
        pts = [jitter((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)) for i in range(n + 1)]
        d.line(pts, fill=col, width=w, joint="curve")


def poly(d, pts, col=INK, w=3, fill=None):
    if fill:
        d.polygon(pts, fill=fill)
    for i in range(len(pts)):
        line(d, pts[i], pts[(i + 1) % len(pts)], col, w)


def rect(d, x, y, w, h, col=INK, lw=3, fill=None):
    poly(d, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], col, lw, fill)


def curve(d, a, c, b, col=INK, w=3, dash=False):
    pts = []
    for i in range(31):
        t = i / 30
        pts.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
                    (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]))
    if dash:
        for i in range(0, 30, 2):
            d.line([pts[i], pts[i + 1]], fill=col, width=w)
    else:
        d.line([jitter(p, 0.8) for p in pts], fill=col, width=w, joint="curve")


def circle(d, c, r, col=INK, w=3, fill=None):
    if fill:
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=fill)
    pts = [jitter((c[0] + r * math.cos(t / 24 * 2 * math.pi), c[1] + r * math.sin(t / 24 * 2 * math.pi)), 1)
           for t in range(25)]
    d.line(pts, fill=col, width=w, joint="curve")


def text(d, xy, s, size=20, col=INK, bold=False, anchor="la"):
    d.text(xy, s, font=font(size, bold), fill=col, anchor=anchor)


def scribble(d, x, y, w, rows, col=SOFT):
    for i in range(rows):
        ww = w * (0.55 + 0.4 * rnd.random()) if i == rows - 1 else w
        line(d, (x, y + i * 12), (x + ww, y + i * 12), col, 2, 1)


def text_card(d, x, y, w=90, h=120, title="", fill=(255, 255, 252), col=INK, rows=5):
    rect(d, x, y, w, h, col, 3, fill)
    if title:
        text(d, (x + 8, y + 6), title, 15, col, True)
    scribble(d, x + 8, y + 32, w - 16, rows, SOFT if col == INK else col)


def image_card(d, x, y, w=110, h=85, col=INK, fill=(255, 255, 252)):
    rect(d, x, y, w, h, col, 3, fill)
    rect(d, x + 6, y + 6, w - 12, h - 12, col, 2)
    # munte + soare: semnul pentru "imagine"
    line(d, (x + 10, y + h - 12), (x + w * 0.4, y + h * 0.4), col, 2, 1)
    line(d, (x + w * 0.4, y + h * 0.4), (x + w * 0.6, y + h * 0.65), col, 2, 1)
    line(d, (x + w * 0.6, y + h * 0.65), (x + w * 0.75, y + h * 0.5), col, 2, 1)
    line(d, (x + w * 0.75, y + h * 0.5), (x + w - 10, y + h - 12), col, 2, 1)
    circle(d, (x + w * 0.75, y + h * 0.28), 7, col, 2)


def hand(d, x, y, pinch=True, flip=False, col=INK):
    # mana vazuta din spate, simplificata: palma + degete; pinch = aratator si degetul mare lipite
    s = -1 if flip else 1
    poly(d, [(x - 34 * s, y + 70), (x - 30 * s, y + 20), (x + 26 * s, y + 18), (x + 34 * s, y + 70)], col, 3,
         fill=(236, 226, 214))
    for i, dx in enumerate((-22, -8, 6)):
        top = y - 20 + i * 4
        line(d, (x + dx * s, y + 20), (x + dx * s + 2 * s, top + 10), col, 3)
    if pinch:
        line(d, (x + 20 * s, y + 20), (x + 26 * s, y - 6), col, 3)
        line(d, (x + 34 * s, y + 40), (x + 30 * s, y - 2), col, 3)
        circle(d, (x + 28 * s, y - 6), 6, OCHRE, 3)
    else:
        line(d, (x + 20 * s, y + 20), (x + 24 * s, y - 14), col, 3)
        line(d, (x + 34 * s, y + 46), (x + 50 * s, y + 20), col, 3)


def room(d, back=(170, 90, 790, 470)):
    # camera vazuta din fata: perete din spate + podea + tavan in perspectiva
    x0, y0, x1, y1 = back
    poly(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], SOFT, 2, fill=(244, 238, 226))
    for a, b in (((0, 0), (x0, y0)), ((W, 0), (x1, y0)), ((0, H), (x0, y1)), ((W, H), (x1, y1))):
        line(d, a, b, SOFT, 2, 1)
    # fereastra si usa, ca repere de scara
    rect(d, x1 - 150, y0 + 60, 110, 140, SOFT, 2)
    line(d, (x1 - 95, y0 + 60), (x1 - 95, y0 + 200), SOFT, 2, 1)


def frame(n, title, caption):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    return img, d


def finish(img, d, n, title, caption):
    rect(d, 6, 6, W - 12, H - 12, INK, 3)
    d.rectangle([12, 12, 330, 52], fill=PAPER)
    text(d, (24, 18), f"{n}. {title}", 24, INK, True)
    d.rectangle([12, H - 58, W - 12, H - 12], fill=(255, 250, 235))
    line(d, (12, H - 58), (W - 12, H - 58), INK, 2, 1)
    text(d, (24, H - 48), caption, 18, INK)
    img.save(os.path.join(OUT, f"{n:02d}.png"))


def note(d, xy, s, col=BLUE, size=17):
    text(d, xy, s, size, col)


def arrow(d, a, b, col=BLUE, w=2):
    line(d, a, b, col, w, 1)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for da in (2.6, -2.6):
        line(d, b, (b[0] + 14 * math.cos(ang + da), b[1] + 14 * math.sin(ang + da)), col, w, 1)


# ---------- cadrele ----------

def f01():
    img, d = frame(1, "", "")
    room(d)
    rect(d, 300, 150, 360, 270, INK, 3, fill=(255, 253, 246))
    text(d, (480, 176), "Storypinner", 34, INK, True, "ma")
    for i, (lbl, c) in enumerate((("Continua ultima camera", OCHRE), ("Alege alt folder", INK), ("Tutorial", INK))):
        rect(d, 340, 230 + i * 58, 280, 44, c, 3)
        text(d, (480, 252 + i * 58), lbl, 20, c, False, "mm")
    hand(d, 700, 420, pinch=False)
    arrow(d, (690, 400), (625, 255))
    note(d, (700, 290), "raza din mana,\npinch = click", size=16)
    finish(img, d, 1, "Main Menu", "Panou la 1.2 m in fata, inaltimea ochilor. Ultimul folder e preselectat; un pinch si esti in camera.")


def f02():
    img, d = frame(2, "", "")
    room(d)
    # raftul cu sertare
    rect(d, 220, 230, 230, 240, INK, 3, fill=(226, 208, 182))
    for i, lbl in enumerate(("Imagini  42", "Texte  17", "Carti  2")):
        rect(d, 235, 245 + i * 72, 200, 60, INK, 2)
        text(d, (335, 275 + i * 72), lbl, 18, INK, False, "mm")
    # sertar deschis, fisa trasa afara
    image_card(d, 520, 170, 140, 105, OCHRE)
    curve(d, (440, 270), (480, 200), (515, 215), BLUE, 2, dash=True)
    hand(d, 640, 270)
    note(d, (690, 250), "pinch pe fisa\nsi tragi afara\n= card nou", size=16)
    note(d, (230, 480), "sertar = tip de fisier\n(poke ca sa-l deschizi)", size=16)
    finish(img, d, 2, "Raftul", "Raftul sta langa birou. Fisierele de pe PC sunt pe tipuri; tragi una afara si devine card in camera.")


def f03():
    img, d = frame(3, "", "")
    room(d)
    image_card(d, 300, 160, 130, 100)
    text_card(d, 460, 150, 100, 130, "Cap. 3")
    # card in mana, umbra pe perete
    rect(d, 590, 215, 120, 95, GHOST, 2)
    image_card(d, 610, 240, 120, 92, OCHRE)
    hand(d, 735, 330)
    arrow(d, (640, 340), (612, 318))
    note(d, (520, 380), "sub 15 cm de perete:\napare umbra, cardul se lipeste\n(0.2 s, sunet de hartie)", size=16)
    text_card(d, 210, 300, 80, 100, "idee")
    note(d, (190, 410), "lasat in aer =\nramane plutind", size=16)
    finish(img, d, 3, "Lipire pe perete", "Cardurile se lipesc de perete sau raman in aer. Cu doua maini pe acelasi card il mari (0.5x - 3x).")


def f04():
    img, d = frame(4, "", "")
    room(d)
    text_card(d, 250, 170, 100, 130, "Scena 1")
    text_card(d, 420, 190, 100, 130, "Scena 2")
    text_card(d, 600, 160, 100, 130, "Scena 3")
    curve(d, (350, 235), (385, 220), (420, 250), OCHRE, 4)
    circle(d, (520, 255), 7, OCHRE, 3, fill=OCHRE)
    curve(d, (520, 255), (555, 330), (600, 230), OCHRE, 4)
    hand(d, 560, 360)
    note(d, (620, 380), "pinch pe marginea cardului,\ntragi pana la urmatorul card", size=16)
    note(d, (260, 120), "fir = ordinea lantului (1 -> 2 -> 3)", size=16)
    finish(img, d, 4, "Firul", "Firul ramane legat si cand muti cardurile. Mai multe fire unul dupa altul fac un lant.")


def f05():
    img, d = frame(5, "", "")
    room(d)
    for i, x in enumerate((210, 350, 490)):
        text_card(d, x, 160, 95, 125, f"Scena {i + 1}", fill=(255, 246, 225), col=OCHRE)
    curve(d, (305, 222), (330, 210), (350, 222), OCHRE, 4)
    curve(d, (445, 222), (470, 210), (490, 222), OCHRE, 4)
    # dropdown langa capatul lantului
    rect(d, 610, 150, 230, 230, INK, 3, fill=(255, 253, 246))
    text(d, (625, 160), "Ce face AI-ul?", 18, INK, True)
    items = ("Continua textul", "Scoate idei", "Scrie dialogul *", "Fa-l mai intunecat *", "+ prompt nou")
    for i, s in enumerate(items):
        y = 190 + i * 36
        rect(d, 622, y, 206, 30, OCHRE if i == 0 else SOFT, 2)
        text(d, (634, y + 15), s, 16, INK, False, "lm")
    hand(d, 860, 260, pinch=False, flip=True)
    note(d, (610, 390), "* = prompturile mele", size=16)
    note(d, (210, 300), "pinch pe un fir = selectezi tot lantul\n(contur ocru pe toate cardurile)", size=16)
    finish(img, d, 5, "Dropdown-ul", "Langa lantul selectat apare lista de actiuni. Poke pe o actiune o porneste.")


def f06():
    img, d = frame(6, "", "")
    room(d)
    for i, x in enumerate((210, 350, 490)):
        text_card(d, x, 180, 95, 125, f"Scena {i + 1}")
    curve(d, (305, 242), (330, 230), (350, 242), OCHRE, 6)
    curve(d, (445, 242), (470, 230), (490, 242), OCHRE, 6)
    for r in (16, 26, 36):
        circle(d, (640, 240), r, OCHRE, 2)
    text(d, (640, 300), "Continua textul...", 18, INK, False, "ma")
    note(d, (220, 350), "firele pulseaza cat se asteapta (2 - 10 s)\nmanile raman libere, poti muta alte carduri", size=16)
    note(d, (560, 360), "palma spre lant 1 s\n= anuleaza", size=16)
    finish(img, d, 6, "Asteptare", "Serverul primeste textele in ordine + actiunea. Dupa 30 s fara raspuns: 'Incearca din nou'.")


def f07():
    img, d = frame(7, "", "")
    room(d)
    for i, x in enumerate((150, 280)):
        text_card(d, x, 210, 90, 120, f"Scena {i + 2}")
    curve(d, (240, 270), (260, 260), (280, 270), OCHRE, 4)
    o = (370, 270)
    titles = ("A. Fuga prin padure", "B. Scrisoarea", "C. Cineva o asteapta")
    for i, (dy, t) in enumerate(zip((-150, 0, 150), titles)):
        end = (560, 270 + dy)
        curve(d, o, (460, 270 + dy * 0.2), (end[0], end[1] - 10 if dy else end[1]), GHOST, 3, dash=True)
        text_card(d, 560, 210 + dy, 170, 110, t, fill=(246, 243, 236), col=GHOST, rows=4)
    note(d, (750, 140), "3 ramuri\nsemitransparente", size=16)
    note(d, (750, 330), "titlu scurt +\ninceputul textului\n(pinch tinut = citesti\ntot, cardul se mareste)", size=16)
    finish(img, d, 7, "Trei drumuri", "Variantele ies din capatul lantului ca ramuri in evantai, la ~40 cm una de alta.")


def f08():
    img, d = frame(8, "", "")
    room(d)
    for i, x in enumerate((150, 280)):
        text_card(d, x, 210, 90, 120, f"Scena {i + 2}")
    curve(d, (240, 270), (260, 260), (280, 270), OCHRE, 4)
    curve(d, (370, 270), (400, 260), (430, 270), OCHRE, 4)
    text_card(d, 430, 205, 120, 130, "B. Scrisoarea", fill=(255, 246, 225), col=OCHRE)
    hand(d, 520, 360)
    # ramura aruncata
    text_card(d, 650, 150, 120, 90, "A.", fill=(246, 243, 236), col=GHOST, rows=3)
    hand(d, 820, 210, pinch=False, flip=True)
    arrow(d, (780, 200), (860, 160))
    note(d, (630, 260), "palma deschisa, gest\nde aruncat = dispare", size=16)
    note(d, (300, 445), "B devine card normal, legat de lant.\nSe salveaza in povestea-mea_continuare.txt", size=16)
    finish(img, d, 8, "Alegi un drum", "Ce pastrezi devine scena urmatoare si poti continua din ea. Originalele nu se schimba.")


def f09():
    img, d = frame(9, "", "")
    room(d)
    image_card(d, 380, 170, 180, 135, OCHRE)
    rect(d, 370, 315, 200, 50, SOFT, 2, fill=(255, 253, 246))
    scribble(d, 380, 330, 180, 2)
    for i, t in enumerate(("padure", "ceata", "turn", "noapte", "lup")):
        a = -math.pi * 0.95 + i * math.pi * 0.95 / 4
        c = (470 + 190 * math.cos(a), 240 + 120 * math.sin(a))
        circle(d, c, 30, BLUE if i == 2 else INK, 3, fill=(255, 253, 246))
        text(d, c, t, 15, INK, False, "mm")
    circle(d, (600, 300), 18, OCHRE, 3, fill=(255, 246, 225))
    text(d, (600, 300), "+", 26, OCHRE, True, "mm")
    line(d, (560, 290), (582, 298), OCHRE, 2, 1)
    note(d, (640, 330), "+ = sugestii\n(imagini, idei, fisiere)", size=16)
    note(d, (180, 380), "poke pe 'turn' -> alte imagini cu turn,\ntaguri care apar des cu el, texte cu cuvantul", size=16)
    finish(img, d, 9, "Imagine, taguri si +", "Poke pe o imagine: descrierea apare sub ea, tagurile in arc deasupra.")


def f10():
    img, d = frame(10, "", "")
    room(d)
    # cartea deschisa pe birou si scenele scoase din ea
    poly(d, [(170, 420), (260, 400), (350, 420), (350, 450), (260, 432), (170, 450)], INK, 3, fill=(255, 250, 238))
    line(d, (260, 400), (260, 432), INK, 2, 1)
    xs = (300, 410, 520, 630, 740)
    for i, x in enumerate(xs):
        y = 300 - i * 30
        text_card(d, x, y, 80, 70, f"S{i + 1}", rows=2)
        if i:
            curve(d, (xs[i - 1] + 80, y + 65), (x - 10, y + 50), (x, y + 35), OCHRE, 3)
    curve(d, (300, 400), (290, 360), (300, 340), BLUE, 2, dash=True)
    note(d, (380, 380), "scenele ies din carte, in ordine, deja legate:\ntitlu, personaje, loc, o fraza", size=16)
    finish(img, d, 10, "Cartea ca lant", "Drumul de scene urca prin camera. Pe ultimul card merge acelasi dropdown.")


def plan():
    # vedere de sus a camerei, cu dimensiuni: referinta pentru graybox
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    s = 120  # px pe metru
    ox, oy = 150, 80
    rw, rd = 4.0, 3.2
    rect(d, ox, oy, rw * s, rd * s, INK, 4)
    text(d, (ox + rw * s / 2, oy - 30), "4.00 m", 18, BLUE, False, "ma")
    text(d, (ox - 70, oy + rd * s / 2), "3.20 m", 18, BLUE, False, "lm")
    # fereastra pe peretele de sus, usa jos-dreapta
    line(d, (ox + 1.4 * s, oy), (ox + 2.6 * s, oy), BLUE, 8, 1)
    text(d, (ox + 2.0 * s, oy + 10), "fereastra", 15, BLUE, False, "ma")
    curve(d, (ox + 3.1 * s, oy + rd * s), (ox + 3.1 * s, oy + rd * s - 0.85 * s), (ox + 3.95 * s, oy + rd * s), SOFT, 2)
    text(d, (ox + 3.5 * s, oy + rd * s - 40), "usa", 15, SOFT, False, "ma")
    items = [
        ("birou 1.2 x 0.6", 1.4, 0.05, 1.2, 0.6),
        ("pat 2.0 x 0.9", 0.05, 1.2, 0.9, 2.0),
        ("dulap", 3.35, 0.4, 0.6, 1.0),
        ("raft", 2.75, 0.05, 0.35, 1.0),
    ]
    for lbl, x, y, w, h in items:
        rect(d, ox + x * s, oy + y * s, w * s, h * s, INK, 2, fill=(236, 226, 214))
        text(d, (ox + (x + w / 2) * s, oy + (y + h / 2) * s), lbl, 13, INK, False, "mm")
    circle(d, (ox + 2.0 * s, oy + 0.95 * s), 0.25 * s, INK, 2)
    text(d, (ox + 2.0 * s, oy + 0.95 * s), "scaun", 13, INK, False, "mm")
    # zona de joc
    rect(d, ox + 1.2 * s, oy + 1.3 * s, 2.0 * s, 1.6 * s, OCHRE, 2)
    text(d, (ox + 2.2 * s, oy + 2.1 * s), "zona libera\n2.0 x 1.6 m\n(guardian)", 15, OCHRE, False, "mm")
    note(d, (660, 90), "inaltime 2.60 m\nfereastra: 1.2 x 1.4 m, la 0.9 m\nusa: 0.85 x 2.05 m\n\ncarduri pe peretele\nde sus si cel din dreapta,\nintre 0.9 si 2.0 m\n\n(dimensiuni de verificat\ncu ruleta)", size=16)
    finish(img, d, 11, "Planul camerei", "Vedere de sus a camerei de acasa, la scara. Referinta pentru graybox (Blender).")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in (f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, plan):
        f()
    print("ok", len(os.listdir(OUT)))
