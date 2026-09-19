import os
import io
import uuid
import random
import requests
import time
import base64
import numpy as np
from scipy import ndimage
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont, ImageColor, ImageOps
from rembg import remove as rembg_remove, new_session

app = FastAPI(title="Zanimo Hyper Automation Image Generator")

MEDIA_DIR = "/data/media"
SCENES_DIR = os.path.join(MEDIA_DIR, "scenes")
OUTPUTS_DIR = os.path.join(MEDIA_DIR, "outputs")
LOGO_PATH = "/app/logo.png"

os.makedirs(SCENES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
CLOUDFLARE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_MODEL}"

MAX_PROMPT_CHARS = 900

_rembg_session = new_session("isnet-general-use")


class SceneInput(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 1080
    height: int = 1350
    position: str = ""


class ProductInfo(BaseModel):
    image_url: str
    id: str = "unknown"
    name: str = "product"


class ComposeInput(BaseModel):
    product: ProductInfo
    promo: str = ""
    tagline: str = ""
    tagline_color: str = ""
    scene_image_path: str
    position: str
    scale: float
    y: float


def download_image(url: str) -> Image.Image:
    try:
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (ZanimoBot/1.0)"},
        )
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur téléchargement image {url}: {str(e)}")


def remove_background(img: Image.Image) -> Image.Image:
    try:
        result = rembg_remove(
            img,
            session=_rembg_session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=5,
        ).convert("RGBA")

        rgb = np.array(img.convert("RGB"))
        alpha = np.array(result.split()[-1])

        mask = alpha > 25
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_erosion(mask, structure=np.ones((3, 3)), iterations=2)

        new_alpha = (mask * 255).astype(np.uint8)
        new_alpha = np.array(Image.fromarray(new_alpha).filter(ImageFilter.GaussianBlur(1)))

        result = Image.fromarray(np.dstack([rgb, new_alpha]), "RGBA")
        bbox = result.getbbox()
        if bbox:
            result = result.crop(bbox)
        return result
    except Exception:
        return img.convert("RGBA")


