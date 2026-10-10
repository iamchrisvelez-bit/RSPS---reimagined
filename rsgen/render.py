"""Tiny numpy z-buffer rasterizer for flat-shaded previews."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _rx(d):
    a = math.radians(d)
    return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])


def _ry(d):
    a = math.radians(d)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


def background(w, h):
    y, x = np.mgrid[0:h, 0:w]
    r = np.sqrt(((x - w / 2) / w) ** 2 + ((y - h * 0.45) / h) ** 2)
    v = np.clip(46 - r * 40, 18, 46)
    img = np.stack([v * 0.95, v, v * 1.08], -1)
    return img


def render(V, F, cols, glow=None, size=480, yaw=-32, pitch=16, ss=3, fill=0.84, bg=None, smooth=False,
           layers=None):
    W = H = size * ss
    R = _rx(pitch) @ _ry(yaw)
    P = np.asarray(V, float) @ R.T
    lo, hi = P.min(0), P.max(0)
    c = (lo + hi) / 2
    s = fill * W / max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)
    X = (P[:, 0] - c[0]) * s + W / 2
    Y = H / 2 - (P[:, 1] - c[1]) * s
    Z = P[:, 2]

    img = background(W, H) if bg is None else bg.copy()
    zbuf = np.full((H, W), -1e9)
    T = P[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    L = np.array([-0.45, 0.75, 0.55]); L /= np.linalg.norm(L)
    L2 = np.array([0.7, 0.1, -0.3]); L2 /= np.linalg.norm(L2)
    diff = np.clip(n @ L, 0, 1)
    rim = np.clip(n @ L2, 0, 1)
    shade = 0.42 + 0.72 * diff + 0.18 * rim
    vshade = None
    if smooth:  # Gouraud, like RS render type 0: light per vertex normal, interpolate across the face
        vn = np.zeros((len(P), 3))
        an = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])  # area-weighted face normals
        for k in range(3):
            np.add.at(vn, np.asarray(F)[:, k], an)
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
        vshade = 0.42 + 0.72 * np.clip(vn @ L, 0, 1) + 0.18 * np.clip(vn @ L2, 0, 1)
    # detail-layer faces (decals) win depth ties against the surface, like a higher RS priority
    zbias = np.zeros(len(F)) if layers is None or len(layers) != len(F) else np.asarray(layers, float) * 1e-3
    cols = np.asarray(cols, float)
    glow = np.zeros(len(F), bool) if glow is None else np.asarray(glow, bool)
    shade = np.where(glow, np.maximum(shade, 1.05), shade)
    fc = np.clip(cols * shade[:, None], 0, 255)

    for i, (a, b, cc) in enumerate(F):
        if n[i, 2] <= 0:  # back-face cull, as the RS client does
            continue
        xs, ys = (X[a], X[b], X[cc]), (Y[a], Y[b], Y[cc])
        x0, x1 = int(max(0, math.floor(min(xs)))), int(min(W - 1, math.ceil(max(xs))))
        y0, y1 = int(max(0, math.floor(min(ys)))), int(min(H - 1, math.ceil(max(ys))))
        if x1 < x0 or y1 < y0:
            continue
        gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
        ax, ay, bx, by, cx, cy = xs[0], ys[0], xs[1], ys[1], xs[2], ys[2]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        z = w0 * Z[a] + w1 * Z[b] + w2 * Z[cc] + zbias[i]
        zb = zbuf[y0:y1 + 1, x0:x1 + 1]
        m &= z > zb
        zb[m] = z[m]
        if vshade is not None and not glow[i]:
            sh = w0 * vshade[a] + w1 * vshade[b] + w2 * vshade[cc]
            img[y0:y1 + 1, x0:x1 + 1][m] = np.clip(cols[i][None, :] * sh[m][:, None], 0, 255)
        else:
            img[y0:y1 + 1, x0:x1 + 1][m] = fc[i]

    # soft glow bloom for emissive faces
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    if glow.any():
        gimg = np.zeros((H, W, 3))
        gm = np.zeros(len(F), bool)
        gm[:] = glow
        # cheap: re-mask pixels whose colour is very saturated-bright
        arr = np.asarray(out).astype(float)
        bright = (arr.max(-1) > 200) & ((arr.max(-1) - arr.min(-1)) > 90)
        gimg[bright] = arr[bright]
        bloom = Image.fromarray(gimg.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6 * ss))
        out = Image.fromarray(np.clip(np.asarray(out).astype(float) + np.asarray(bloom).astype(float) * 0.6,
                                      0, 255).astype(np.uint8))
    return out.resize((size, size), Image.LANCZOS)


def _font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def label(img, text, sub=None):
    d = ImageDraw.Draw(img)
    d.text((12, 8), text, fill=(240, 240, 240), font=_font(20))
    if sub:
        d.text((12, img.height - 28), sub, fill=(170, 170, 175), font=_font(15))
    return img


def sheet(tiles, cols, tile=320, title=None):
    rows = math.ceil(len(tiles) / cols)
    top = 44 if title else 0
    out = Image.new('RGB', (cols * tile, rows * tile + top), (22, 22, 26))
    d = ImageDraw.Draw(out)
    if title:
        d.text((12, 10), title, fill=(255, 255, 255), font=_font(24))
    for i, t in enumerate(tiles):
        out.paste(t.resize((tile, tile), Image.LANCZOS), ((i % cols) * tile, top + (i // cols) * tile))
    return out


def render_rgba(V, F, cols, size=256, yaw=-32, pitch=16, ss=2, smooth=False, layers=None):
    """Transparent-background render (no bloom), cropped to the model."""
    W = size * ss
    bg = np.zeros((W, W, 3))
    probe = np.full((W, W, 3), 255.0)
    kw = dict(size=W, yaw=yaw, pitch=pitch, ss=1, fill=0.96, smooth=smooth, layers=layers)
    a = np.asarray(render(V, F, cols, None, bg=bg, **kw))
    b = np.asarray(render(V, F, cols, None, bg=probe, **kw))
    # a pixel is model-covered when it is the same on both backgrounds
    alpha = (np.abs(a.astype(int) - b.astype(int)).max(-1) == 0).astype(np.uint8) * 255
    img = Image.fromarray(np.dstack([a, alpha]).astype(np.uint8), 'RGBA')
    box = img.getbbox()
    return img.crop(box) if box else img


OUTLINE = (0, 0, 1, 255)      # client item outline colour 0x000001
SHADOW = (0x30, 0x20, 0x20, 255)  # client item drop-shadow colour 0x302020


def item_sprite(rgba, w=36, h=32):
    """Downscale a model render into a client-style inventory sprite:
    hard alpha, 1px outline on the 4 neighbours, shadow to the bottom-right."""
    iw, ih = rgba.size
    k = min((w - 4) / iw, (h - 4) / ih)
    small = rgba.resize((max(1, round(iw * k)), max(1, round(ih * k))), Image.LANCZOS)
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.paste(small, ((w - small.width) // 2 - 1, (h - small.height) // 2 - 1), small)
    px = np.array(canvas)
    solid = px[..., 3] >= 128
    px[..., 3] = np.where(solid, 255, 0)
    px[~solid, :3] = 0
    out = px.copy()
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nb = np.roll(np.roll(solid, dy, 0), dx, 1)
        ring_ = nb & ~solid & (out[..., 3] == 0)
        out[ring_] = OUTLINE
    filled = out[..., 3] > 0
    sh = np.roll(np.roll(filled, 1, 0), 1, 1) & ~filled
    out[sh] = SHADOW
    return Image.fromarray(out, 'RGBA')
