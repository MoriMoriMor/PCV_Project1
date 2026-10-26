
import os
import sys
import time
import math
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


WINDOW_TITLE = "PUZZLE CAMS - Arcade Computer Vision Game"
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


GRID_COLS = 3
GRID_ROWS = 3
TILE_SIZE = 150
BOARD_SIZE = GRID_COLS * TILE_SIZE


BOARD_X = (CANVAS_WIDTH - BOARD_SIZE) // 2
BOARD_Y = 185


STATE_MAIN_MENU = "STATE_MAIN_MENU"
STATE_CALIBRATION = "STATE_CALIBRATION"
STATE_CAPTURE = "STATE_CAPTURE"
STATE_PLAYING = "STATE_PLAYING"
STATE_STAGE_CLEAR = "STATE_STAGE_CLEAR"
STATE_GAME_OVER = "STATE_GAME_OVER"
STATE_VICTORY = "STATE_VICTORY"


CALIB_IDLE = "CALIB_IDLE"
CALIB_PREPARING = "CALIB_PREPARING"
CALIB_READING = "CALIB_READING"
CALIB_CALIBRATING = "CALIB_CALIBRATING"
CALIB_SUCCESS = "CALIB_SUCCESS"
CALIB_FAILED = "CALIB_FAILED"


STAGE_SHUFFLE_CONFIG = {
    1: (2, 3),
    2: (4, 5),
    3: (6, 8)
}


OBSTACLE_SPAWN_INTERVAL = 15.0
OBSTACLE_IDLE_LIMIT = 15.0


CAMERA_MARGIN_X = 0.18
CAMERA_MARGIN_Y = 0.18


OBSTACLE_NONE = 0
OBSTACLE_BUSH = 1
OBSTACLE_ICE = 2
OBSTACLE_DARK = 3
OBSTACLE_FOG = 4

OBSTACLE_NAMES = {
    OBSTACLE_NONE: "Bersih",
    OBSTACLE_BUSH: "Semak Belukar",
    OBSTACLE_ICE: "Es Beku",
    OBSTACLE_DARK: "Kutukan Gelap",
    OBSTACLE_FOG: "Kabut Tebal"
}


TOOL_NONE = 0
TOOL_KNIFE = 1
TOOL_HAIRDRYER = 2
TOOL_FLASHLIGHT = 3
TOOL_SPONGE = 4

TOOL_NAMES = {
    TOOL_NONE: "Kosong",
    TOOL_KNIFE: "Pisau",
    TOOL_HAIRDRYER: "Hairdryer",
    TOOL_FLASHLIGHT: "Senter",
    TOOL_SPONGE: "Spons"
}


TOOL_MATCH = {
    OBSTACLE_BUSH: TOOL_KNIFE,
    OBSTACLE_ICE: TOOL_HAIRDRYER,
    OBSTACLE_DARK: TOOL_FLASHLIGHT,
    OBSTACLE_FOG: TOOL_SPONGE
}


HOLD_TIME_SLIDE_GRAB = 0.25
HOLD_TIME_EQUIP = 0.35
HOLD_TIME_CLEAR = 0.60
AUTO_DROP_OPEN_TIME = 0.30
HOLD_TIME_CAPTURE_FIST = 1.5


COLOR_BG_DARK = (20, 18, 26)
COLOR_PANEL_BG = (35, 30, 42)
COLOR_NEON_CYAN = (255, 215, 0)
COLOR_NEON_GOLD = (0, 215, 255)
COLOR_NEON_GREEN = (60, 235, 80)
COLOR_NEON_RED = (50, 50, 240)
COLOR_TEXT_WHITE = (245, 245, 250)
COLOR_TEXT_DIM = (160, 160, 175)


ASSET_DIR = "assets"
ASSET_FILES = {
    "knife.png": os.path.join(ASSET_DIR, "knife.png"),
    "hairdryer.png": os.path.join(ASSET_DIR, "hairdryer.png"),
    "flashlight.png": os.path.join(ASSET_DIR, "flashlight.png"),
    "sponge.png": os.path.join(ASSET_DIR, "sponge.png"),
    "hand_open.png": os.path.join(ASSET_DIR, "hand_open.png"),
    "hand_fist.png": os.path.join(ASSET_DIR, "hand_fist.png"),
    "heart.png": os.path.join(ASSET_DIR, "heart.png"),
    "frame.png": os.path.join(ASSET_DIR, "frame.png")
}


EMOJI_GLYPHS = {
    "knife.png": "\U0001F52A",
    "hairdryer.png": "\U0001F4A8",
    "flashlight.png": "\U0001F526",
    "sponge.png": "\U0001F9FD",
    "hand_open.png": "\u270B",
    "hand_fist.png": "\u270A",
    "heart.png": "\u2764\uFE0F"
}


class AssetManager:
    def __init__(self, asset_dir=ASSET_DIR):
        self.asset_dir = asset_dir
        self.images = {}
        self.ensure_assets_exist()
        self.load_all_assets()

    def ensure_assets_exist(self):
        if not os.path.exists(self.asset_dir):
            os.makedirs(self.asset_dir, exist_ok=True)

        font_path = "C:/Windows/Fonts/seguiemj.ttf"
        font = None
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, 96)
            except Exception:
                font = None

        for filename, filepath in ASSET_FILES.items():
            if not os.path.exists(filepath):
                if filename == "frame.png":
                    self._create_frame_png(filepath)
                else:
                    emoji_char = EMOJI_GLYPHS.get(filename, "⭐")
                    self._create_emoji_png(filepath, emoji_char, font)

    def _create_emoji_png(self, filepath, emoji_char, font):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if font is not None:
            try:
                bbox = draw.textbbox((0, 0), emoji_char, font=font, embedded_color=True)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (128 - w) // 2 - bbox[0]
                y = (128 - h) // 2 - bbox[1]
                draw.text((x, y), emoji_char, font=font, embedded_color=True)
            except Exception:
                draw.ellipse((20, 20, 108, 108), fill=(255, 200, 50, 255))
        else:
            draw.ellipse((20, 20, 108, 108), fill=(255, 200, 50, 255))
        img.save(filepath, "PNG")

    def _create_frame_png(self, filepath):
        w, h = BOARD_SIZE + 40, BOARD_SIZE + 40
        frame_img = np.zeros((h, w, 4), dtype=np.uint8)
        cv2.rectangle(frame_img, (0, 0), (w - 1, h - 1), (45, 40, 55, 255), 8)
        cv2.rectangle(frame_img, (8, 8), (w - 9, h - 9), COLOR_NEON_CYAN, 2)
        L = 36
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        for cx, cy in corners:
            dx = 1 if cx == 0 else -1
            dy = 1 if cy == 0 else -1
            cv2.line(frame_img, (cx, cy), (cx + dx * L, cy), COLOR_NEON_GOLD, 5, cv2.LINE_AA)
            cv2.line(frame_img, (cx, cy), (cx, cy + dy * L), COLOR_NEON_GOLD, 5, cv2.LINE_AA)
        cv2.imwrite(filepath, frame_img)

    def load_all_assets(self):
        for name, filepath in ASSET_FILES.items():
            img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
            if img is not None:
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                elif img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                self.images[name] = img
            else:
                self.images[name] = np.zeros((128, 128, 4), dtype=np.uint8)

    def overlay_alpha(self, canvas, img_rgba, x, y, target_size=None):
        if img_rgba is None or img_rgba.size == 0:
            return
        if target_size is not None:
            img_rgba = cv2.resize(img_rgba, target_size, interpolation=cv2.INTER_AREA)

        h, w = img_rgba.shape[:2]
        H, W = canvas.shape[:2]

        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(W, x + w), min(H, y + h)

        if x1 >= x2 or y1 >= y2:
            return

        src_x1 = x1 - x
        src_y1 = y1 - y
        src_x2 = src_x1 + (x2 - x1)
        src_y2 = src_y1 + (y2 - y1)

        src_crop = img_rgba[src_y1:src_y2, src_x1:src_x2]
        alpha = (src_crop[:, :, 3] / 255.0)[:, :, np.newaxis]

        bg_crop = canvas[y1:y2, x1:x2]
        blended = (alpha * src_crop[:, :, :3] + (1.0 - alpha) * bg_crop).astype(np.uint8)
        canvas[y1:y2, x1:x2] = blended