def create_floor_shadow(width: int, height: int) -> Image.Image:
    shadow_blur = 15
    shadow_img = Image.new(
        "RGBA",
        (width + shadow_blur * 2, height // 4 + shadow_blur * 2),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(shadow_img)
    draw.ellipse(
        [shadow_blur, shadow_blur, width + shadow_blur, height // 4 + shadow_blur],
        fill=(0, 0, 0, 90),
    )
    return shadow_img.filter(ImageFilter.GaussianBlur(shadow_blur))


def add_logo(background: Image.Image):
    if not os.path.exists(LOGO_PATH):
        return background, 0, 0
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_size = int(background.width * 0.20)
        aspect = logo.width / logo.height
        logo_h = int(logo_size / aspect)
        logo = logo.resize((logo_size, logo_h), Image.Resampling.LANCZOS)
        background.alpha_composite(logo, (18, 18))
        return background, logo_size, logo_h
    except Exception as e:
        print(f"Logo error: {e}")
        return background, 0, 0


BADGE_STAR_PATH = "/app/fonts/badge_star.png"


def add_promo_badge(background: Image.Image, promo: str) -> Image.Image:
    promo = promo.strip()
    if not promo:
        return background
    try:
        bg_w, bg_h = background.size
        draw = ImageDraw.Draw(background)
        margin = int(bg_w * 0.07)
        max_line_w = int(bg_w * 0.75) - margin

        promo_stripped = promo.replace("%", "").replace("-", "").strip()
        is_percent_only = promo_stripped.replace(",", "").replace(".", "").isdigit()

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        def build_font(size):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                return ImageFont.load_default()

        if is_percent_only and os.path.exists(BADGE_STAR_PATH):
            badge_text = f"-{promo_stripped}%"
            badge = Image.open(BADGE_STAR_PATH).convert("RGBA")
            badge_bbox = badge.getbbox()
            if badge_bbox:
                badge = badge.crop(badge_bbox)

            badge_w = int(bg_w * 0.40)
            aspect = badge.width / badge.height
            badge_h = int(badge_w / aspect)
            badge_resized = badge.resize((badge_w, badge_h), Image.Resampling.LANCZOS)

            badge_margin_x = int(bg_w * 0.02)
            badge_x = bg_w - badge_w - badge_margin_x
            badge_y = 40
            background.alpha_composite(badge_resized, (badge_x, badge_y))

            safe_w = badge_w * 0.55
            safe_h = badge_h * 0.55
            font_size = int(badge_h * 0.30)
            font_big = build_font(font_size)
            bb = draw.textbbox((0, 0), badge_text, font=font_big)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            min_font_size = 10
            while (tw > safe_w or th > safe_h) and font_size > min_font_size:
                font_size -= 2
                font_big = build_font(font_size)
                bb = draw.textbbox((0, 0), badge_text, font=font_big)
                tw, th = bb[2] - bb[0], bb[3] - bb[1]

            tx = badge_x + (badge_w - tw) // 2
            ty = badge_y + (badge_h - th) // 2 - bb[1]
            draw.text((tx, ty), badge_text, font=font_big, fill=(255, 255, 255, 255))
            return background

        def wrap_to_width(words, font):
            wrapped = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                bb = draw.textbbox((0, 0), candidate, font=font)
                if bb[2] - bb[0] <= max_line_w or not current:
                    current = candidate
                else:
                    wrapped.append(current)
                    current = word
            if current:
                wrapped.append(current)
            return wrapped

        if is_percent_only:
            words = [f"-{promo_stripped}%"]
            font_size = int(bg_w * 0.16)
            min_font_size = int(bg_w * 0.020)
        else:
            words = promo.split()
            word_count = len(words)
            if word_count <= 2:
                font_size = int(bg_w * 0.055)
            elif word_count <= 9:
                font_size = int(bg_w * 0.053)
            else:
                font_size = int(bg_w * 0.052)
            min_font_size = int(bg_w * 0.030)

        font_big = build_font(font_size)
        lines = wrap_to_width(words, font_big)
        widest = max((draw.textbbox((0, 0), line, font=font_big)[2] for line in lines), default=0)
        while widest > max_line_w and font_size > min_font_size:
            font_size -= 2
            font_big = build_font(font_size)
            lines = wrap_to_width(words, font_big)
            widest = max((draw.textbbox((0, 0), line, font=font_big)[2] for line in lines), default=0)

        if len(lines) > 4:
            lines = lines[:4]
            lines[-1] = lines[-1].rstrip(".,;: ") + "…"

        line_heights = []
        line_widths = []
        for line in lines:
            bb = draw.textbbox((0, 0), line, font=font_big)
            line_widths.append(bb[2] - bb[0])
            line_heights.append(bb[3] - bb[1])
        line_spacing = int(font_size * 0.30)
        y = margin

        for line, line_w, line_h in zip(lines, line_widths, line_heights):
            x = bg_w - line_w - margin

            for offset in range(6, 0, -1):
                alpha = int(180 * (offset / 6))
                draw.text((x + offset, y + offset), line, font=font_big, fill=(120, 80, 0, alpha))

            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
                draw.text((x + ox, y + oy), line, font=font_big, fill=(180, 120, 0, 255))

            draw.text((x, y), line, font=font_big, fill=(255, 215, 0, 255))

            y += line_h + line_spacing

    except Exception as e:
        print(f"Promo badge error: {e}")
    return background


TAGLINE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TAGLINE_DEFAULT_COLOR = (255, 255, 255, 255)


def add_tagline_badge(background: Image.Image, tagline: str, tagline_color: str = "", logo_zone=None) -> Image.Image:
    tagline = (tagline or "").strip()
    if not tagline:
        return background

    try:
        try:
            rgb = ImageColor.getrgb((tagline_color or "").strip())
            text_color = rgb + (255,)
        except Exception:
            text_color = TAGLINE_DEFAULT_COLOR

        bg_w, bg_h = background.size
        draw = ImageDraw.Draw(background, "RGBA")
        font_path = TAGLINE_FONT_PATH

        tagline_upper = tagline.upper().replace(".", "")
        words = tagline_upper.split()
        word_count = len(words)
        font_size = int(bg_w * (0.055 if word_count <= 2 else 0.053))

        margin_x = int(bg_w * 0.07)
        max_line_w = int(bg_w * 0.75) - margin_x
        comma_idx = tagline_upper.find(",")

        def wrap_words(words_list, fsize):
            font = ImageFont.truetype(font_path, fsize)
            lines, current = [], ""
            for w in words_list:
                test = (current + " " + w).strip()
                bb = draw.textbbox((0, 0), test, font=font)
                if bb[2] - bb[0] <= max_line_w or not current:
                    current = test
                else:
                    lines.append(current)
                    current = w
            if current:
                lines.append(current)
            return lines, font

        def wrap_at_size(fsize):
            if comma_idx != -1:
                part1 = tagline_upper[:comma_idx + 1].strip()
                part2 = tagline_upper[comma_idx + 1:].strip()
                font = ImageFont.truetype(font_path, fsize)
                bb_part1 = draw.textbbox((0, 0), part1, font=font)
                if (bb_part1[2] - bb_part1[0]) <= max_line_w and part2:
                    lines1, _ = wrap_words(part1.split(), fsize)
                    lines2, font = wrap_words(part2.split(), fsize)
                    return lines1 + lines2, font
            return wrap_words(words, fsize)

        def max_line_width(lines, font):
            return max(draw.textbbox((0, 0), l, font=font)[2] for l in lines)

        min_font_size = int(bg_w * 0.020)
        lines, font = wrap_at_size(font_size)
        while max_line_width(lines, font) > max_line_w and font_size > min_font_size:
            font_size -= 2
            lines, font = wrap_at_size(font_size)

        if len(lines) > 4:
            lines = lines[:4]
            lines[-1] = lines[-1].rstrip(".,;: ") + "…"

        ascent, descent = font.getmetrics()
        line_h = ascent + descent
        line_gap = int(line_h * 0.20)

        y = int(bg_h * 0.08)
        right_edge = bg_w - margin_x

        logo_right, logo_bottom = 0, 0
        if logo_zone:
            logo_w, logo_h = logo_zone
            logo_right = 18 + logo_w + int(bg_w * 0.02)
            logo_bottom = 18 + logo_h

        shadow_color = tuple(max(0, c - 60) for c in text_color[:3]) + (255,)
        outline_color = tuple(max(0, c - 30) for c in text_color[:3]) + (255,)

        for line in lines:
            clean_line = line.replace(",", "")
            bb = draw.textbbox((0, 0), clean_line, font=font, anchor="la")
            text_w = bb[2] - bb[0]
            x = right_edge - text_w

            if logo_zone and (y + line_h) > 18 and y < logo_bottom:
                x = max(x, logo_right)
            else:
                x = max(x, margin_x)

            for offset in range(6, 0, -1):
                alpha = int(180 * (offset / 6))
                draw.text((x + offset, y + offset), clean_line, font=font, fill=shadow_color[:3] + (alpha,), anchor="la")

            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
                draw.text((x + ox, y + oy), clean_line, font=font, fill=outline_color, anchor="la")

            draw.text((x, y), clean_line, font=font, fill=text_color, anchor="la")

            y += line_h + line_gap

    except Exception as e:
        print(f"Tagline text error: {e}")
    return background


def clean_and_truncate_prompt(raw_prompt: str) -> str:
    text = raw_prompt
    for marker in ["negative_prompt", "negative:", "negative prompt"]:
        idx = text.lower().find(marker)
        if idx != -1:
            text = text[:idx]

    text = text.replace("\n", " ").replace("\r", " ").strip()
    text = " ".join(text.split())

    if len(text) > MAX_PROMPT_CHARS:
        cut = text[:MAX_PROMPT_CHARS]
        last_space = cut.rfind(" ")
        if last_space > 0:
            cut = cut[:last_space]
        text = cut.rstrip(",;: ")

    return text


def correct_subject_position(img: Image.Image, desired_side: str, permissive: bool = False, midline: float = 0.55, trigger: float = 0.55):
    desired_side = (desired_side or "").strip().lower()
    if desired_side not in ("left", "right"):
        return img, "no_side_requested", True

    try:
        result = rembg_remove(img.convert("RGB"), session=_rembg_session).convert("RGBA")
        alpha = np.array(result.split()[-1], dtype=np.float32)
        h, w = alpha.shape
        coverage = alpha.sum() / (h * w * 255)

        if coverage < 0.03:
            return img, "no_subject_detected", True

        if coverage > (0.85 if permissive else 0.55):
            return img, "subject_too_large_or_noisy", False

        binary_mask = alpha > 50
        if not permissive:
            labeled_array, num_features = ndimage.label(binary_mask)
            sizes = ndimage.sum(binary_mask, labeled_array, range(1, num_features + 1))
            if int(np.sum(sizes > (h * w * 0.015))) >= 2:
                return img, "multiple_subjects_detected", False

        cols = np.where(binary_mask.any(axis=0))[0]
        if len(cols) == 0:
            return img, "no_subject_detected", True
        left_edge, right_edge = int(cols[0]), int(cols[-1])

        col_weights = alpha.sum(axis=0)
        centroid_ratio = (np.arange(w) * col_weights).sum() / col_weights.sum() / w
        detected_side = "left" if centroid_ratio < 0.5 else "right"

        if detected_side != desired_side:
            img = ImageOps.mirror(img)
            left_edge, right_edge = w - right_edge, w - left_edge
            return img, "mirrored", True

        midline_x = int(w * midline)
        trigger_x = int(w * trigger)
        feather = max(10, int(w * 0.05))

        def blend_seam(canvas, x_seam, from_left_to_right):
            arr = np.array(canvas).astype(np.float32)
            x0 = max(0, x_seam - feather)
            x1 = min(w, x_seam + feather)
            if x1 <= x0:
                return canvas
            ramp = np.linspace(0, 1, x1 - x0)[None, :, None]
            if not from_left_to_right:
                ramp = 1 - ramp
            left_col = arr[:, x0:x0 + 1, :]
            right_col = arr[:, x1 - 1:x1, :]
            arr[:, x0:x1, :] = left_col * (1 - ramp) + right_col * ramp
            return Image.fromarray(arr.astype(np.uint8), canvas.mode)

        def build_fill(real_bg_crop, gap, h):
            src_w = real_bg_crop.width
            if src_w < 2:
                return Image.new(img.mode, (gap, h), (210, 210, 210))
            fill = real_bg_crop.resize((gap, h), Image.Resampling.LANCZOS)
            stretch_factor = gap / src_w
            if stretch_factor > 1.3:
                blur_amount = min(14, 2 + stretch_factor * 1.5)
                fill = fill.filter(ImageFilter.GaussianBlur(blur_amount))
            return fill

        if desired_side == "left":
            if right_edge <= trigger_x:
                return img, "already_correct", True
            scale = midline_x / right_edge
            new_w = max(1, int(w * scale))
            shrunk = img.resize((new_w, h), Image.Resampling.LANCZOS)
            canvas = Image.new(img.mode, (w, h))
            canvas.paste(shrunk, (0, 0))
            gap = w - new_w
            if gap > 0:
                real_bg_w = w - right_edge
                real_bg = img.crop((right_edge, 0, w, h)) if real_bg_w >= 8 else img.crop((max(0, w - int(w * 0.1)), 0, w, h))
                fill = build_fill(real_bg, gap, h)
                canvas.paste(fill, (new_w, 0))
                canvas = blend_seam(canvas, new_w, from_left_to_right=True)
            img = canvas
        else:
            if left_edge >= (w - trigger_x):
                return img, "already_correct", True
            scale = (w - midline_x) / (w - left_edge)
            new_w = max(1, int(w * scale))
            shrunk = img.resize((new_w, h), Image.Resampling.LANCZOS)
            canvas = Image.new(img.mode, (w, h))
            gap = w - new_w
            if gap > 0:
                real_bg_w = left_edge
                real_bg = img.crop((0, 0, left_edge, h)) if real_bg_w >= 8 else img.crop((0, 0, max(1, int(w * 0.1)), h))
                fill = build_fill(real_bg, gap, h)
                canvas.paste(fill, (0, 0))
                canvas.paste(shrunk, (gap, 0))
                canvas = blend_seam(canvas, gap, from_left_to_right=False)
            else:
                canvas.paste(shrunk, (gap, 0))
            img = canvas

        return img, "corrected", True
    except Exception as e:
        print(f"correct_subject_position error: {e}")
        return img, "correction_failed", True


@app.post("/tools/generate-scene")
async def generate_scene(payload: SceneInput):
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail=(
                "CLOUDFLARE_ACCOUNT_ID ou CLOUDFLARE_API_TOKEN manquant. Créez un compte "
                "gratuit sur https://dash.cloudflare.com et un token avec la permission "
                "Workers AI, puis passez-les en variables d'environnement au conteneur hf-generator."
            ),
        )

    clean_text = clean_and_truncate_prompt(payload.prompt)
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}

    max_retries = 4
    last_error = None
    for attempt in range(max_retries):
        try:
            random_seed = random.randint(1, 100000)
            form_data = {
                "prompt": (None, clean_text),
                "width": (None, str(payload.width)),
                "height": (None, str(payload.height)),
                "seed": (None, str(random_seed)),
            }
            response = requests.post(CLOUDFLARE_URL, headers=headers, files=form_data, timeout=60)

            if response.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"Cloudflare 429 — attente {wait}s (tentative {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue

            if response.status_code in (401, 403):
                raise HTTPException(status_code=401, detail="Token API Cloudflare invalide ou expiré.")

            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                error_msg = str(data.get("errors", data))[:300]
                if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    raise HTTPException(
                        status_code=402,
                        detail=f"Quota Cloudflare épuisé (10 000 neurons/jour). Détail: {error_msg}",
                    )
                raise Exception(f"Erreur Cloudflare: {error_msg}")

            image_b64 = data["result"]["image"]
            scene_img = Image.open(io.BytesIO(base64.b64decode(image_b64)))
            scene_img = scene_img.resize((payload.width, payload.height), Image.Resampling.LANCZOS)

            product_position = (payload.position or "").strip().lower()
            desired_animal_side = {"left": "right", "right": "left"}.get(product_position, "")

            if desired_animal_side:
                scene_img, action, valid = correct_subject_position(scene_img, desired_animal_side)
                if not valid:
                    last_error = f"scene rejetée ({action}), nouvelle tentative"
                    print(f"Scene invalide ({action}), tentative {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                    scene_img, action, _ = correct_subject_position(scene_img, desired_animal_side, permissive=True)
                    print(f"Fallback permissif: {action}")

            filename = f"scene_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(SCENES_DIR, filename)
            scene_img.save(filepath, "PNG")
            return {
                "ok": True,
                "scene_image_path": filepath,
                "scene_prompt": clean_text,
                "model_used": CLOUDFLARE_MODEL,
            }

        except HTTPException:
            raise
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(10)
                continue

    raise HTTPException(
        status_code=400,
        detail=f"Erreur génération scène après {max_retries} tentatives: {last_error}",
    )


@app.post("/tools/compose-product")
async def compose_product(payload: ComposeInput):
    if not os.path.exists(payload.scene_image_path):
        raise HTTPException(status_code=404, detail="Image de scène introuvable sur le volume.")

    background = Image.open(payload.scene_image_path).convert("RGBA")
    bg_w, bg_h = background.size

    raw_product = download_image(payload.product.image_url)
    product_cutout = remove_background(raw_product)

    aspect_ratio = product_cutout.width / product_cutout.height

    if aspect_ratio > 1.25:
        scale_clamped = max(0.30, min(payload.scale, 0.85))
        target_w = int(bg_w * scale_clamped)
        target_h = int(target_w / aspect_ratio)
    else:
        scale_clamped = max(0.30, min(payload.scale, 0.70))
        target_h = int(bg_h * scale_clamped)
        target_w = int(target_h * aspect_ratio)
    product_resized = product_cutout.resize((target_w, target_h), Image.Resampling.LANCZOS)

    positions_x = {"left": 0.23, "center": 0.50, "bottom_center": 0.50, "right": 0.77}
    pos_x_ratio = positions_x.get(payload.position.lower(), 0.50)

    x_coords = int((bg_w * pos_x_ratio) - (target_w / 2))
    y_coords = int(bg_h * payload.y) - target_h

    x_coords = max(-target_w // 3, min(x_coords, bg_w - target_w // 3 * 2))
    y_coords = max(-target_h // 4, min(y_coords, bg_h - target_h // 4))

    shadow_blur = 15
    shadow = create_floor_shadow(target_w, target_h)
    shadow_x = int((x_coords + target_w / 2) - (target_w / 2 + shadow_blur))
    shadow_y = int((y_coords + target_h) - ((target_h // 4) / 2 + shadow_blur))

    enhancer = ImageEnhance.Brightness(product_resized)
    product_resized = enhancer.enhance(0.92)

    background.alpha_composite(shadow, (shadow_x, shadow_y))
    background.alpha_composite(product_resized, (x_coords, y_coords))

    background, logo_w, logo_h = add_logo(background)
    if payload.promo.strip():
        background = add_promo_badge(background, payload.promo)
    else:
        background = add_tagline_badge(background, payload.tagline, payload.tagline_color, logo_zone=(logo_w, logo_h))

    final_filename = f"final_{payload.product.id}_{uuid.uuid4().hex[:6]}.jpg"
    final_path = os.path.join(OUTPUTS_DIR, final_filename)
    background.convert("RGB").save(final_path, "JPEG", quality=95)

    return {
        "ok": True,
        "final_image_path": final_path,
        "position_applied": payload.position,
        "scale_applied": payload.scale,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)