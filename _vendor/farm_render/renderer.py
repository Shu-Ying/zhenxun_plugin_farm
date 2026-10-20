"""纯快照农场合成：目标尺寸、独立素材、可见状态成图缓存。"""

from dataclasses import replace
import hashlib
from io import BytesIO
import logging
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageDraw, UnidentifiedImageError

from .assets import Assets, ByteLRU
from .canvas import Canvas, font
from .layout import scene_from_snapshot
from .models import RenderOptions, RenderResult

logger = logging.getLogger(__name__)
MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_AVATAR_PIXELS = 4_000_000


class FarmRenderer:
    def __init__(
        self, font_path, asset_cache_bytes=32 * 1024 * 1024,
        result_cache_bytes=8 * 1024 * 1024,
    ):
        self.font_path = Path(font_path).resolve()
        if not self.font_path.is_file():
            raise ValueError("Configure an existing Chinese font path")
        font(self.font_path, 16)
        self.assets = Assets(asset_cache_bytes)
        self.results = ByteLRU(result_cache_bytes)

    def scene(self, identity, snapshot, now):
        return scene_from_snapshot(
            identity, snapshot, now, self.assets.metadata,
        )

    def request_key(
        self, identity, snapshot, now, options=None, avatar=None,
        supported=("JPEG",),
    ):
        options = options or RenderOptions()
        if avatar is not None and not isinstance(avatar, bytes):
            raise ValueError("Avatar must be bytes or None")
        digest = hashlib.sha256(avatar).hexdigest() if (
            avatar and len(avatar) <= MAX_AVATAR_BYTES
        ) else "default"
        scene = self.scene(identity, snapshot, now)
        return scene, options, options.codec(supported), digest

    def render(
        self, identity, snapshot, now, options=None, avatar=None,
        supported=("JPEG",),
    ):
        key = self.request_key(
            identity, snapshot, now, options, avatar, supported,
        )
        cached = self.results.get(key)
        if cached is not None:
            logger.info("farm render cache=hit bytes=%s", len(cached.content))
            return replace(cached, cache_hit=True, compose_ms=0, encode_ms=0)
        scene, options, codec, _ = key
        started = perf_counter()
        canvas = self._base(scene, options)
        self._plants(canvas, scene, options)
        self._pests(canvas, scene, options)
        self._decorations(canvas, options, "foreground")
        self._panel(canvas, scene, options, avatar)
        composed = perf_counter()
        content = canvas.encode(codec, options.quality, options.method)
        encoded = perf_counter()
        result = RenderResult(
            content, {"JPEG":"image/jpeg", "PNG":"image/png",
                      "WEBP":"image/webp"}[codec],
            *canvas.image.size, (composed - started) * 1000,
            (encoded - composed) * 1000,
        )
        self.results.put(key, result, len(content) + 4096)
        logger.info(
            "farm render cache=miss compose_ms=%.2f encode_ms=%.2f "
            "width=%s height=%s bytes=%s codec=%s",
            result.compose_ms, result.encode_ms, result.width,
            result.height, len(content), codec,
        )
        return result

    @staticmethod
    def _scale(value, options):
        return round(value * options.width / 3072)

    def _base(self, scene, options):
        slots = frozenset(p.slot for p in scene.plots)
        key = ("base", options.theme, options.width, slots)
        cached = self.assets.cache.get(key)
        if cached is not None:
            return Canvas(cached.copy())
        s = lambda n: self._scale(n, options)
        size = (options.width, s(1872))
        background = self.assets.image(
            "background/decorateIcon/"
            f"decorate_{options.theme}_1.jpg", size,
        )
        canvas = Canvas(background)
        self._decorations(canvas, options, "background")
        soil_size = tuple(max(1, s(n)) for n in (
            self.assets.metadata["soil_size"]
        ))
        tiles = {
            True: self.assets.image("soil/普通土地.png", soil_size),
            False: self.assets.image("soil/草土地.png", soil_size),
        }
        expansion = False
        for slot, pos in enumerate(self.assets.metadata["positions"], 1):
            xy = (s(pos["x"]), s(pos["y"]))
            canvas.paste(tiles[slot in slots], xy)
            if slot not in slots and not expansion:
                icon = self.assets.image(
                    "background/expansion.png", (max(1, s(90)),) * 2,
                )
                canvas.paste(icon, (xy[0] + s(70), xy[1] + s(10)))
                expansion = True
        self.assets.cache.put(key, canvas.image, size[0] * size[1] * 4)
        return canvas.copy()

    def _decorations(self, canvas, options, layer):
        s = lambda n: self._scale(n, options)
        for item in self.assets.metadata["decorations"][options.theme]:
            if item["layer"] != layer:
                continue
            image = self.assets.image(
                item["sprite"], tuple(max(1, s(n)) for n in item["size"]),
            )
            canvas.paste(image, tuple(s(n) for n in item["position"]))

    def _plants(self, canvas, scene, options):
        s = lambda n: self._scale(n, options)
        soil_w, soil_h = self.assets.metadata["soil_size"]
        rules = self.assets.metadata["placement"]
        unit = soil_h / rules["reference_soil_height"]
        first_ripe = True
        for plot in scene.plots:
            if not plot.sprite:
                continue
            pos = self.assets.metadata["positions"][plot.slot - 1]
            metadata = self.assets.metadata["images"].get(plot.sprite)
            if metadata is None:
                logger.warning("farm render missing packaged crop sprite")
                plant = Image.new("RGBA", (max(1, s(60)),) * 2, "#597b45")
                ImageDraw.Draw(plant).text(
                    (s(10), 0), "?", fill="white",
                    font=font(self.font_path, max(10, s(48))),
                )
            else:
                factor = rules["common_scale"] if (
                    plot.stage == 0 or plot.state == "withered"
                ) else rules["growth_scale"]
                size = [n * factor * unit for n in metadata["size"]]
                plant = self.assets.image(
                    plot.sprite, tuple(max(1, s(n)) for n in size),
                )
            center_x = pos["x"] + soil_w / 2
            bottom = pos["y"] + soil_h
            if plot.stage == 0 or plot.state == "withered":
                bottom = pos["y"] + soil_h / 2
                if plot.state == "withered":
                    bottom += rules["wither_down"] * unit
            xy = (
                round(center_x * options.width / 3072 - plant.width / 2),
                s(bottom) - plant.height,
            )
            canvas.paste(plant, xy)
            if plot.state == "ripe" and first_ripe:
                icon = self.assets.image(
                    "background/ripe.png", (max(1, s(100)),) * 2,
                )
                canvas.paste(icon, (s(pos["x"] + 70), s(pos["y"] - 80)))
                first_ripe = False

    def _pests(self, canvas, scene, options):
        s = lambda n: self._scale(n, options)
        soil_w, soil_h = self.assets.metadata["soil_size"]
        unit = soil_h / self.assets.metadata["placement"][
            "reference_soil_height"
        ]
        config = self.assets.metadata["pest"]
        size = tuple(max(1, s(n * unit)) for n in config["display_size"])
        for plot in scene.plots:
            if plot.state not in ("growing", "ripe"):
                continue
            pos = self.assets.metadata["positions"][plot.slot - 1]
            for frame, (x, y) in zip(plot.pest_frames, config["positions"]):
                image = self.assets.image(frame, size)
                center_x = pos["x"] + soil_w / 2 + x * unit
                center_y = pos["y"] + soil_h / 2 - y * unit
                canvas.paste(image, (
                    round(center_x * options.width / 3072 - image.width / 2),
                    round(center_y * options.width / 3072 - image.height / 2),
                ))

    def _avatar(self, content, size):
        if content and len(content) <= MAX_AVATAR_BYTES:
            try:
                with Image.open(BytesIO(content)) as image:
                    if image.width * image.height > MAX_AVATAR_PIXELS:
                        raise ValueError("Avatar dimensions exceed limit")
                    return image.convert("RGBA").resize(
                        size, Image.Resampling.LANCZOS,
                    )
            except (UnidentifiedImageError, OSError, ValueError,
                    Image.DecompressionBombError):
                logger.warning("farm render avatar rejected; using default")
        avatar = Image.new("RGBA", size, "#dce8cf")
        draw = ImageDraw.Draw(avatar)
        w, h = size
        draw.ellipse((w*.3, h*.12, w*.7, h*.52), fill="#6f8a54")
        draw.ellipse((w*.15, h*.55, w*.85, h*1.2), fill="#6f8a54")
        return avatar

    def _panel(self, canvas, scene, options, avatar):
        s = lambda n: self._scale(n, options)

        def paste_asset(name, position):
            original = self.assets.metadata["images"][name]["size"]
            image = self.assets.image(
                name, tuple(max(1, s(n)) for n in original),
            )
            canvas.paste(image, tuple(s(n) for n in position))

        paste_asset("background/userInfo.png", (100, 30))
        canvas.paste(
            self._avatar(avatar, (max(1, s(140)), max(1, s(150)))),
            (s(125), s(85)),
        )
        paste_asset("background/frame/frame.png", (75, 44))
        account = scene.account
        level = account.level
        current = account.experience - 200 * level * (level + 1) // 2
        next_total = 200 * (level + 1) * (level + 2) // 2
        progress = min(247, max(0, current * 247 // next_total))
        if progress:
            canvas.rectangle(
                tuple(s(n) for n in (292, 164, 292 + progress, 189)),
                (171, 194, 41),
            )
        lines = (
            (account.name, (300, 92), 24, (77, 35, 4), 330),
            (f"{current} / {next_total}", (365, 164), 20,
             (102, 120, 19), 165),
            (str(level), (570, 158), 32, (214, 111, 1), 60),
            (str(account.point), (330, 211), 24, (253, 253, 253), 100),
            (str(account.vip_point), (570, 211), 24, (253, 253, 253), 40),
        )
        for value, position, original_size, color, width in lines:
            size = max(1, s(original_size))
            text = canvas.fit_text(
                value, self.font_path, size, max(1, s(width)),
            )
            canvas.text(
                tuple(s(n) for n in position), text,
                self.font_path, size, color,
            )