class PCVEngine:

    @staticmethod
    def flip_horizontal(frame):
        return cv2.flip(frame, 1)

    @staticmethod
    def crop_square_grid(frame, crop_size=450):
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        half = crop_size // 2
        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(w, x1 + crop_size)
        y2 = min(h, y1 + crop_size)
        cropped = frame[y1:y2, x1:x2]
        return cv2.resize(cropped, (crop_size, crop_size), interpolation=cv2.INTER_AREA)

    @staticmethod
    def quantize_bit_depth(image, bits=3):
        levels = 2 ** bits
        step = 256 // levels
        quantized = (image // step) * step + (step // 2)
        return np.clip(quantized, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_flash_effect(image, intensity=1.0):
        intensity = np.clip(intensity, 0.0, 1.0)
        white_overlay = np.full_like(image, 255)
        return cv2.addWeighted(image, 1.0 - intensity, white_overlay, intensity, 0)

    @staticmethod
    def apply_negative_lut(image):
        lut_negative = 255 - np.arange(256, dtype=np.uint8)
        return cv2.LUT(image, lut_negative)

    @staticmethod
    def apply_gamma(image, gamma=4.0):
        gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
        return cv2.LUT(image, gamma_table)

    @staticmethod
    def apply_sobel_edges(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(sx**2 + sy**2)
        return np.clip(mag, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_median_blur(image, ksize=7):
        return cv2.medianBlur(image, ksize)

    @staticmethod
    def apply_gaussian_fog(image, ksize=(15, 15)):
        return cv2.GaussianBlur(image, ksize, 0)

    @staticmethod
    def apply_unsharp_mask(image, sigma=1.0, strength=1.5):
        blurred = cv2.GaussianBlur(image, (9, 9), sigma)
        unsharp = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
        return np.clip(unsharp, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_bush_obstacle(tile_img):
        edges = PCVEngine.apply_sobel_edges(tile_img)
        k_dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated_edges = cv2.dilate(edges, k_dil, iterations=2)

        green_tint = np.zeros_like(tile_img)
        green_tint[:, :, 1] = 190
        green_tint[:, :, 0] = 30
        green_tint[:, :, 2] = 40

        vines = cv2.cvtColor(dilated_edges, cv2.COLOR_GRAY2BGR)
        vines[:, :, 0] = (vines[:, :, 0] * 0.15).astype(np.uint8)
        vines[:, :, 2] = (vines[:, :, 2] * 0.10).astype(np.uint8)

        base_blend = cv2.addWeighted(tile_img, 0.45, green_tint, 0.55, 0)
        return cv2.addWeighted(base_blend, 0.75, vines, 0.65, 0)

    @staticmethod
    def apply_ice_obstacle(tile_img):
        neg = PCVEngine.apply_negative_lut(tile_img)
        med = PCVEngine.apply_median_blur(neg, 7)

        frost = med.copy()
        frost[:, :, 0] = np.clip(frost[:, :, 0].astype(np.int16) + 70, 0, 255).astype(np.uint8)
        frost[:, :, 1] = np.clip(frost[:, :, 1].astype(np.int16) + 40, 0, 255).astype(np.uint8)
        frost[:, :, 2] = (frost[:, :, 2] * 0.55).astype(np.uint8)
        return cv2.addWeighted(tile_img, 0.20, frost, 0.80, 0)

    @staticmethod
    def apply_dark_curse_obstacle(tile_img):
        dark = PCVEngine.apply_gamma(tile_img, 4.0)
        h, w = tile_img.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (np.sqrt(cx**2 + cy**2))
        vignette = np.clip(dist * 1.6, 0, 1)[:, :, None]

        purple = np.zeros_like(tile_img)
        purple[:, :, 0] = 90
        purple[:, :, 2] = 90
        return (dark * (1.0 - vignette * 0.6) + purple * (vignette * 0.4)).astype(np.uint8)

    @staticmethod
    def apply_fog_obstacle(tile_img):
        blur = PCVEngine.apply_gaussian_fog(tile_img, (15, 15))
        fog_color = np.full_like(tile_img, 215)
        return cv2.addWeighted(blur, 0.45, fog_color, 0.55, 0)

    @staticmethod
    def clean_hand_mask(mask):
        k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask_open = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open)
        return cv2.morphologyEx(mask_open, cv2.MORPH_CLOSE, k_close)


class HandTracker:
    def __init__(self):

        self.lower_hsv1 = np.array([0, 30, 50], dtype=np.uint8)
        self.upper_hsv1 = np.array([25, 200, 255], dtype=np.uint8)
        self.wrap_hue = False
        self.lower_hsv2 = None
        self.upper_hsv2 = None

        self.is_calibrated = False


        self.ref_area = 15000
        self.current_area = 0
        self.current_solidity = 0.70
        self.current_circularity = 0.25


        self.cursor_x = CANVAS_WIDTH // 2
        self.cursor_y = CANVAS_HEIGHT // 2
        self.raw_target_x = self.cursor_x
        self.raw_target_y = self.cursor_y


        self.is_fist = False
        self.fist_confirm_counter = 0
        self.open_confirm_counter = 0
        self.hand_detected = False
        self.target_lost_timer = 0.0


        self.open_hand_timer = 0.0


        self.latest_mask = None
        self.latest_contour = None


        self.calibrated_bgr = (180, 160, 210)

    def apply_color_segmentation(self, frame_hsv):
        mask1 = cv2.inRange(frame_hsv, self.lower_hsv1, self.upper_hsv1)
        if self.wrap_hue and self.lower_hsv2 is not None and self.upper_hsv2 is not None:
            mask2 = cv2.inRange(frame_hsv, self.lower_hsv2, self.upper_hsv2)
            return cv2.bitwise_or(mask1, mask2)
        return mask1

    def process_frame(self, frame, dt):
        h_cam, w_cam = frame.shape[:2]
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        raw_mask = self.apply_color_segmentation(frame_hsv)
        clean_mask = PCVEngine.clean_hand_mask(raw_mask)
        self.latest_mask = clean_mask


        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_cnt = None
        largest_area = 0


        min_detect_area = max(700, int(self.ref_area * 0.12))
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > largest_area and area >= min_detect_area:
                largest_area = area
                best_cnt = cnt

        if best_cnt is not None:
            self.hand_detected = True
            self.target_lost_timer = 0.0
            self.current_area = largest_area
            self.latest_contour = best_cnt


            M = cv2.moments(best_cnt)
            if M["m00"] > 0:
                best_cx = M["m10"] / M["m00"]
                best_cy = M["m01"] / M["m00"]
            else:
                x, y, w, h = cv2.boundingRect(best_cnt)
                best_cx = x + w / 2.0
                best_cy = y + h / 2.0


            min_x = w_cam * CAMERA_MARGIN_X
            max_x = w_cam * (1.0 - CAMERA_MARGIN_X)
            min_y = h_cam * CAMERA_MARGIN_Y
            max_y = h_cam * (1.0 - CAMERA_MARGIN_Y)

            norm_x = np.clip((best_cx - min_x) / max(1.0, max_x - min_x), 0.0, 1.0)
            norm_y = np.clip((best_cy - min_y) / max(1.0, max_y - min_y), 0.0, 1.0)

            target_x = int(norm_x * CANVAS_WIDTH)
            target_y = int(norm_y * CANVAS_HEIGHT)
            self.raw_target_x = target_x
            self.raw_target_y = target_y


            dist_sq = (target_x - self.cursor_x)**2 + (target_y - self.cursor_y)**2
            if dist_sq > 9:

                alpha = 0.40 if dist_sq < 2500 else 0.70
                self.cursor_x = int(alpha * target_x + (1.0 - alpha) * self.cursor_x)
                self.cursor_y = int(alpha * target_y + (1.0 - alpha) * self.cursor_y)


            self.cursor_x = int(np.clip(self.cursor_x, 0, CANVAS_WIDTH))
            self.cursor_y = int(np.clip(self.cursor_y, 0, CANVAS_HEIGHT))


            hull = cv2.convexHull(best_cnt)
            hull_area = cv2.contourArea(hull)
            solidity = self.current_area / max(1.0, hull_area)
            self.current_solidity = solidity

            perimeter = cv2.arcLength(best_cnt, True)
            circularity = (4.0 * math.pi * self.current_area) / max(1.0, perimeter * perimeter)
            self.current_circularity = circularity

            area_ratio = self.current_area / max(1.0, self.ref_area)


            fist_score = (circularity * 0.40) + (solidity * 0.35) + (max(0.0, 1.0 - area_ratio) * 0.25)


            if fist_score >= 0.52:
                self.fist_confirm_counter += 1
                self.open_confirm_counter = 0
                if self.fist_confirm_counter >= 2:
                    self.is_fist = True
                    self.open_hand_timer = 0.0
            elif fist_score <= 0.42:
                self.open_confirm_counter += 1
                self.fist_confirm_counter = 0
                if self.open_confirm_counter >= 3:
                    self.is_fist = False
                    self.open_hand_timer += dt
            else:
                if self.is_fist:
                    self.open_hand_timer = 0.0
                else:
                    self.open_hand_timer += dt

        else:

            self.target_lost_timer += dt
            if self.target_lost_timer > 0.35:
                self.hand_detected = False
                self.current_area = 0
                self.open_hand_timer += dt


class PuzzleEngine:
    def __init__(self):
        self.tiles = list(range(9))
        self.empty_val = 8
        self.stage = 1
        self.tile_images = [None] * 9
        self.full_photo = None


        self.neighbors = {
            0: [1, 3],
            1: [0, 2, 4],
            2: [1, 5],
            3: [0, 4, 6],
            4: [1, 3, 5, 7],
            5: [2, 4, 8],
            6: [3, 7],
            7: [4, 6, 8],
            8: [5, 7]
        }

    def set_captured_photo(self, photo_450):
        self.full_photo = photo_450.copy()
        self.tile_images = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                y1 = r * TILE_SIZE
                y2 = (r + 1) * TILE_SIZE
                x1 = c * TILE_SIZE
                x2 = (c + 1) * TILE_SIZE
                tile = photo_450[y1:y2, x1:x2].copy()
                self.tile_images.append(tile)

    def shuffle_legal_moves(self, num_moves):
        self.tiles = list(range(9))
        last_empty_pos = -1

        for _ in range(num_moves):
            empty_idx = self.tiles.index(self.empty_val)
            valid_swaps = self.neighbors[empty_idx]

            candidate_swaps = [pos for pos in valid_swaps if pos != last_empty_pos]
            if not candidate_swaps:
                candidate_swaps = valid_swaps

            chosen_pos = random.choice(candidate_swaps)
            self.tiles[empty_idx], self.tiles[chosen_pos] = self.tiles[chosen_pos], self.tiles[empty_idx]
            last_empty_pos = empty_idx

    def can_slide(self, tile_grid_pos):
        empty_pos = self.tiles.index(self.empty_val)
        return tile_grid_pos in self.neighbors[empty_pos]

    def slide_tile(self, tile_grid_pos):
        empty_pos = self.tiles.index(self.empty_val)
        if tile_grid_pos in self.neighbors[empty_pos]:
            self.tiles[empty_pos], self.tiles[tile_grid_pos] = self.tiles[tile_grid_pos], self.tiles[empty_pos]
            return True
        return False

    def is_solved(self):
        return self.tiles == list(range(9))


class ObstacleManager:
    def __init__(self):
        self.grid_obstacles = {}
        self.tile_idle_timers = {i: 0.0 for i in range(9)}
        self.time_since_last_spawn = 0.0
        self.stage = 1

    def reset_for_stage(self, stage):
        self.stage = stage
        self.grid_obstacles = {}
        self.tile_idle_timers = {i: 0.0 for i in range(9)}
        self.time_since_last_spawn = 0.0

    def get_stage_settings(self):
        if self.stage == 1:
            return {
                "allowed_obstacles": [OBSTACLE_BUSH],
                "active_tools": [TOOL_KNIFE]
            }
        elif self.stage == 2:
            return {
                "allowed_obstacles": [OBSTACLE_BUSH, OBSTACLE_ICE],
                "active_tools": [TOOL_KNIFE, TOOL_HAIRDRYER]
            }
        else:
            return {
                "allowed_obstacles": [OBSTACLE_BUSH, OBSTACLE_ICE, OBSTACLE_DARK, OBSTACLE_FOG],
                "active_tools": [TOOL_KNIFE, TOOL_HAIRDRYER, TOOL_FLASHLIGHT, TOOL_SPONGE]
            }

    def update(self, dt, hovered_grid_pos, empty_grid_pos):
        cfg = self.get_stage_settings()


        for pos in range(9):
            if pos == empty_grid_pos or pos == hovered_grid_pos:
                self.tile_idle_timers[pos] = 0.0
            else:
                self.tile_idle_timers[pos] += dt


        self.time_since_last_spawn += dt
        if self.time_since_last_spawn >= OBSTACLE_SPAWN_INTERVAL:
            self.time_since_last_spawn = 0.0
            free_slots = [p for p in range(9) if p != empty_grid_pos and p not in self.grid_obstacles]
            if free_slots:

                target_pos = max(free_slots, key=lambda p: self.tile_idle_timers.get(p, 0.0))
                chosen_obs = random.choice(cfg["allowed_obstacles"])
                self.grid_obstacles[target_pos] = chosen_obs
                self.tile_idle_timers[target_pos] = 0.0

    def check_deadlock(self, puzzle_engine):
        empty_pos = puzzle_engine.tiles.index(puzzle_engine.empty_val)
        neighbors = puzzle_engine.neighbors[empty_pos]
        all_neighbors_locked = all(n in self.grid_obstacles for n in neighbors)
        total_obstacles = len(self.grid_obstacles)
        return all_neighbors_locked or (total_obstacles >= 6)

    def clear_all(self):
        self.grid_obstacles.clear()
        for p in self.tile_idle_timers:
            self.tile_idle_timers[p] = 0.0


class UIRenderer:
    def __init__(self, asset_mgr):
        self.assets = asset_mgr


        self.tool_slots = {
            TOOL_KNIFE: {"name": "Pisau", "key": "[1]", "rect": (40, 200, 160, 130), "icon": "knife.png"},
            TOOL_HAIRDRYER: {"name": "Hairdryer", "key": "[2]", "rect": (40, 360, 160, 130), "icon": "hairdryer.png"},
            TOOL_FLASHLIGHT: {"name": "Senter", "key": "[3]", "rect": (1080, 200, 160, 130), "icon": "flashlight.png"},
            TOOL_SPONGE: {"name": "Spons", "key": "[4]", "rect": (1080, 360, 160, 130), "icon": "sponge.png"},
        }

    @staticmethod
    def draw_button(canvas, rect, text, is_hovered, accent_color, hotkey_text=None):
        x, y, w, h = rect
        bg_col = (45, 38, 55) if is_hovered else (32, 28, 40)
        border_col = accent_color if is_hovered else (95, 90, 115)
        border_th = 3 if is_hovered else 2

        cv2.rectangle(canvas, (x, y), (x + w, y + h), bg_col, -1)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), border_col, border_th)

        if is_hovered:
            corner_len = 12
            cv2.line(canvas, (x, y), (x + corner_len, y), accent_color, 4)
            cv2.line(canvas, (x, y), (x, y + corner_len), accent_color, 4)
            cv2.line(canvas, (x + w, y + h), (x + w - corner_len, y + h), accent_color, 4)
            cv2.line(canvas, (x + w, y + h), (x + w, y + h - corner_len), accent_color, 4)

        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.85, 2)
        tx = x + (w - tw) // 2
        ty = y + (h + th) // 2 - 2
        text_col = COLOR_TEXT_WHITE if not is_hovered else accent_color
        cv2.putText(canvas, text, (tx, ty), cv2.FONT_HERSHEY_DUPLEX, 0.85, text_col, 2, cv2.LINE_AA)

        if hotkey_text:
            cv2.putText(canvas, hotkey_text, (x + w - 46, y + 22), cv2.FONT_HERSHEY_PLAIN, 1.1, COLOR_NEON_GOLD, 1, cv2.LINE_AA)

    def render_hud(self, canvas, stage, score, lives, elapsed_sec):
        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 75), COLOR_PANEL_BG, -1)
        cv2.line(canvas, (0, 75), (CANVAS_WIDTH, 75), COLOR_NEON_CYAN, 2)

        stage_text = f"STAGE {stage}/3"
        cv2.putText(canvas, stage_text, (40, 48), cv2.FONT_HERSHEY_DUPLEX, 0.9, COLOR_NEON_GOLD, 2, cv2.LINE_AA)

        title_text = "PUZZLE CAMS"
        (tw, _), _ = cv2.getTextSize(title_text, cv2.FONT_HERSHEY_TRIPLEX, 1.2, 2)
        tx = (CANVAS_WIDTH - tw) // 2
        cv2.putText(canvas, title_text, (tx + 2, 52), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (20, 20, 20), 3, cv2.LINE_AA)
        cv2.putText(canvas, title_text, (tx, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, COLOR_NEON_CYAN, 2, cv2.LINE_AA)

        score_text = f"SCORE: {score:05d}"
        cv2.putText(canvas, score_text, (750, 48), cv2.FONT_HERSHEY_DUPLEX, 0.85, COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

        heart_img = self.assets.images.get("heart.png")
        hx_start = 980
        for i in range(3):
            hx = hx_start + (i * 38)
            if i < lives:
                self.assets.overlay_alpha(canvas, heart_img, hx, 22, (32, 32))
            else:
                cv2.circle(canvas, (hx + 16, 38), 12, (60, 60, 70), 2, cv2.LINE_AA)

        mins = int(elapsed_sec) // 60
        secs = int(elapsed_sec) % 60
        timer_text = f"{mins:02d}:{secs:02d}"
        cv2.putText(canvas, timer_text, (1140, 48), cv2.FONT_HERSHEY_DUPLEX, 0.85, COLOR_NEON_GOLD, 2, cv2.LINE_AA)

    def render_tool_panels(self, canvas, active_tools, equipped_tool, hover_tool, hover_progress):
        for tool_id, info in self.tool_slots.items():
            rx, ry, rw, rh = info["rect"]
            is_active = tool_id in active_tools
            is_equipped = (equipped_tool == tool_id)
            is_hovered = (hover_tool == tool_id)

            if not is_active:
                bg_col = (26, 24, 30)
                border_col = (50, 50, 55)
            elif is_equipped:
                bg_col = (45, 65, 30)
                border_col = COLOR_NEON_GREEN
            elif is_hovered:
                bg_col = (55, 50, 65)
                border_col = COLOR_NEON_GOLD
            else:
                bg_col = COLOR_PANEL_BG
                border_col = (90, 85, 110)

            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), bg_col, -1)
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), border_col, 2)

            cv2.putText(canvas, info["name"], (rx + 12, ry + 24), cv2.FONT_HERSHEY_DUPLEX, 0.55, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
            cv2.putText(canvas, info["key"], (rx + rw - 35, ry + 24), cv2.FONT_HERSHEY_PLAIN, 1.1, COLOR_NEON_GOLD, 1, cv2.LINE_AA)

            icon_img = self.assets.images.get(info["icon"])
            ix = rx + (rw - 64) // 2
            iy = ry + 35
            if icon_img is not None:
                if is_active:
                    self.assets.overlay_alpha(canvas, icon_img, ix, iy, (64, 64))
                else:
                    locked_icon = icon_img.copy()
                    locked_icon[:, :, :3] = (locked_icon[:, :, :3] * 0.25).astype(np.uint8)
                    self.assets.overlay_alpha(canvas, locked_icon, ix, iy, (64, 64))
                    cv2.putText(canvas, "TERKUNCI", (rx + 35, ry + 75), cv2.FONT_HERSHEY_DUPLEX, 0.5, (100, 100, 110), 1, cv2.LINE_AA)

            if is_hovered and hover_progress > 0.0:
                bar_w = int((rw - 20) * hover_progress)
                cv2.rectangle(canvas, (rx + 10, ry + rh - 10), (rx + 10 + bar_w, ry + rh - 6), COLOR_NEON_GOLD, -1)

            if is_equipped:
                cv2.rectangle(canvas, (rx + 25, ry + rh - 20), (rx + rw - 25, ry + rh - 4), COLOR_NEON_GREEN, -1)
                cv2.putText(canvas, "DIPEGANG", (rx + 38, ry + rh - 8), cv2.FONT_HERSHEY_PLAIN, 0.9, (20, 20, 20), 1, cv2.LINE_AA)

    def render_puzzle_board(self, canvas, puzzle, obstacles, hovered_grid_pos, hover_progress, held_tile_pos):
        frame_img = self.assets.images.get("frame.png")
        if frame_img is not None:
            self.assets.overlay_alpha(canvas, frame_img, BOARD_X - 20, BOARD_Y - 20, (BOARD_SIZE + 40, BOARD_SIZE + 40))
        else:
            cv2.rectangle(canvas, (BOARD_X - 8, BOARD_Y - 8), (BOARD_X + BOARD_SIZE + 8, BOARD_Y + BOARD_SIZE + 8), COLOR_NEON_CYAN, 3)

        empty_val = puzzle.empty_val
        empty_pos = puzzle.tiles.index(empty_val)

        for grid_pos in range(9):
            r = grid_pos // GRID_COLS
            c = grid_pos % GRID_COLS
            tx = BOARD_X + (c * TILE_SIZE)
            ty = BOARD_Y + (r * TILE_SIZE)

            tile_id = puzzle.tiles[grid_pos]

            if tile_id == empty_val:
                cv2.rectangle(canvas, (tx, ty), (tx + TILE_SIZE, ty + TILE_SIZE), (22, 18, 25), -1)
                cv2.rectangle(canvas, (tx + 2, ty + 2), (tx + TILE_SIZE - 2, ty + TILE_SIZE - 2), (40, 36, 48), 1)
                cv2.line(canvas, (tx + 20, ty + 20), (tx + TILE_SIZE - 20, ty + TILE_SIZE - 20), (32, 28, 38), 2)
                cv2.line(canvas, (tx + TILE_SIZE - 20, ty + 20), (tx + 20, ty + TILE_SIZE - 20), (32, 28, 38), 2)
            else:
                raw_tile = puzzle.tile_images[tile_id]
                if raw_tile is None:
                    raw_tile = np.full((TILE_SIZE, TILE_SIZE, 3), 80, dtype=np.uint8)

                obs_type = obstacles.get(grid_pos, OBSTACLE_NONE)
                if obs_type == OBSTACLE_BUSH:
                    display_tile = PCVEngine.apply_bush_obstacle(raw_tile)
                elif obs_type == OBSTACLE_ICE:
                    display_tile = PCVEngine.apply_ice_obstacle(raw_tile)
                elif obs_type == OBSTACLE_DARK:
                    display_tile = PCVEngine.apply_dark_curse_obstacle(raw_tile)
                elif obs_type == OBSTACLE_FOG:
                    display_tile = PCVEngine.apply_fog_obstacle(raw_tile)
                else:
                    display_tile = raw_tile.copy()

                canvas[ty:ty+TILE_SIZE, tx:tx+TILE_SIZE] = display_tile
                cv2.rectangle(canvas, (tx, ty), (tx + TILE_SIZE, ty + TILE_SIZE), (30, 25, 35), 1)


                if obs_type != OBSTACLE_NONE:
                    obs_label = OBSTACLE_NAMES[obs_type]
                    cv2.rectangle(canvas, (tx, ty + TILE_SIZE - 22), (tx + TILE_SIZE, ty + TILE_SIZE), (15, 15, 20), -1)
                    cv2.putText(canvas, obs_label, (tx + 12, ty + TILE_SIZE - 6), cv2.FONT_HERSHEY_PLAIN, 0.95, (0, 215, 255), 1, cv2.LINE_AA)


            if grid_pos == held_tile_pos:
                cv2.rectangle(canvas, (tx + 1, ty + 1), (tx + TILE_SIZE - 1, ty + TILE_SIZE - 1), COLOR_NEON_GREEN, 3)


            elif grid_pos == hovered_grid_pos:
                is_movable = (grid_pos in puzzle.neighbors[empty_pos]) and (grid_pos not in obstacles)
                has_obs = (grid_pos in obstacles)

                border_color = COLOR_NEON_GREEN if is_movable else (COLOR_NEON_RED if has_obs else COLOR_NEON_GOLD)
                cv2.rectangle(canvas, (tx + 1, ty + 1), (tx + TILE_SIZE - 1, ty + TILE_SIZE - 1), border_color, 2)

                if hover_progress > 0.0:
                    center_pt = (tx + TILE_SIZE // 2, ty + TILE_SIZE // 2)
                    radius = 28
                    cv2.circle(canvas, center_pt, radius, (20, 20, 20), -1)
                    cv2.circle(canvas, center_pt, radius, border_color, 2, cv2.LINE_AA)
                    angle = int(360 * hover_progress)
                    cv2.ellipse(canvas, center_pt, (radius, radius), -90, 0, angle, border_color, 4, cv2.LINE_AA)

    def render_cursor(self, canvas, tracker, equipped_tool):
        cx, cy = tracker.cursor_x, tracker.cursor_y
        is_fist = tracker.is_fist

        if equipped_tool != TOOL_NONE:
            tool_info = self.tool_slots.get(equipped_tool)
            if tool_info:
                icon_img = self.assets.images.get(tool_info["icon"])
                if icon_img is not None:
                    offset_y = int(math.sin(time.time() * 6.0) * 4)
                    self.assets.overlay_alpha(canvas, icon_img, cx - 32, cy - 32 + offset_y, (64, 64))
                    cv2.circle(canvas, (cx, cy), 6, COLOR_NEON_GOLD, 2, cv2.LINE_AA)
        else:
            cursor_name = "hand_fist.png" if is_fist else "hand_open.png"
            cursor_img = self.assets.images.get(cursor_name)
            if cursor_img is not None:
                self.assets.overlay_alpha(canvas, cursor_img, cx - 28, cy - 28, (56, 56))
            else:
                reticle_col = COLOR_NEON_GOLD if is_fist else COLOR_NEON_CYAN
                cv2.circle(canvas, (cx, cy), 16, reticle_col, 2, cv2.LINE_AA)
                cv2.circle(canvas, (cx, cy), 4, reticle_col, -1, cv2.LINE_AA)

    def render_pip_camera(self, canvas, frame, tracker):
        pip_w, pip_h = 160, 120
        pip_x, pip_y = 40, CANVAS_HEIGHT - pip_h - 20

        cv2.rectangle(canvas, (pip_x - 2, pip_y - 2), (pip_x + pip_w + 2, pip_y + pip_h + 2), COLOR_NEON_CYAN, 1)
        small_cam = cv2.resize(frame, (pip_w, pip_h), interpolation=cv2.INTER_AREA)

        if tracker.latest_mask is not None:
            small_mask = cv2.resize(tracker.latest_mask, (pip_w, pip_h), interpolation=cv2.INTER_NEAREST)
            contours, _ = cv2.findContours(small_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(small_cam, contours, -1, COLOR_NEON_GREEN, 1)

        canvas[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = small_cam

        gesture_str = "KEPAL (FIST)" if tracker.is_fist else "BUKA (OPEN)"
        badge_col = COLOR_NEON_GOLD if tracker.is_fist else COLOR_NEON_GREEN
        cv2.rectangle(canvas, (pip_x, pip_y), (pip_x + pip_w, pip_y + 18), (20, 20, 20), -1)
        cv2.putText(canvas, gesture_str, (pip_x + 6, pip_y + 14), cv2.FONT_HERSHEY_PLAIN, 0.9, badge_col, 1, cv2.LINE_AA)


class PuzzleCamsGame:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.using_simulated_camera = False

        if not self.cap.isOpened():
            print("[INFO] Kamera fisik tidak terdeteksi. Menggunakan simulator kamera virtual.")
            self.using_simulated_camera = True
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


        self.assets = AssetManager(ASSET_DIR)
        self.tracker = HandTracker()
        self.puzzle = PuzzleEngine()
        self.obstacles = ObstacleManager()
        self.ui = UIRenderer(self.assets)


        self.state = STATE_MAIN_MENU
        self.running = True

        self.stage = 1
        self.score = 0
        self.lives = 3
        self.stage_start_time = time.time()


        self.equipped_tool = TOOL_NONE
        self.held_tile_grid_pos = -1


        self.hover_grid_pos = -1
        self.hover_grid_timer = 0.0

        self.hover_tool_id = TOOL_NONE
        self.hover_tool_timer = 0.0


        self.capture_fist_timer = 0.0
        self.capture_countdown = -1.0


        self.flash_intensity = 0.0
        self.deadlock_flash_timer = 0.0


        self.stage_clear_timer = 0.0


        self.calib_state = CALIB_IDLE
        self.calib_progress = 0.0
        self.calib_status_text = "Menyiapkan"
        self.calib_error_message = ""
        self.calib_samples_hsv = []
        self.calib_samples_area = []
        self.calib_timer = 0.0
        self.calib_target_samples = 30

        roi_size = 200
        self.calib_roi = (
            (CANVAS_WIDTH - roi_size) // 2,
            (CANVAS_HEIGHT - roi_size) // 2 - 25,
            roi_size,
            roi_size
        )


        self.mouse_mode = False
        self.mouse_x = CANVAS_WIDTH // 2
        self.mouse_y = CANVAS_HEIGHT // 2
        self.mouse_clicked = False


        self.btn_main_menu_play = ((CANVAS_WIDTH - 280) // 2, 360, 280, 65)
        self.btn_main_menu_exit = ((CANVAS_WIDTH - 280) // 2, 450, 280, 65)

        self.btn_gameover_retry = ((CANVAS_WIDTH - 280) // 2, 440, 280, 55)
        self.btn_gameover_menu = ((CANVAS_WIDTH - 280) // 2, 510, 280, 55)
        self.btn_gameover_exit = ((CANVAS_WIDTH - 280) // 2, 580, 280, 55)

    def setup_window(self):
        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW_TITLE, self._on_mouse_event)

    def _on_mouse_event(self, event, x, y, flags, param):
        self.mouse_x = x
        self.mouse_y = y
        if self.mouse_mode:
            self.tracker.cursor_x = x
            self.tracker.cursor_y = y

        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_clicked = True
            if self.mouse_mode:
                self.tracker.is_fist = True
        elif event == cv2.EVENT_LBUTTONUP:
            if self.mouse_mode:
                self.tracker.is_fist = False

    def is_mouse_inside(self, rect):
        rx, ry, rw, rh = rect
        return (rx <= self.mouse_x <= rx + rw) and (ry <= self.mouse_y <= ry + rh)

    def read_camera_frame(self):
        if not self.using_simulated_camera and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return PCVEngine.flip_horizontal(frame)

        sim_frame = np.full((480, 640, 3), 35, dtype=np.uint8)
        for i in range(0, 640, 40):
            cv2.line(sim_frame, (i, 0), (i, 480), (45, 45, 55), 1)
        for j in range(0, 480, 40):
            cv2.line(sim_frame, (0, j), (640, j), (45, 45, 55), 1)
        cv2.putText(sim_frame, "SIMULASI KAMERA", (220, 240), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 215, 255), 1)
        return sim_frame

    def reset_game_state(self):
        self.stage = 1
        self.score = 0
        self.lives = 3
        self.equipped_tool = TOOL_NONE
        self.held_tile_grid_pos = -1
        self.hover_grid_pos = -1
        self.hover_grid_timer = 0.0
        self.hover_tool_id = TOOL_NONE
        self.hover_tool_timer = 0.0
        self.capture_fist_timer = 0.0
        self.capture_countdown = -1.0
        self.flash_intensity = 0.0
        self.deadlock_flash_timer = 0.0
        self.obstacles.reset_for_stage(1)


    def run(self):
        self.setup_window()
        last_time = time.time()

        while self.running:
            cur_time = time.time()
            dt = cur_time - last_time
            last_time = cur_time

            frame = self.read_camera_frame()


            if self.state in (STATE_CAPTURE, STATE_PLAYING) and not self.mouse_mode:
                self.tracker.process_frame(frame, dt)


            if self.state == STATE_PLAYING and self.equipped_tool != TOOL_NONE:
                if not self.tracker.is_fist and self.tracker.open_hand_timer >= AUTO_DROP_OPEN_TIME:
                    self.equipped_tool = TOOL_NONE

            canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH, 3), COLOR_BG_DARK, dtype=np.uint8)


            if self.state == STATE_MAIN_MENU:
                self._update_and_render_main_menu(canvas, dt)
            elif self.state == STATE_CALIBRATION:
                self._update_and_render_calibration(canvas, frame, dt)
            elif self.state == STATE_CAPTURE:
                self._update_and_render_capture(canvas, frame, dt)
            elif self.state == STATE_PLAYING:
                self._update_and_render_playing(canvas, frame, dt)
            elif self.state == STATE_STAGE_CLEAR:
                self._update_and_render_stage_clear(canvas, dt)
            elif self.state in (STATE_GAME_OVER, STATE_VICTORY):
                self._update_and_render_end(canvas, dt)

            cv2.imshow(WINDOW_TITLE, canvas)
            self.mouse_clicked = False

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                if self.state in (STATE_MAIN_MENU, STATE_GAME_OVER, STATE_VICTORY):
                    self.running = False
                    break
                else:
                    self.state = STATE_MAIN_MENU
            self._handle_keyboard_shortcuts(key, frame)

        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()

    def _handle_keyboard_shortcuts(self, key, frame):
        if key == 13 or key == ord(' '):
            if self.state == STATE_MAIN_MENU:
                self._start_calibration_flow()
            elif self.state == STATE_CALIBRATION:
                if self.calib_state in (CALIB_IDLE, CALIB_FAILED):
                    self._start_calibration_process()
            elif self.state == STATE_CAPTURE:
                self._trigger_photo_capture(frame)
            elif self.state == STATE_STAGE_CLEAR:
                self.stage_clear_timer = 0.0

        elif key in (ord('n'), ord('N')):
            if self.state == STATE_PLAYING:
                self._complete_current_stage()
            elif self.state == STATE_STAGE_CLEAR:
                self.stage_clear_timer = 0.0

        elif key in (ord('r'), ord('R')):
            if self.state == STATE_CALIBRATION:
                self._start_calibration_process()
            elif self.state in (STATE_PLAYING, STATE_GAME_OVER, STATE_VICTORY):
                self.reset_game_state()
                self._start_calibration_flow()

        elif key in (ord('m'), ord('M')):
            if self.state in (STATE_GAME_OVER, STATE_VICTORY):
                self.reset_game_state()
                self.state = STATE_MAIN_MENU
            else:
                self.mouse_mode = not self.mouse_mode

        elif key in (ord('d'), ord('D')):
            if self.state == STATE_PLAYING:
                self._trigger_deadlock()

        elif key == ord('1'):
            if self.state == STATE_PLAYING and TOOL_KNIFE in self.obstacles.get_stage_settings()["active_tools"]:
                self.equipped_tool = TOOL_KNIFE
        elif key == ord('2'):
            if self.state == STATE_PLAYING and TOOL_HAIRDRYER in self.obstacles.get_stage_settings()["active_tools"]:
                self.equipped_tool = TOOL_HAIRDRYER
        elif key == ord('3'):
            if self.state == STATE_PLAYING and TOOL_FLASHLIGHT in self.obstacles.get_stage_settings()["active_tools"]:
                self.equipped_tool = TOOL_FLASHLIGHT
        elif key == ord('4'):
            if self.state == STATE_PLAYING and TOOL_SPONGE in self.obstacles.get_stage_settings()["active_tools"]:
                self.equipped_tool = TOOL_SPONGE
        elif key == ord('0'):
            self.equipped_tool = TOOL_NONE


    def _update_and_render_main_menu(self, canvas, dt):
        for y in range(0, CANVAS_HEIGHT, 40):
            cv2.line(canvas, (0, y), (CANVAS_WIDTH, y), (26, 22, 34), 1)
        for x in range(0, CANVAS_WIDTH, 40):
            cv2.line(canvas, (x, 0), (x, CANVAS_HEIGHT), (26, 22, 34), 1)


        title = "PUZZLE CAMS"
        (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_TRIPLEX, 2.4, 3)
        tx = (CANVAS_WIDTH - tw) // 2
        cv2.putText(canvas, title, (tx + 4, 214), cv2.FONT_HERSHEY_TRIPLEX, 2.4, (15, 12, 20), 4, cv2.LINE_AA)
        cv2.putText(canvas, title, (tx, 210), cv2.FONT_HERSHEY_TRIPLEX, 2.4, COLOR_NEON_CYAN, 3, cv2.LINE_AA)


        hover_play = self.is_mouse_inside(self.btn_main_menu_play)
        UIRenderer.draw_button(canvas, self.btn_main_menu_play, "MAIN", hover_play, COLOR_NEON_GREEN, "[SPACE]")
        if hover_play and self.mouse_clicked:
            self._start_calibration_flow()


        hover_exit = self.is_mouse_inside(self.btn_main_menu_exit)
        UIRenderer.draw_button(canvas, self.btn_main_menu_exit, "KELUAR", hover_exit, COLOR_NEON_RED, "[ESC]")
        if hover_exit and self.mouse_clicked:
            self.running = False

    def _start_calibration_flow(self):
        self.calib_state = CALIB_IDLE
        self.calib_progress = 0.0
        self.calib_status_text = "Menyiapkan"
        self.calib_error_message = ""
        self.calib_samples_hsv = []
        self.calib_samples_area = []
        self.calib_timer = 0.0
        self.state = STATE_CALIBRATION

    def _start_calibration_process(self):
        self.calib_state = CALIB_PREPARING
        self.calib_progress = 0.05
        self.calib_status_text = "Menyiapkan"
        self.calib_error_message = ""
        self.calib_samples_hsv = []
        self.calib_samples_area = []
        self.calib_timer = 0.0


    def _update_and_render_calibration(self, canvas, frame, dt):
        cam_resized = cv2.resize(frame, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_LINEAR)
        canvas[:] = cam_resized

        overlay = np.zeros_like(canvas)
        canvas[:] = cv2.addWeighted(canvas, 0.65, overlay, 0.35, 0)


        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 70), COLOR_PANEL_BG, -1)
        cv2.line(canvas, (0, 70), (CANVAS_WIDTH, 70), COLOR_NEON_CYAN, 2)
        cv2.putText(canvas, "KALIBRASI WARNA KURSOR", (40, 46), cv2.FONT_HERSHEY_TRIPLEX, 0.95, COLOR_NEON_CYAN, 2, cv2.LINE_AA)


        rx, ry, rw, rh = self.calib_roi
        roi_color = COLOR_NEON_GREEN if self.calib_state == CALIB_SUCCESS else (COLOR_NEON_RED if self.calib_state == CALIB_FAILED else COLOR_NEON_GOLD)
        cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), roi_color, 3)

        cx, cy = rx + rw // 2, ry + rh // 2
        cv2.line(canvas, (cx - 15, cy), (cx + 15, cy), roi_color, 2)
        cv2.line(canvas, (cx, cy - 15), (cx, cy + 15), roi_color, 2)


        h_cam, w_cam = frame.shape[:2]
        cam_rx = int(rx * (w_cam / CANVAS_WIDTH))
        cam_ry = int(ry * (h_cam / CANVAS_HEIGHT))
        cam_rw = int(rw * (w_cam / CANVAS_WIDTH))
        cam_rh = int(rh * (h_cam / CANVAS_HEIGHT))
        roi_frame = frame[cam_ry:cam_ry+cam_rh, cam_rx:cam_rx+cam_rw]


        if self.calib_state == CALIB_PREPARING:
            self.calib_timer += dt
            self.calib_progress = min(0.15, 0.05 + (self.calib_timer / 0.4) * 0.10)
            self.calib_status_text = "Menyiapkan"
            if self.calib_timer >= 0.4:
                self.calib_state = CALIB_READING
                self.calib_timer = 0.0

        elif self.calib_state == CALIB_READING:
            if roi_frame.size > 0:
                roi_hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
                self.calib_samples_hsv.append(roi_hsv)
                avg_bgr = np.mean(roi_frame, axis=(0, 1))
                self.tracker.calibrated_bgr = (int(avg_bgr[0]), int(avg_bgr[1]), int(avg_bgr[2]))

            sample_count = len(self.calib_samples_hsv)
            self.calib_progress = 0.15 + (sample_count / self.calib_target_samples) * 0.60
            self.calib_status_text = "Membaca warna"

            if sample_count >= self.calib_target_samples:
                self.calib_state = CALIB_CALIBRATING
                self.calib_timer = 0.0

        elif self.calib_state == CALIB_CALIBRATING:
            self.calib_status_text = "Mengkalibrasi warna"
            self.calib_progress = 0.85
            success, err_msg = self._compute_and_validate_calibration()
            if success:
                self.calib_state = CALIB_SUCCESS
                self.calib_progress = 1.0
                self.calib_status_text = "Kalibrasi selesai"
                self.calib_timer = 0.0
            else:
                self.calib_state = CALIB_FAILED
                self.calib_error_message = err_msg

        elif self.calib_state == CALIB_SUCCESS:
            self.calib_timer += dt
            self.calib_progress = 1.0
            self.calib_status_text = "Kalibrasi selesai! Memulai permainan..."
            if self.calib_timer >= 1.0:
                self.state = STATE_CAPTURE
                self.capture_fist_timer = 0.0
                self.capture_countdown = -1.0


        self._render_calibration_progress_bar(canvas)


        btn_action_rect = ((CANVAS_WIDTH - 220) // 2, ry + rh + 100, 220, 50)
        hover_action = self.is_mouse_inside(btn_action_rect)

        if self.calib_state == CALIB_IDLE:
            cv2.putText(canvas, "Posisikan tangan di dalam kotak, lalu tekan [SPACE] atau tombol Mulai", (260, ry - 20), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
            UIRenderer.draw_button(canvas, btn_action_rect, "MULAI", hover_action, COLOR_NEON_GREEN, "[SPACE]")
            if hover_action and self.mouse_clicked:
                self._start_calibration_process()

        elif self.calib_state == CALIB_FAILED:
            cv2.putText(canvas, self.calib_error_message, (310, ry - 20), cv2.FONT_HERSHEY_DUPLEX, 0.65, COLOR_NEON_RED, 1, cv2.LINE_AA)
            UIRenderer.draw_button(canvas, btn_action_rect, "COBA LAGI", hover_action, COLOR_NEON_GOLD, "[SPACE]")
            if hover_action and self.mouse_clicked:
                self._start_calibration_process()


        btn_back_rect = (40, CANVAS_HEIGHT - 65, 180, 45)
        hover_back = self.is_mouse_inside(btn_back_rect)
        UIRenderer.draw_button(canvas, btn_back_rect, "MENU UTAMA", hover_back, COLOR_NEON_CYAN, "[ESC]")
        if hover_back and self.mouse_clicked:
            self.state = STATE_MAIN_MENU

    def _compute_and_validate_calibration(self):
        if self.using_simulated_camera:
            self.tracker.is_calibrated = True
            self.tracker.ref_area = 12000
            self.tracker.calibrated_bgr = (180, 160, 210)
            return True, ""

        if not self.calib_samples_hsv:
            return False, "Tidak ada frame sampel yang terbaca dari kamera."

        all_pixels = np.vstack([sample.reshape(-1, 3) for sample in self.calib_samples_hsv])
        h_vals = all_pixels[:, 0]
        s_vals = all_pixels[:, 1]
        v_vals = all_pixels[:, 2]

        v_mean = np.mean(v_vals)
        s_mean = np.mean(s_vals)

        if v_mean < 35:
            return False, "Pencahayaan terlalu gelap! Harap gunakan ruangan yang lebih terang."
        if s_mean < 20:
            return False, "Saturasi warna terlalu rendah (warna tidak terbaca jelas)."

        h_med = np.median(h_vals)
        s_med = np.median(s_vals)
        v_med = np.median(v_vals)

        h_low = int(h_med - 16)
        h_high = int(h_med + 16)


        if h_low < 0:
            self.tracker.wrap_hue = True
            self.tracker.lower_hsv1 = np.array([0, max(30, int(s_med - 45)), max(40, int(v_med - 55))], dtype=np.uint8)
            self.tracker.upper_hsv1 = np.array([h_high, min(255, int(s_med + 60)), min(255, int(v_med + 65))], dtype=np.uint8)
            self.tracker.lower_hsv2 = np.array([180 + h_low, max(30, int(s_med - 45)), max(40, int(v_med - 55))], dtype=np.uint8)
            self.tracker.upper_hsv2 = np.array([179, min(255, int(s_med + 60)), min(255, int(v_med + 65))], dtype=np.uint8)
        elif h_high > 179:
            self.tracker.wrap_hue = True
            self.tracker.lower_hsv1 = np.array([h_low, max(30, int(s_med - 45)), max(40, int(v_med - 55))], dtype=np.uint8)
            self.tracker.upper_hsv1 = np.array([179, min(255, int(s_med + 60)), min(255, int(v_med + 65))], dtype=np.uint8)
            self.tracker.lower_hsv2 = np.array([0, max(30, int(s_med - 45)), max(40, int(v_med - 55))], dtype=np.uint8)
            self.tracker.upper_hsv2 = np.array([h_high - 180, min(255, int(s_med + 60)), min(255, int(v_med + 65))], dtype=np.uint8)
        else:
            self.tracker.wrap_hue = False
            self.tracker.lower_hsv1 = np.array([h_low, max(30, int(s_med - 45)), max(40, int(v_med - 55))], dtype=np.uint8)
            self.tracker.upper_hsv1 = np.array([h_high, min(255, int(s_med + 60)), min(255, int(v_med + 65))], dtype=np.uint8)
            self.tracker.lower_hsv2 = None
            self.tracker.upper_hsv2 = None

        test_mask = self.tracker.apply_color_segmentation(self.calib_samples_hsv[-1])
        clean_test = PCVEngine.clean_hand_mask(test_mask)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(clean_test, connectivity=8)

        max_a = 0
        for i in range(1, num_labels):
            a = stats[i, cv2.CC_STAT_AREA]
            if a > max_a:
                max_a = a

        if max_a < 600:
            return False, "Target tidak terdeteksi. Posisikan tangan menutupi kotak."

        self.tracker.ref_area = max(max_a * 2, 4500)
        self.tracker.is_calibrated = True
        return True, ""

    def _render_calibration_progress_bar(self, canvas):
        rx, ry, rw, rh = self.calib_roi
        bar_w = 460
        bar_h = 24
        bar_x = (CANVAS_WIDTH - bar_w) // 2
        bar_y = ry + rh + 20

        cv2.rectangle(canvas, (bar_x - 2, bar_y - 2), (bar_x + bar_w + 2, bar_y + bar_h + 2), (40, 35, 50), -1)
        cv2.rectangle(canvas, (bar_x - 2, bar_y - 2), (bar_x + bar_w + 2, bar_y + bar_h + 2), COLOR_NEON_CYAN, 1)

        fill_w = int(bar_w * np.clip(self.calib_progress, 0.0, 1.0))
        if fill_w > 0:
            fill_col = COLOR_NEON_GREEN if self.calib_progress >= 1.0 else COLOR_NEON_GOLD
            cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), fill_col, -1)

        percent_str = f"{int(self.calib_progress * 100)}%"
        cv2.putText(canvas, percent_str, (bar_x + bar_w + 14, bar_y + 18), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, self.calib_status_text, (bar_x, bar_y + bar_h + 26), cv2.FONT_HERSHEY_DUPLEX, 0.65, COLOR_NEON_CYAN, 1, cv2.LINE_AA)

        swatch_size = 32
        swatch_x = bar_x - swatch_size - 16
        swatch_y = bar_y - 4
        cv2.rectangle(canvas, (swatch_x, swatch_y), (swatch_x + swatch_size, swatch_y + swatch_size), self.tracker.calibrated_bgr, -1)
        cv2.rectangle(canvas, (swatch_x, swatch_y), (swatch_x + swatch_size, swatch_y + swatch_size), COLOR_TEXT_WHITE, 1)


    def _update_and_render_capture(self, canvas, frame, dt):
        cam_resized = cv2.resize(frame, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_LINEAR)
        canvas[:] = cam_resized

        bx, by = (CANVAS_WIDTH - 450) // 2, (CANVAS_HEIGHT - 450) // 2
        cv2.rectangle(canvas, (bx, by), (bx + 450, by + 450), COLOR_NEON_CYAN, 3)

        header_banner = f"STAGE {self.stage}: POSE DAN KEPALKAN TANGAN UNTUK JEPRET"
        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 70), COLOR_PANEL_BG, -1)
        cv2.putText(canvas, header_banner, (240, 48), cv2.FONT_HERSHEY_TRIPLEX, 0.95, COLOR_NEON_GOLD, 2, cv2.LINE_AA)

        cv2.putText(canvas, "Kepalkan tangan selama 1.5 detik atau tekan [SPACE] / [C]", (330, CANVAS_HEIGHT - 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        if self.tracker.is_fist:
            self.capture_fist_timer += dt
            if self.capture_fist_timer >= HOLD_TIME_CAPTURE_FIST and self.capture_countdown < 0:
                self.capture_countdown = 3.0
        else:
            if self.capture_countdown < 0:
                self.capture_fist_timer = max(0.0, self.capture_fist_timer - dt * 2.0)

        if self.capture_countdown < 0 and self.capture_fist_timer > 0.0:
            prog = min(1.0, self.capture_fist_timer / HOLD_TIME_CAPTURE_FIST)
            bar_w = int(450 * prog)
            cv2.rectangle(canvas, (bx, by + 455), (bx + bar_w, by + 465), COLOR_NEON_GOLD, -1)

        if self.capture_countdown > 0:
            self.capture_countdown -= dt
            count_num = int(math.ceil(self.capture_countdown))
            if count_num > 0:
                count_str = str(count_num)
                cv2.circle(canvas, (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2), 65, (20, 20, 20), -1)
                cv2.circle(canvas, (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2), 65, COLOR_NEON_GOLD, 3, cv2.LINE_AA)
                cv2.putText(canvas, count_str, (CANVAS_WIDTH // 2 - 20, CANVAS_HEIGHT // 2 + 25), cv2.FONT_HERSHEY_TRIPLEX, 2.5, COLOR_TEXT_WHITE, 3, cv2.LINE_AA)
            else:
                self._trigger_photo_capture(frame)

        self.ui.render_pip_camera(canvas, frame, self.tracker)

    def _trigger_photo_capture(self, frame):
        cam_resized = cv2.resize(frame, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_LINEAR)
        bx = (CANVAS_WIDTH - BOARD_SIZE) // 2
        by = (CANVAS_HEIGHT - BOARD_SIZE) // 2
        photo_450 = cam_resized[by:by+BOARD_SIZE, bx:bx+BOARD_SIZE].copy()

        self.puzzle.set_captured_photo(photo_450)


        min_m, max_m = STAGE_SHUFFLE_CONFIG.get(self.stage, (2, 3))
        moves = random.randint(min_m, max_m)

        self.puzzle.shuffle_legal_moves(moves)
        self.obstacles.reset_for_stage(self.stage)
        self.equipped_tool = TOOL_NONE
        self.held_tile_grid_pos = -1
        self.stage_start_time = time.time()

        self.flash_intensity = 1.0
        self.state = STATE_PLAYING


    def _update_and_render_playing(self, canvas, frame, dt):
        cx, cy = self.tracker.cursor_x, self.tracker.cursor_y
        current_hover_grid = -1

        if (BOARD_X <= cx < BOARD_X + BOARD_SIZE) and (BOARD_Y <= cy < BOARD_Y + BOARD_SIZE):
            col = (cx - BOARD_X) // TILE_SIZE
            row = (cy - BOARD_Y) // TILE_SIZE
            current_hover_grid = int(row * GRID_COLS + col)

        current_hover_tool = TOOL_NONE
        for t_id, t_info in self.ui.tool_slots.items():
            tx, ty, tw, th = t_info["rect"]
            if (tx <= cx < tx + tw) and (ty <= cy < ty + th):
                if t_id in self.obstacles.get_stage_settings()["active_tools"]:
                    current_hover_tool = t_id
                    break

        empty_grid_pos = self.puzzle.tiles.index(self.puzzle.empty_val)
        self.obstacles.update(dt, current_hover_grid, empty_grid_pos)

        if self.obstacles.check_deadlock(self.puzzle):
            self._trigger_deadlock()

        action_progress = 0.0


        if self.tracker.is_fist:

            if current_hover_tool != TOOL_NONE:
                if current_hover_tool == self.hover_tool_id:
                    self.hover_tool_timer += dt
                else:
                    self.hover_tool_id = current_hover_tool
                    self.hover_tool_timer = 0.0

                action_progress = min(1.0, self.hover_tool_timer / HOLD_TIME_EQUIP)
                if self.hover_tool_timer >= HOLD_TIME_EQUIP:
                    self.equipped_tool = current_hover_tool
                    self.hover_tool_timer = 0.0
            else:
                self.hover_tool_timer = 0.0
                self.hover_tool_id = TOOL_NONE


            if self.equipped_tool != TOOL_NONE and current_hover_grid != -1:
                active_obs = self.obstacles.grid_obstacles.get(current_hover_grid, OBSTACLE_NONE)
                matched_tool = TOOL_MATCH.get(active_obs, TOOL_NONE)

                if active_obs != OBSTACLE_NONE and self.equipped_tool == matched_tool:
                    if current_hover_grid == self.hover_grid_pos:
                        self.hover_grid_timer += dt
                    else:
                        self.hover_grid_pos = current_hover_grid
                        self.hover_grid_timer = 0.0

                    action_progress = min(1.0, self.hover_grid_timer / HOLD_TIME_CLEAR)
                    if self.hover_grid_timer >= HOLD_TIME_CLEAR:
                        del self.obstacles.grid_obstacles[current_hover_grid]
                        self.hover_grid_timer = 0.0
                        self.hover_grid_pos = -1
                else:
                    self.hover_grid_timer = 0.0


            elif self.equipped_tool == TOOL_NONE and current_hover_grid != -1 and current_hover_grid != empty_grid_pos:
                can_move = self.puzzle.can_slide(current_hover_grid)
                is_locked = (current_hover_grid in self.obstacles.grid_obstacles)

                if can_move and not is_locked:
                    self.held_tile_grid_pos = current_hover_grid

                    if current_hover_grid == self.hover_grid_pos:
                        self.hover_grid_timer += dt
                    else:
                        self.hover_grid_pos = current_hover_grid
                        self.hover_grid_timer = 0.0

                    action_progress = min(1.0, self.hover_grid_timer / HOLD_TIME_SLIDE_GRAB)

                    if self.hover_grid_timer >= HOLD_TIME_SLIDE_GRAB:
                        self.puzzle.slide_tile(current_hover_grid)
                        self.hover_grid_timer = 0.0
                        self.hover_grid_pos = -1
                        self.held_tile_grid_pos = -1

                        if self.puzzle.is_solved():
                            self._complete_current_stage()
                            return
                else:
                    self.hover_grid_timer = 0.0
            else:
                self.hover_grid_timer = 0.0

        else:


            self.held_tile_grid_pos = -1
            self.hover_grid_timer = 0.0
            self.hover_tool_timer = 0.0
            self.hover_grid_pos = -1
            self.hover_tool_id = TOOL_NONE


        active_tools = self.obstacles.get_stage_settings()["active_tools"]
        elapsed_sec = time.time() - self.stage_start_time

        self.ui.render_hud(canvas, self.stage, self.score, self.lives, elapsed_sec)
        tool_hover_prog = action_progress if current_hover_tool != TOOL_NONE else 0.0
        self.ui.render_tool_panels(canvas, active_tools, self.equipped_tool, current_hover_tool, tool_hover_prog)
        tile_hover_prog = action_progress if current_hover_grid != -1 else 0.0
        self.ui.render_puzzle_board(canvas, self.puzzle, self.obstacles.grid_obstacles, current_hover_grid, tile_hover_prog, self.held_tile_grid_pos)
        self.ui.render_pip_camera(canvas, frame, self.tracker)
        self.ui.render_cursor(canvas, self.tracker, self.equipped_tool)

        if self.flash_intensity > 0.0:
            canvas[:] = PCVEngine.apply_flash_effect(canvas, self.flash_intensity)
            self.flash_intensity = max(0.0, self.flash_intensity - dt * 3.5)

        if self.deadlock_flash_timer > 0.0:
            self.deadlock_flash_timer -= dt
            red_overlay = np.zeros_like(canvas)
            red_overlay[:, :, 2] = 230
            canvas[:] = cv2.addWeighted(canvas, 0.65, red_overlay, 0.35, 0)

    def _trigger_deadlock(self):
        self.lives -= 1
        self.score = max(0, self.score - 200)
        self.deadlock_flash_timer = 0.5
        self.obstacles.clear_all()

        if self.lives <= 0:
            self.state = STATE_GAME_OVER

    def _complete_current_stage(self):
        elapsed = time.time() - self.stage_start_time
        base_points = {1: 300, 2: 600, 3: 900}.get(self.stage, 300)
        time_bonus = max(0, int((90 - elapsed) * 10))

        self.score += (base_points + time_bonus)
        self.stage_clear_timer = 3.0
        self.state = STATE_STAGE_CLEAR

    def _update_and_render_stage_clear(self, canvas, dt):
        self.stage_clear_timer -= dt

        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 80), COLOR_PANEL_BG, -1)
        clear_title = f"STAGE {self.stage} SELESAI!"
        cv2.putText(canvas, clear_title, (480, 52), cv2.FONT_HERSHEY_TRIPLEX, 1.2, COLOR_NEON_GREEN, 2, cv2.LINE_AA)

        if self.puzzle.full_photo is not None:
            canvas[BOARD_Y:BOARD_Y+BOARD_SIZE, BOARD_X:BOARD_X+BOARD_SIZE] = self.puzzle.full_photo

        cv2.rectangle(canvas, (BOARD_X - 4, BOARD_Y - 4), (BOARD_X + BOARD_SIZE + 4, BOARD_Y + BOARD_SIZE + 4), COLOR_NEON_GREEN, 3)
        cv2.putText(canvas, f"TOTAL SKOR: {self.score:05d}", (BOARD_X + 110, BOARD_Y + BOARD_SIZE + 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        countdown_sec = max(1, int(math.ceil(self.stage_clear_timer)))
        cv2.putText(canvas, f"Melanjutkan dalam {countdown_sec} detik... (Tekan [N] untuk lewati)", (BOARD_X + 20, BOARD_Y + BOARD_SIZE + 70), cv2.FONT_HERSHEY_PLAIN, 1.2, COLOR_NEON_GOLD, 1, cv2.LINE_AA)

        if self.stage_clear_timer <= 0:
            if self.stage < 3:
                self.stage += 1
                self.state = STATE_CAPTURE
                self.capture_fist_timer = 0.0
                self.capture_countdown = -1.0
            else:
                self.state = STATE_VICTORY


    def _update_and_render_end(self, canvas, dt):
        is_victory = (self.state == STATE_VICTORY)

        if is_victory:
            title = "SELAMAT! ANDA MENANG!"
            title_col = COLOR_NEON_GOLD

            if self.puzzle.full_photo is not None:
                photo_small = cv2.resize(self.puzzle.full_photo, (280, 280), interpolation=cv2.INTER_AREA)
                px = (CANVAS_WIDTH - 280) // 2
                canvas[140:420, px:px+280] = photo_small
                cv2.rectangle(canvas, (px - 2, 138), (px + 282, 422), COLOR_NEON_GOLD, 2)

            rank = "RANK: S" if self.score >= 2600 else ("RANK: A" if self.score >= 1800 else "RANK: B")
            cv2.putText(canvas, rank, ((CANVAS_WIDTH - 120) // 2, 125), cv2.FONT_HERSHEY_TRIPLEX, 0.85, COLOR_NEON_CYAN, 1, cv2.LINE_AA)

        else:
            title = "GAME OVER"
            title_col = COLOR_NEON_RED

            if self.puzzle.full_photo is not None:
                quantized = PCVEngine.quantize_bit_depth(self.puzzle.full_photo, bits=3)
                photo_small = cv2.resize(quantized, (280, 280), interpolation=cv2.INTER_AREA)
                px = (CANVAS_WIDTH - 280) // 2
                canvas[140:420, px:px+280] = photo_small
                cv2.rectangle(canvas, (px - 2, 138), (px + 282, 422), COLOR_NEON_RED, 2)

        (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_TRIPLEX, 1.3, 2)
        cv2.putText(canvas, title, ((CANVAS_WIDTH - tw) // 2, 95), cv2.FONT_HERSHEY_TRIPLEX, 1.3, title_col, 2, cv2.LINE_AA)

        score_text = f"SKOR AKHIR: {self.score:05d}  |  STAGE: {self.stage}"
        (st_w, _), _ = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)
        cv2.putText(canvas, score_text, ((CANVAS_WIDTH - st_w) // 2, 430), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)


        hover_retry = self.is_mouse_inside(self.btn_gameover_retry)
        UIRenderer.draw_button(canvas, self.btn_gameover_retry, "MAIN LAGI", hover_retry, COLOR_NEON_GREEN, "[R]")
        if hover_retry and self.mouse_clicked:
            self.reset_game_state()
            self._start_calibration_flow()


        hover_menu = self.is_mouse_inside(self.btn_gameover_menu)
        UIRenderer.draw_button(canvas, self.btn_gameover_menu, "MENU UTAMA", hover_menu, COLOR_NEON_CYAN, "[M]")
        if hover_menu and self.mouse_clicked:
            self.reset_game_state()
            self.state = STATE_MAIN_MENU


        hover_exit = self.is_mouse_inside(self.btn_gameover_exit)
        UIRenderer.draw_button(canvas, self.btn_gameover_exit, "KELUAR GAME", hover_exit, COLOR_NEON_RED, "[ESC]")
        if hover_exit and self.mouse_clicked:
            self.running = False


if __name__ == "__main__":
    game = PuzzleCamsGame()
    game.run()
