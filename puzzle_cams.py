"""
====================================================================================================
                             PUZZLE CAMS - WEBCAM ARCADE PUZZLE GAME
                 Game Komputer Berbasis Kamera & Pengolahan Citra dan Visi (PCV)
====================================================================================================

Deskripsi:
  Game sliding puzzle interaktif 3x3 yang dikendalikan 100% menggunakan kamera webcam dan
  gerakan tangan pemain secara real-time. Dilengkapi dengan sistem rintangan (obstacles) dinamis,
  peralatan (tools), deteksi deadlock, dan penerapan nyata materi Pengolahan Citra dan Visi (PCV).

Peta Implementasi Materi PCV (P1 - P5):
  [P1] Dasar Citra & Operasi Spasial:
       - Flip horizontal kamera (Mirroring) agar interaksi intuitif (cv2.flip).
       - Cropping matriks grid 3x3 dari foto webcam pemain (Array slicing).
       - Kuantisasi bit-depth rendah (3-bit / 8 level warna) untuk efek Game Over arcade retro.
  [P2] Operasi Titik & Transformasi Kontras:
       - Efek Flash putih pada jepretan foto (Linear point blending / cv2.addWeighted).
       - Transformasi Look-Up Table (LUT) Negatif untuk rintangan "Es Beku" (cv2.LUT).
       - Transformasi Gamma 4.0 untuk rintangan "Kutukan Gelap" (Pencahayaan non-linear).
       - Transformasi Gamma 0.45 / Local contrast boost untuk alat "Senter".
  [P3] Filter Spasial & Transformasi Frekuensi:
       - Filter Sobel (Gradient Magnitude Gx & Gy) untuk tekstur sulur rintangan "Semak".
       - Median Filter untuk menghaluskan kristal es pada rintangan "Es Beku" (cv2.medianBlur).
       - Gaussian Blur 15x15 untuk rintangan "Kabut Tebal" (cv2.GaussianBlur).
       - Unsharp Masking (High-pass boost) untuk efek alat "Spons" pembersih kabut.
  [P4] Segmentasi Warna & Operasi Matriks / Blending:
       - Color Masking ruang warna HSV untuk pelacakan tangan secara adaptif (cv2.inRange).
       - Alpha Blending multi-channel untuk ikon alat mengambang & tint visual rintangan.
  [P5] Morfologi Citra & Analisis Bentuk:
       - Morfologi Opening (erosi lalu dilasi) untuk membersihkan noise bintik (salt noise).
       - Morfologi Closing (dilasi lalu erosi) untuk menutup lubang di dalam kontur tangan.
       - cv2.connectedComponentsWithStats untuk menghitung centroid (x, y) dan luas piksel (Area).
       - Dilasi pada tepi Sobel untuk efek pertumbuhan Semak.
       - Erosi untuk efek pemotongan Semak oleh alat Pisau.
       - Analisis Rasio Area (< 65% area referensi) untuk membedakan gestur Tangan Terbuka vs Mengepal.

Sistem Aset Gambar:
  - Seluruh aset gambar (ikon pisau, hairdryer, senter, spons, cursor tangan, bingkai, hati) disimpan
    di dalam folder lokal 'assets/'.
  - Program ini otomatis membuat folder 'assets/' dan menggambar aset default berkualitas tinggi
    menggunakan OpenCV drawing jika file belum ada, sehingga program DAPAT LANGSUNG BERJALAN.
  - CARA MENGGANTI ASET:
    Pengguna dapat menimpa file di folder 'assets/' dengan gambar PNG transparan (RGBA) buatan
    sendiri atau unduhan dari web (ukuran disarankan 128x128 piksel untuk ikon, 490x490 untuk frame).

Kontrol & Tombol Pintas (Demo / Pengaman):
  - Kamera: Letakkan telapak tangan di layar untuk menggerakkan kursor.
  - Buka Tangan (Area > 65%): Mode Geser puzzle & reset idle timer semak.
  - Kepalkan Tangan (Area < 65%): Mode Genggam alat & pakai alat pada rintangan.
  - [SPACE] : Kalibrasi di layar HOME / Jepret foto di layar CAPTURE.
  - [N]     : Instant Stage Clear (Lewati stage untuk evaluasi/demo).
  - [R]     : Restart permainan dari awal.
  - [D]     : Paksa Deadlock (untuk menguji pengurangan nyawa, penalti skor & flash merah).
  - [1..4]  : Pintas cepat memilih Tool (1: Pisau, 2: Hairdryer, 3: Senter, 4: Spons).
  - [0]     : Lepas tool yang sedang dipegang.
  - [M]     : Toggle kontrol Hybrid (Mouse / Kamera Hand-Tracking).
  - [Q]/[ESC]: Keluar dari permainan.
====================================================================================================
"""

import os
import sys
import time
import math
import random
import cv2
import numpy as np

# ==================================================================================================
# 1. KONFIGURASI GLOBAL & KONSTANTA SISTEM
# ==================================================================================================
WINDOW_TITLE = "PUZZLE CAMS - Arcade Computer Vision Game"
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720

# Ukuran Papan Puzzle (3x3)
GRID_COLS = 3
GRID_ROWS = 3
TILE_SIZE = 150
BOARD_SIZE = GRID_COLS * TILE_SIZE  # 450 x 450 piksel

# Koordinat Penempatan Papan Puzzle di Tengah Layar
BOARD_X = (CANVAS_WIDTH - BOARD_SIZE) // 2  # 415
BOARD_Y = 185                               # 185 .. 635

# State Permainan
STATE_HOME = "STATE_HOME"
STATE_CAPTURE = "STATE_CAPTURE"
STATE_PLAYING = "STATE_PLAYING"
STATE_STAGE_CLEAR = "STATE_STAGE_CLEAR"
STATE_GAME_OVER = "STATE_GAME_OVER"
STATE_VICTORY = "STATE_VICTORY"

# Jenis Rintangan (Obstacles)
OBSTACLE_NONE = 0
OBSTACLE_BUSH = 1   # Semak (Sobel + Dilation + Green Blend) -> Tool: Pisau
OBSTACLE_ICE = 2    # Es Beku (LUT Negatif + Median Filter) -> Tool: Hairdryer
OBSTACLE_DARK = 3   # Kutukan Gelap (Gamma 4.0 + Vignette) -> Tool: Senter
OBSTACLE_FOG = 4    # Kabut Tebal (Gaussian Blur 15x15)    -> Tool: Spons

OBSTACLE_NAMES = {
    OBSTACLE_NONE: "Bersih",
    OBSTACLE_BUSH: "Semak Belukar",
    OBSTACLE_ICE: "Es Beku",
    OBSTACLE_DARK: "Kutukan Gelap",
    OBSTACLE_FOG: "Kabut Tebal"
}

# Jenis Peralatan (Tools)
TOOL_NONE = 0
TOOL_KNIFE = 1       # Pisau (Membersihkan Semak)
TOOL_HAIRDRYER = 2   # Hairdryer (Melelehkan Es Beku)
TOOL_FLASHLIGHT = 3  # Senter (Menerangi Kutukan Gelap)
TOOL_SPONGE = 4      # Spons (Menyeka Kabut Tebal)

TOOL_NAMES = {
    TOOL_NONE: "Kosong",
    TOOL_KNIFE: "Pisau",
    TOOL_HAIRDRYER: "Hairdryer",
    TOOL_FLASHLIGHT: "Senter",
    TOOL_SPONGE: "Spons"
}

# Pemetaan Tool yang cocok untuk setiap Obstacle
TOOL_MATCH = {
    OBSTACLE_BUSH: TOOL_KNIFE,
    OBSTACLE_ICE: TOOL_HAIRDRYER,
    OBSTACLE_DARK: TOOL_FLASHLIGHT,
    OBSTACLE_FOG: TOOL_SPONGE
}

# Durasi Hover untuk memicu aksi (detik)
HOLD_TIME_SLIDE = 0.40       # Tahan di dekat kotak kosong untuk geser puzzle
HOLD_TIME_EQUIP = 0.50       # Tahan mengepal di panel alat untuk mengambil alat
HOLD_TIME_CLEAR = 0.80       # Tahan mengepal dengan alat yang cocok untuk membersihkan
AUTO_DROP_OPEN_TIME = 0.30   # Lepas tangan terbuka 0.3s otomatis lepas alat
HOLD_TIME_CAPTURE_FIST = 1.5 # Kepalkan tangan 1.5s di layar capture untuk jepret

# Palet Warna Cyberpunk / Arcade (BGR format)
COLOR_BG_DARK = (20, 18, 26)
COLOR_PANEL_BG = (35, 30, 42)
COLOR_NEON_CYAN = (255, 215, 0)
COLOR_NEON_GOLD = (0, 215, 255)
COLOR_NEON_GREEN = (60, 235, 80)
COLOR_NEON_RED = (50, 50, 240)
COLOR_TEXT_WHITE = (245, 245, 250)
COLOR_TEXT_DIM = (160, 160, 175)


# ==================================================================================================
# 2. SISTEM ASET GAMBAR & IKON (ASSET MANAGER)
# ==================================================================================================
class AssetManager:
    """
    Mengelola pemuatan aset gambar eksternal (PNG ber-alpha channel) dari folder 'assets/'.
    Jika file gambar belum tersedia, fungsi ini otomatis menggambar representasi grafis
    prosedural berkualitas tinggi dan menyimpannya ke disk agar pengguna dapat melihatnya
    maupun menggantinya secara langsung dengan gambar kustom mereka sendiri.
    """
    def __init__(self, asset_dir="assets"):
        self.asset_dir = asset_dir
        self.images = {}
        self.ensure_assets_exist()
        self.load_all_assets()

    def ensure_assets_exist(self):
        """Membuat folder assets dan menghasilkan file fallback jika belum ada."""
        if not os.path.exists(self.asset_dir):
            os.makedirs(self.asset_dir, exist_ok=True)

        asset_generators = {
            "knife.png": self._draw_knife_asset,
            "hairdryer.png": self._draw_hairdryer_asset,
            "flashlight.png": self._draw_flashlight_asset,
            "sponge.png": self._draw_sponge_asset,
            "hand_open.png": self._draw_hand_open_asset,
            "hand_fist.png": self._draw_hand_fist_asset,
            "heart.png": self._draw_heart_asset,
            "frame.png": self._draw_frame_asset
        }

        for filename, generator in asset_generators.items():
            filepath = os.path.join(self.asset_dir, filename)
            if not os.path.exists(filepath):
                img = generator()
                cv2.imwrite(filepath, img)

    def load_all_assets(self):
        """Memuat seluruh file gambar PNG dengan 4-channel BGRA."""
        filenames = [
            "knife.png", "hairdryer.png", "flashlight.png", "sponge.png",
            "hand_open.png", "hand_fist.png", "heart.png", "frame.png"
        ]
        for name in filenames:
            path = os.path.join(self.asset_dir, name)
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is not None:
                # Pastikan memiliki channel alpha
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                elif img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                self.images[name] = img
            else:
                # Fallback in-memory jika file korup
                self.images[name] = np.zeros((128, 128, 4), dtype=np.uint8)

    # ---------------- Generator Grafis Prosedural Beresolusi Tinggi ----------------
    def _draw_knife_asset(self):
        """Ikon Pisau (Pisau Dapur Baja Tajam dengan Gagang Ergonomis)."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        # Bilah Pisau
        blade = np.array([[30, 25], [105, 25], [118, 50], [50, 50]], dtype=np.int32)
        cv2.fillPoly(img, [blade], (245, 245, 250, 255), cv2.LINE_AA)
        blade_edge = np.array([[30, 25], [105, 25], [116, 38], [50, 38]], dtype=np.int32)
        cv2.fillPoly(img, [blade_edge], (210, 210, 225, 255), cv2.LINE_AA)
        cv2.line(img, (105, 25), (118, 50), (255, 255, 255, 255), 2, cv2.LINE_AA)
        # Gagang Pisau
        handle = np.array([[18, 42], [52, 42], [42, 65], [10, 65]], dtype=np.int32)
        cv2.fillPoly(img, [handle], (40, 42, 55, 255), cv2.LINE_AA)
        # Paku Kuningan Gagang
        cv2.circle(img, (26, 53), 3, (0, 215, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (38, 53), 3, (0, 215, 255, 255), -1, cv2.LINE_AA)
        return img

    def _draw_hairdryer_asset(self):
        """Ikon Hairdryer (Corong pemanas udara panas dengan gelombang uap)."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        # Bodi Tabung
        cv2.rectangle(img, (35, 30), (85, 62), (230, 85, 45, 255), -1)
        cv2.rectangle(img, (85, 36), (105, 56), (75, 75, 85, 255), -1)
        # Pegangan Bawah
        handle_pts = np.array([[45, 62], [65, 62], [55, 105], [35, 105]], dtype=np.int32)
        cv2.fillPoly(img, [handle_pts], (60, 60, 70, 255), cv2.LINE_AA)
        # Gelombang Udara Panas
        cv2.ellipse(img, (112, 40), (8, 6), 0, -60, 60, (50, 160, 255, 240), 2, cv2.LINE_AA)
        cv2.ellipse(img, (116, 46), (10, 7), 0, -60, 60, (60, 210, 255, 240), 2, cv2.LINE_AA)
        cv2.ellipse(img, (112, 52), (8, 6), 0, -60, 60, (50, 160, 255, 240), 2, cv2.LINE_AA)
        return img

    def _draw_flashlight_asset(self):
        """Ikon Senter (Bodi taktis dengan sorotan cahaya kerucut kuning terang)."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        # Gagang Senter
        body_pts = np.array([[25, 75], [55, 45], [75, 65], [45, 95]], dtype=np.int32)
        cv2.fillPoly(img, [body_pts], (65, 65, 75, 255), cv2.LINE_AA)
        # Kepala Lensa
        head_pts = np.array([[50, 40], [80, 10], [95, 25], [65, 55]], dtype=np.int32)
        cv2.fillPoly(img, [head_pts], (95, 95, 105, 255), cv2.LINE_AA)
        # Sorot Cahaya (Beam)
        beam_pts = np.array([[88, 18], [125, 5], [125, 60], [88, 18]], dtype=np.int32)
        cv2.fillPoly(img, [beam_pts], (50, 235, 255, 190), cv2.LINE_AA)
        return img

    def _draw_sponge_asset(self):
        """Ikon Spons (Bantalan cuci berpori dengan busa sabun berkilau)."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        # Bodi Spons Kuning
        cv2.rectangle(img, (24, 45), (104, 95), (45, 215, 250, 255), -1)
        # Lapisan Hijau Penggosok
        cv2.rectangle(img, (24, 35), (104, 45), (55, 185, 65, 255), -1)
        # Pori-pori Spons
        for pos, r in [((45, 65), 5), ((75, 60), 6), ((60, 80), 4), ((85, 80), 5), ((38, 82), 4)]:
            cv2.circle(img, pos, r, (25, 165, 205, 255), -1, cv2.LINE_AA)
        # Gelembung Sabun
        cv2.circle(img, (40, 25), 6, (255, 255, 255, 230), 2, cv2.LINE_AA)
        cv2.circle(img, (60, 20), 8, (255, 255, 255, 230), 2, cv2.LINE_AA)
        return img

    def _draw_hand_open_asset(self):
        """Ikon Tangan Terbuka (Kursor Mode Geser Puzzle)."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        cv2.circle(img, (64, 76), 24, (255, 215, 0, 255), -1, cv2.LINE_AA)
        fingers = [
            ((42, 45), (50, 68)), ((54, 35), (58, 62)),
            ((66, 32), (66, 60)), ((78, 38), (74, 64)),
            ((90, 52), (80, 72))
        ]
        for tip, base in fingers:
            cv2.line(img, base, tip, (255, 215, 0, 255), 9, cv2.LINE_AA)
            cv2.circle(img, tip, 5, (255, 215, 0, 255), -1, cv2.LINE_AA)
        return img

    def _draw_hand_fist_asset(self):
        """Ikon Tangan Mengepal (Kursor Mode Ambil & Gunakan Alat)."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        cv2.circle(img, (64, 68), 26, (0, 180, 255, 255), -1, cv2.LINE_AA)
        for kx in [46, 58, 70, 82]:
            cv2.circle(img, (kx, 50), 9, (0, 180, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(img, (kx, 50), 4, (0, 220, 255, 255), -1, cv2.LINE_AA)
        cv2.ellipse(img, (45, 75), (14, 8), -30, 0, 360, (0, 160, 240, 255), -1, cv2.LINE_AA)
        return img

    def _draw_heart_asset(self):
        """Ikon Nyawa Hati Merah Bersinar."""
        img = np.zeros((128, 128, 4), dtype=np.uint8)
        cv2.circle(img, (46, 46), 26, (50, 50, 240, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (82, 46), 26, (50, 50, 240, 255), -1, cv2.LINE_AA)
        pts = np.array([[22, 54], [106, 54], [64, 108]], dtype=np.int32)
        cv2.fillPoly(img, [pts], (50, 50, 240, 255), cv2.LINE_AA)
        # Pantulan kilau putih
        cv2.circle(img, (42, 38), 7, (255, 255, 255, 200), -1, cv2.LINE_AA)
        return img

    def _draw_frame_asset(self):
        """Bingkai Konsol Arkade Futuristik untuk Papan Puzzle."""
        w, h = BOARD_SIZE + 40, BOARD_SIZE + 40
        img = np.zeros((h, w, 4), dtype=np.uint8)
        # Bevel luar
        cv2.rectangle(img, (0, 0), (w - 1, h - 1), (45, 40, 55, 255), 8)
        cv2.rectangle(img, (8, 8), (w - 9, h - 9), (255, 215, 0, 255), 2)
        # Sudut siku-siku futuristik
        L = 36
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        for cx, cy in corners:
            dx = 1 if cx == 0 else -1
            dy = 1 if cy == 0 else -1
            cv2.line(img, (cx, cy), (cx + dx * L, cy), (0, 215, 255, 255), 5, cv2.LINE_AA)
            cv2.line(img, (cx, cy), (cx, cy + dy * L), (0, 215, 255, 255), 5, cv2.LINE_AA)
        return img

    def overlay_alpha(self, canvas, img_rgba, x, y, target_size=None):
        """
        Menempelkan gambar RGBA ke canvas BGR menggunakan Alpha Blending (P4)
        secara tervektorisasi dengan clipping koordinat batas aman.
        """
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


# ==================================================================================================
# 3. IMPLEMENTASI MATERI PENGOLAHAN CITRA & VISI (PCV ENGINE: P1 - P5)
# ==================================================================================================
class PCVEngine:
    """
    Kumpulan fungsi pengolahan citra murni OpenCV & NumPy yang mengimplementasikan
    materi mata kuliah PCV (P1 sampai P5) untuk gameplay dan efek visual.
    """

    # ---------------- [P1] DASAR CITRA & OPERASI SPASIAL ----------------
    @staticmethod
    def flip_horizontal(frame):
        """P1: Mirroring kamera secara horizontal agar pergerakan tangan selaras."""
        return cv2.flip(frame, 1)

    @staticmethod
    def crop_square_grid(frame, crop_size=450):
        """P1: Pemotongan (Cropping) bingkai persegi di tengah kamera."""
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
        """
        P1: Kuantisasi kedalaman bit rendah (Low Bit-depth Quantization).
        Mengurangi level intensitas 8-bit (256 level) menjadi 2^bits level (misal 3-bit = 8 level)
        untuk menghasilkan efek grafis arcade retro 8-bit pada layar Game Over.
        """
        levels = 2 ** bits
        step = 256 // levels
        quantized = (image // step) * step + (step // 2)
        return np.clip(quantized, 0, 255).astype(np.uint8)

    # ---------------- [P2] OPERASI TITIK & TRANSFORMASI KONTRAS ----------------
    @staticmethod
    def apply_flash_effect(image, intensity=1.0):
        """P2: Efek Flash putih jepretan kamera (Operasi titik linear contrast blending)."""
        intensity = np.clip(intensity, 0.0, 1.0)
        white_overlay = np.full_like(image, 255)
        return cv2.addWeighted(image, 1.0 - intensity, white_overlay, intensity, 0)

    @staticmethod
    def apply_negative_lut(image):
        """P2: Transformasi Look-Up Table (LUT) Negatif (I' = 255 - I)."""
        lut_negative = 255 - np.arange(256, dtype=np.uint8)
        return cv2.LUT(image, lut_negative)

    @staticmethod
    def apply_gamma(image, gamma=4.0):
        """P2: Transformasi Daya Gamma (Power Law Transformation) I' = 255 * (I / 255)^gamma."""
        gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
        return cv2.LUT(image, gamma_table)

    # ---------------- [P3] FILTER SPASIAL & FREKUENSI ----------------
    @staticmethod
    def apply_sobel_edges(image):
        """P3: Filter Sobel (Turunan pertama arah X dan Y) untuk mendeteksi tepi tajam."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(sx**2 + sy**2)
        return np.clip(mag, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_median_blur(image, ksize=7):
        """P3: Median Filter spasial non-linear penghilang noise bintik."""
        return cv2.medianBlur(image, ksize)

    @staticmethod
    def apply_gaussian_fog(image, ksize=(15, 15)):
        """P3: Gaussian Blur spasial (Filter low-pass penapis kabut tebal)."""
        return cv2.GaussianBlur(image, ksize, 0)

    @staticmethod
    def apply_unsharp_mask(image, sigma=1.0, strength=1.5):
        """P3: Unsharp Masking (Penajaman frekuensi tinggi untuk alat Spons pembersih kabut)."""
        blurred = cv2.GaussianBlur(image, (9, 9), sigma)
        unsharp = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
        return np.clip(unsharp, 0, 255).astype(np.uint8)

    # ---------------- [P4 & P5] MORFOLOGI, SEGMEN WARNA & ANALISIS ----------------
    @staticmethod
    def apply_bush_obstacle(tile_img):
        """
        Rintangan Semak:
        Filter Sobel (P3) + Dilasi Morfologi (P5) + Alpha Blending Hijau (P4).
        """
        edges = PCVEngine.apply_sobel_edges(tile_img)
        # Dilasi Morfologi (P5) untuk membuat sulur semak tebal menjalar
        k_dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated_edges = cv2.dilate(edges, k_dil, iterations=2)

        # Alpha Blending Hijau (P4)
        green_tint = np.zeros_like(tile_img)
        green_tint[:, :, 1] = 190  # Hijau tajam
        green_tint[:, :, 0] = 30   # Biru rendah
        green_tint[:, :, 2] = 40   # Merah rendah

        vines = cv2.cvtColor(dilated_edges, cv2.COLOR_GRAY2BGR)
        vines[:, :, 0] = (vines[:, :, 0] * 0.15).astype(np.uint8)
        vines[:, :, 2] = (vines[:, :, 2] * 0.10).astype(np.uint8)

        base_blend = cv2.addWeighted(tile_img, 0.45, green_tint, 0.55, 0)
        return cv2.addWeighted(base_blend, 0.75, vines, 0.65, 0)

    @staticmethod
    def apply_ice_obstacle(tile_img):
        """
        Rintangan Es Beku:
        LUT Negatif (P2) + Median Filter (P3) + Cool Cyan Frost Tint.
        """
        neg = PCVEngine.apply_negative_lut(tile_img)
        med = PCVEngine.apply_median_blur(neg, 7)

        frost = med.copy()
        # Perkuat nuansa beku (Cyan-Blue)
        frost[:, :, 0] = np.clip(frost[:, :, 0].astype(np.int16) + 70, 0, 255).astype(np.uint8)
        frost[:, :, 1] = np.clip(frost[:, :, 1].astype(np.int16) + 40, 0, 255).astype(np.uint8)
        frost[:, :, 2] = (frost[:, :, 2] * 0.55).astype(np.uint8)
        return cv2.addWeighted(tile_img, 0.20, frost, 0.80, 0)

    @staticmethod
    def apply_dark_curse_obstacle(tile_img):
        """
        Rintangan Kutukan Gelap:
        Transformasi Gamma 4.0 (P2) + Vignette aura ungu pekat.
        """
        dark = PCVEngine.apply_gamma(tile_img, 4.0)
        h, w = tile_img.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (np.sqrt(cx**2 + cy**2))
        vignette = np.clip(dist * 1.6, 0, 1)[:, :, None]

        purple = np.zeros_like(tile_img)
        purple[:, :, 0] = 90
        purple[:, :, 2] = 90

        result = (dark * (1.0 - vignette * 0.6) + purple * (vignette * 0.4)).astype(np.uint8)
        return result

    @staticmethod
    def apply_fog_obstacle(tile_img):
        """
        Rintangan Kabut Tebal:
        Gaussian Blur 15x15 (P3) + Alpha Blending Kabut Putih Susu (P4).
        """
        blur = PCVEngine.apply_gaussian_fog(tile_img, (15, 15))
        fog_color = np.full_like(tile_img, 215)
        return cv2.addWeighted(blur, 0.45, fog_color, 0.55, 0)

    @staticmethod
    def clean_hand_mask(mask):
        """
        P5: Pembersihan Morfologi (Opening & Closing) pada masker biner tangan:
        - Opening: Menghilangkan salt-noise bintik kecil di latar belakang.
        - Closing: Menutup celah dan lubang di dalam telapak tangan.
        """
        k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask_open = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open)
        mask_clean = cv2.morphologyEx(mask_open, cv2.MORPH_CLOSE, k_close)
        return mask_clean


# ==================================================================================================
# 4. SISTEM PELACAK TANGAN REAL-TIME (HAND TRACKER: HSV & MORFOLOGI P4-P5)
# ==================================================================================================
class HandTracker:
    """
    Pelacak gestur tangan berbasis segmentasi warna HSV (P4), pembersihan Morfologi (P5),
    dan analisis komponen terhubung (connectedComponentsWithStats P5).
    """
    def __init__(self):
        # Nilai batas HSV default (kulit manusia standar)
        self.lower_hsv = np.array([0, 30, 60], dtype=np.uint8)
        self.upper_hsv = np.array([25, 200, 255], dtype=np.uint8)
        self.is_calibrated = False

        # Area referensi piksel telapak tangan terbuka (A_ref)
        self.ref_area = 15000
        self.current_area = 0

        # Koordinat centroid kursor k (EMA Smoothed)
        self.cursor_x = CANVAS_WIDTH // 2
        self.cursor_y = CANVAS_HEIGHT // 2
        self.is_fist = False
        self.hand_detected = False

        # Timer untuk gestur lepas alat (Auto-Drop)
        self.open_hand_timer = 0.0

        # Masker tangan biner terkini untuk visualisasi PiP mini
        self.latest_mask = None

    def calibrate_from_roi(self, frame_hsv, roi_rect):
        """
        Mengambil sampel warna dari Region of Interest (ROI) di tengah layar pada STATE_HOME.
        Menghitung median H, S, V dan area awal tangan untuk kalibrasi adaptif.
        """
        rx, ry, rw, rh = roi_rect
        roi = frame_hsv[ry:ry+rh, rx:rx+rw]
        if roi.size == 0:
            return False

        h_med = np.median(roi[:, :, 0])
        s_med = np.median(roi[:, :, 1])
        v_med = np.median(roi[:, :, 2])

        # Bentuk rentang toleransi adaptif
        h_low = max(0, int(h_med - 18))
        h_high = min(179, int(h_med + 18))
        s_low = max(30, int(s_med - 50))
        s_high = min(255, int(s_med + 65))
        v_low = max(40, int(v_med - 60))
        v_high = min(255, int(v_med + 70))

        self.lower_hsv = np.array([h_low, s_low, v_low], dtype=np.uint8)
        self.upper_hsv = np.array([h_high, s_high, v_high], dtype=np.uint8)

        # Uji segmentasi di ROI untuk mendapatkan luas piksel tangan referensi
        mask_roi = cv2.inRange(roi, self.lower_hsv, self.upper_hsv)
        clean_roi = PCVEngine.clean_hand_mask(mask_roi)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(clean_roi, connectivity=8)

        max_a = 0
        for i in range(1, num_labels):
            a = stats[i, cv2.CC_STAT_AREA]
            if a > max_a:
                max_a = a

        # Perkiraan area tangan penuh terhadap resolusi frame
        self.ref_area = max(max_a * 2, 4500)
        self.is_calibrated = True
        return True

    def process_frame(self, frame, dt):
        """
        Memproses frame kamera:
        1. Segmentasi warna HSV (P4)
        2. Morfologi Opening/Closing (P5)
        3. connectedComponentsWithStats (P5) untuk mendapatkan centroid & area
        4. Deteksi gestur Tangan Terbuka vs Mengepal (< 65% A_ref)
        """
        h_cam, w_cam = frame.shape[:2]
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        raw_mask = cv2.inRange(frame_hsv, self.lower_hsv, self.upper_hsv)
        clean_mask = PCVEngine.clean_hand_mask(raw_mask)
        self.latest_mask = clean_mask

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(clean_mask, connectivity=8)

        largest_area = 0
        best_cx, best_cy = self.cursor_x, self.cursor_y
        self.hand_detected = False

        # Cari komponen terhubung terbesar (abaikan label 0 latar belakang)
        min_detect_area = max(800, int(self.ref_area * 0.15))
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > largest_area and area >= min_detect_area:
                largest_area = area
                best_cx = centroids[i, 0]
                best_cy = centroids[i, 1]
                self.hand_detected = True

        if self.hand_detected:
            self.current_area = largest_area

            # Petakan koordinat kamera ke koordinat display game (1280x720)
            target_x = int(best_cx * (CANVAS_WIDTH / w_cam))
            target_y = int(best_cy * (CANVAS_HEIGHT / h_cam))

            # Exponential Moving Average (EMA) Smoothing untuk mengurangi getaran webcam
            alpha_smooth = 0.35
            self.cursor_x = int(alpha_smooth * target_x + (1.0 - alpha_smooth) * self.cursor_x)
            self.cursor_y = int(alpha_smooth * target_y + (1.0 - alpha_smooth) * self.cursor_y)

            # Deteksi Gestur:
            # Gesture 2 (Mengepal / Fist) jika Luas Area Turun < 65% dari Area Referensi
            ratio = self.current_area / max(1, self.ref_area)
            if ratio < 0.65:
                self.is_fist = True
                self.open_hand_timer = 0.0
            else:
                self.is_fist = False
                self.open_hand_timer += dt
        else:
            self.current_area = 0
            self.open_hand_timer += dt


# ==================================================================================================
# 5. STRUKTUR PAPAN PUZZLE & PENGACAKAN 100% SOLVABLE
# ==================================================================================================
class PuzzleEngine:
    """
    Logika papan puzzle 3x3 (8 keping foto dan 1 kotak kosong).
    Pengacakan menggunakan metode Random Legal Moves dari keadaan terpecahkan,
    sehingga terjamin 100% solvable (dapat diselesaikan secara sah).
    """
    def __init__(self):
        # Susunan terpecahkan: 0..7 keping, 8 adalah kotak kosong
        self.tiles = list(range(9))
        self.empty_val = 8
        self.stage = 1

        # Gambar asli kepingan (masing-masing 150x150)
        self.tile_images = [None] * 9
        self.full_photo = None

        # Graf Ketetanggaan Grid 3x3 untuk langkah geser legal
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
        """Memotong foto 450x450 menjadi 9 kepingan 150x150."""
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
        """
        Mengacak susunan papan hanya melalui langkah-langkah geser legal
        berturut-turut mulai dari kondisi tersusun rapi.
        """
        self.tiles = list(range(9))
        last_empty_pos = -1

        for _ in range(num_moves):
            empty_idx = self.tiles.index(self.empty_val)
            valid_swaps = self.neighbors[empty_idx]

            # Cegah langsung membatalkan langkah sebelumnya jika ada pilihan lain
            candidate_swaps = [pos for pos in valid_swaps if pos != last_empty_pos]
            if not candidate_swaps:
                candidate_swaps = valid_swaps

            chosen_pos = random.choice(candidate_swaps)
            # Tukar kotak kosong dengan kepingan tetangga
            self.tiles[empty_idx], self.tiles[chosen_pos] = self.tiles[chosen_pos], self.tiles[empty_idx]
            last_empty_pos = empty_idx

    def can_slide(self, tile_grid_pos):
        """Mengecek apakah kepingan berada tepat di sebelah kotak kosong."""
        empty_pos = self.tiles.index(self.empty_val)
        return tile_grid_pos in self.neighbors[empty_pos]

    def slide_tile(self, tile_grid_pos):
        """Melakukan pergeseran kepingan ke kotak kosong."""
        empty_pos = self.tiles.index(self.empty_val)
        if tile_grid_pos in self.neighbors[empty_pos]:
            self.tiles[empty_pos], self.tiles[tile_grid_pos] = self.tiles[tile_grid_pos], self.tiles[empty_pos]
            return True
        return False

    def is_solved(self):
        """Mengecek apakah susunan sudah kembali terurut 0..8."""
        return self.tiles == list(range(9))


# ==================================================================================================
# 6. SISTEM RINTANGAN (OBSTACLES) & ALAT (TOOLS)
# ==================================================================================================
class ObstacleManager:
    """
    Mengelola kemunculan dan pembersihan rintangan pada kepingan puzzle:
    - Semak (Idle timer jika keping tidak disentuh)
    - Es Beku, Kutukan Gelap, Kabut Tebal (Muncul berkala per stage)
    - Deteksi kondisi Instant Deadlock
    """
    def __init__(self):
        # Dictionary {grid_pos: obstacle_type}
        self.grid_obstacles = {}
        # Dictionary {grid_pos: detik_idle}
        self.tile_idle_timers = {i: 0.0 for i in range(9)}

        self.time_since_last_spawn = 0.0
        self.stage = 1

    def reset_for_stage(self, stage):
        """Reset seluruh rintangan dan konfigurasi timer untuk stage baru."""
        self.stage = stage
        self.grid_obstacles = {}
        self.tile_idle_timers = {i: 0.0 for i in range(9)}
        self.time_since_last_spawn = 0.0

    def get_stage_settings(self):
        """
        Pengaturan per stage sesuai spesifikasi:
        Stage 1: Hanya Semak (Idle: 3.5s, Spawn interval: 4.5s)
        Stage 2: Semak & Es Beku (Idle: 3.0s, Spawn interval: 3.5s)
        Stage 3: Semua rintangan (Idle: 2.5s, Spawn interval: 2.5s)
        """
        if self.stage == 1:
            return {
                "idle_limit": 3.5,
                "spawn_interval": 4.5,
                "allowed_obstacles": [OBSTACLE_BUSH],
                "active_tools": [TOOL_KNIFE]
            }
        elif self.stage == 2:
            return {
                "idle_limit": 3.0,
                "spawn_interval": 3.5,
                "allowed_obstacles": [OBSTACLE_BUSH, OBSTACLE_ICE],
                "active_tools": [TOOL_KNIFE, TOOL_HAIRDRYER]
            }
        else:
            return {
                "idle_limit": 2.5,
                "spawn_interval": 2.5,
                "allowed_obstacles": [OBSTACLE_BUSH, OBSTACLE_ICE, OBSTACLE_DARK, OBSTACLE_FOG],
                "active_tools": [TOOL_KNIFE, TOOL_HAIRDRYER, TOOL_FLASHLIGHT, TOOL_SPONGE]
            }

    def update(self, dt, hovered_grid_pos, empty_grid_pos):
        """Memperbarui idle timer dan memunculkan rintangan."""
        cfg = self.get_stage_settings()

        # Update Idle Timer Semak
        for pos in range(9):
            if pos == empty_grid_pos:
                self.tile_idle_timers[pos] = 0.0
                continue

            # Jika kursor melayang di atas kepingan dengan tangan terbuka, reset timer
            if pos == hovered_grid_pos:
                self.tile_idle_timers[pos] = 0.0
            else:
                self.tile_idle_timers[pos] += dt
                # Jika melebihi batas idle dan belum ada rintangan, semak tumbuh!
                if self.tile_idle_timers[pos] >= cfg["idle_limit"]:
                    if pos not in self.grid_obstacles:
                        self.grid_obstacles[pos] = OBSTACLE_BUSH
                        self.tile_idle_timers[pos] = 0.0

        # Spawn rintangan acak berkala
        self.time_since_last_spawn += dt
        if self.time_since_last_spawn >= cfg["spawn_interval"]:
            self.time_since_last_spawn = 0.0
            free_slots = [p for p in range(9) if p != empty_grid_pos and p not in self.grid_obstacles]
            if free_slots:
                target_pos = random.choice(free_slots)
                chosen_obs = random.choice(cfg["allowed_obstacles"])
                self.grid_obstacles[target_pos] = chosen_obs

    def check_deadlock(self, puzzle_engine):
        """
        Deteksi Instant Deadlock:
        1. Semua tetangga di sekeliling Kotak Kosong terkunci rintangan (tidak ada langkah legal), ATAU
        2. 6 dari 8 kepingan tertutup rintangan secara bersamaan.
        """
        empty_pos = puzzle_engine.tiles.index(puzzle_engine.empty_val)
        neighbors = puzzle_engine.neighbors[empty_pos]

        # Cek apakah seluruh tetangga terkunci
        all_neighbors_locked = all(n in self.grid_obstacles for n in neighbors)

        # Cek jumlah total rintangan
        total_obstacles = len(self.grid_obstacles)

        return all_neighbors_locked or (total_obstacles >= 6)

    def clear_all(self):
        """Membersihkan seluruh rintangan (digunakan saat deadlock terpicu)."""
        self.grid_obstacles.clear()
        for p in self.tile_idle_timers:
            self.tile_idle_timers[p] = 0.0


# ==================================================================================================
# 7. SISTEM RENDERER TAMPILAN & ANTARMUKA (HUD & UI RENDERER)
# ==================================================================================================
class UIRenderer:
    """
    Menggambar seluruh komponen visual antarmuka (HUD) arkade:
    - Header Bar (Stage, Judul Game, Skor, Nyawa, Timer)
    - Panel Peralatan Kiri dan Kanan
    - Bingkai Konsol Papan Puzzle di Tengah
    - Kepingan Gambar dengan Efek Transformasi PCV
    - Kursor Tangan Interaktif & Indikator Pengisian Aksi (Radial Hover Gauge)
    - Jendela Mini PiP Kamera & Segmentasi Masker
    """
    def __init__(self, asset_mgr):
        self.assets = asset_mgr

        # Definisi Slot Alat di Layar
        # Panel Kiri (Tool 1 & 2)
        self.tool_slots = {
            TOOL_KNIFE: {"name": "Pisau", "key": "[1]", "rect": (40, 200, 160, 130), "icon": "knife.png"},
            TOOL_HAIRDRYER: {"name": "Hairdryer", "key": "[2]", "rect": (40, 360, 160, 130), "icon": "hairdryer.png"},
            # Panel Kanan (Tool 3 & 4)
            TOOL_FLASHLIGHT: {"name": "Senter", "key": "[3]", "rect": (1080, 200, 160, 130), "icon": "flashlight.png"},
            TOOL_SPONGE: {"name": "Spons", "key": "[4]", "rect": (1080, 360, 160, 130), "icon": "sponge.png"},
        }

    def render_hud(self, canvas, stage, score, lives, elapsed_sec):
        """Menggambar bar judul dan status arkade di bagian atas layar."""
        # Background bar atas
        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 75), COLOR_PANEL_BG, -1)
        cv2.line(canvas, (0, 75), (CANVAS_WIDTH, 75), COLOR_NEON_CYAN, 2)

        # STAGE INDIKATOR
        stage_text = f"STAGE {stage}/3"
        cv2.putText(canvas, stage_text, (40, 48), cv2.FONT_HERSHEY_DUPLEX, 0.9, COLOR_NEON_GOLD, 2, cv2.LINE_AA)

        # JUDUL GAME DI TENGAH
        title_text = "PUZZLE CAMS"
        (tw, _), _ = cv2.getTextSize(title_text, cv2.FONT_HERSHEY_TRIPLEX, 1.2, 2)
        tx = (CANVAS_WIDTH - tw) // 2
        # Glow bayangan judul
        cv2.putText(canvas, title_text, (tx + 2, 52), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (20, 20, 20), 3, cv2.LINE_AA)
        cv2.putText(canvas, title_text, (tx, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, COLOR_NEON_CYAN, 2, cv2.LINE_AA)

        # SKOR
        score_text = f"SCORE: {score:05d}"
        cv2.putText(canvas, score_text, (750, 48), cv2.FONT_HERSHEY_DUPLEX, 0.85, COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

        # NYAWA (Ikon Hati)
        heart_img = self.assets.images.get("heart.png")
        hx_start = 980
        for i in range(3):
            hx = hx_start + (i * 38)
            if i < lives:
                self.assets.overlay_alpha(canvas, heart_img, hx, 22, (30, 30))
            else:
                # Hati redup/kosong jika nyawa berkurang
                cv2.circle(canvas, (hx + 15, 37), 12, (60, 60, 70), 2, cv2.LINE_AA)

        # TIMER
        mins = int(elapsed_sec) // 60
        secs = int(elapsed_sec) % 60
        timer_text = f"{mins:02d}:{secs:02d}"
        cv2.putText(canvas, timer_text, (1140, 48), cv2.FONT_HERSHEY_DUPLEX, 0.85, COLOR_NEON_GOLD, 2, cv2.LINE_AA)

    def render_tool_panels(self, canvas, active_tools, equipped_tool, hover_tool, hover_progress):
        """Menggambar panel peralatan kiri dan kanan beserta status dan icon."""
        for tool_id, info in self.tool_slots.items():
            rx, ry, rw, rh = info["rect"]
            is_active = tool_id in active_tools
            is_equipped = (equipped_tool == tool_id)
            is_hovered = (hover_tool == tool_id)

            # Warna Card Slot
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

            # Gambar background slot
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), bg_col, -1)
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), border_col, 2)

            # Nama Tool & Tombol Pintas
            cv2.putText(canvas, info["name"], (rx + 12, ry + 24), cv2.FONT_HERSHEY_DUPLEX, 0.55, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
            cv2.putText(canvas, info["key"], (rx + rw - 35, ry + 24), cv2.FONT_HERSHEY_PLAIN, 1.1, COLOR_NEON_GOLD, 1, cv2.LINE_AA)

            # Ikon Tool
            icon_img = self.assets.images.get(info["icon"])
            ix = rx + (rw - 64) // 2
            iy = ry + 35
            if icon_img is not None:
                if is_active:
                    self.assets.overlay_alpha(canvas, icon_img, ix, iy, (64, 64))
                else:
                    # Tampilkan siluet gelap terkunci jika stage belum mengizinkan
                    locked_icon = icon_img.copy()
                    locked_icon[:, :, :3] = (locked_icon[:, :, :3] * 0.25).astype(np.uint8)
                    self.assets.overlay_alpha(canvas, locked_icon, ix, iy, (64, 64))
                    cv2.putText(canvas, "TERKUNCI", (rx + 35, ry + 75), cv2.FONT_HERSHEY_DUPLEX, 0.5, (100, 100, 110), 1, cv2.LINE_AA)

            # Progress Bar Hovering saat mengambil alat
            if is_hovered and hover_progress > 0.0:
                bar_w = int((rw - 20) * hover_progress)
                cv2.rectangle(canvas, (rx + 10, ry + rh - 10), (rx + 10 + bar_w, ry + rh - 6), COLOR_NEON_GOLD, -1)

            # Status Badge
            if is_equipped:
                cv2.rectangle(canvas, (rx + 25, ry + rh - 20), (rx + rw - 25, ry + rh - 4), COLOR_NEON_GREEN, -1)
                cv2.putText(canvas, "DIPEGANG", (rx + 38, ry + rh - 8), cv2.FONT_HERSHEY_PLAIN, 0.9, (20, 20, 20), 1, cv2.LINE_AA)

    def render_puzzle_board(self, canvas, puzzle, obstacles, hovered_grid_pos, hover_progress):
        """Menggambar papan puzzle 3x3, bingkai estetik konsol, dan rintangan PCV."""
        # Bingkai Konsol Arkade (Border Estetik)
        frame_img = self.assets.images.get("frame.png")
        if frame_img is not None:
            self.assets.overlay_alpha(canvas, frame_img, BOARD_X - 20, BOARD_Y - 20, (BOARD_SIZE + 40, BOARD_SIZE + 40))
        else:
            # Fallback border jika gambar frame tidak ada
            cv2.rectangle(canvas, (BOARD_X - 8, BOARD_Y - 8), (BOARD_X + BOARD_SIZE + 8, BOARD_Y + BOARD_SIZE + 8), COLOR_NEON_CYAN, 3)

        empty_val = puzzle.empty_val
        empty_pos = puzzle.tiles.index(empty_val)

        # Gambar 9 Slot Kepingan
        for grid_pos in range(9):
            r = grid_pos // GRID_COLS
            c = grid_pos % GRID_COLS
            tx = BOARD_X + (c * TILE_SIZE)
            ty = BOARD_Y + (r * TILE_SIZE)

            tile_id = puzzle.tiles[grid_pos]

            if tile_id == empty_val:
                # KOTAK KOSONG: Tampilan ceruk metalik gelap
                cv2.rectangle(canvas, (tx, ty), (tx + TILE_SIZE, ty + TILE_SIZE), (22, 18, 25), -1)
                cv2.rectangle(canvas, (tx + 2, ty + 2), (tx + TILE_SIZE - 2, ty + TILE_SIZE - 2), (40, 36, 48), 1)
                # Garis diagonal penanda kotak kosong
                cv2.line(canvas, (tx + 20, ty + 20), (tx + TILE_SIZE - 20, ty + TILE_SIZE - 20), (32, 28, 38), 2)
                cv2.line(canvas, (tx + TILE_SIZE - 20, ty + 20), (tx + 20, ty + TILE_SIZE - 20), (32, 28, 38), 2)
            else:
                # KEPINGAN BERGAMBAR
                raw_tile = puzzle.tile_images[tile_id]
                if raw_tile is None:
                    raw_tile = np.full((TILE_SIZE, TILE_SIZE, 3), 80, dtype=np.uint8)

                # Cek Rintangan Aktif pada kepingan ini (Penerapan Transformasi PCV)
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

                # Tempelkan ke kanvas
                canvas[ty:ty+TILE_SIZE, tx:tx+TILE_SIZE] = display_tile

                # Border pembatas kepingan
                cv2.rectangle(canvas, (tx, ty), (tx + TILE_SIZE, ty + TILE_SIZE), (30, 25, 35), 1)

                # Nomor kepingan di sudut kiri atas (nomor 1 sampai 8)
                num_badge = str(tile_id + 1)
                cv2.rectangle(canvas, (tx + 4, ty + 4), (tx + 24, ty + 24), (20, 20, 20), -1)
                cv2.putText(canvas, num_badge, (tx + 8, ty + 19), cv2.FONT_HERSHEY_PLAIN, 1.0, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

                # Label indikator rintangan jika terkunci
                if obs_type != OBSTACLE_NONE:
                    # Bar penanda terkunci rintangan
                    obs_label = OBSTACLE_NAMES[obs_type]
                    cv2.rectangle(canvas, (tx, ty + TILE_SIZE - 22), (tx + TILE_SIZE, ty + TILE_SIZE), (15, 15, 20), -1)
                    cv2.putText(canvas, obs_label, (tx + 12, ty + TILE_SIZE - 6), cv2.FONT_HERSHEY_PLAIN, 0.95, (0, 215, 255), 1, cv2.LINE_AA)

            # Sorotan Kursor saat Hovering
            if grid_pos == hovered_grid_pos:
                # Jika kepingan bisa digeser ke kotak kosong
                is_movable = (grid_pos in puzzle.neighbors[empty_pos]) and (grid_pos not in obstacles)
                has_obs = (grid_pos in obstacles)

                if is_movable:
                    border_color = COLOR_NEON_GREEN
                elif has_obs:
                    border_color = COLOR_NEON_RED
                else:
                    border_color = COLOR_NEON_GOLD

                cv2.rectangle(canvas, (tx + 1, ty + 1), (tx + TILE_SIZE - 1, ty + TILE_SIZE - 1), border_color, 2)

                # Lingkaran Indikator Progres Aksi (Slide / Clear)
                if hover_progress > 0.0:
                    center_pt = (tx + TILE_SIZE // 2, ty + TILE_SIZE // 2)
                    radius = 28
                    cv2.circle(canvas, center_pt, radius, (20, 20, 20), -1)
                    cv2.circle(canvas, center_pt, radius, border_color, 2, cv2.LINE_AA)
                    # Arc progres melingkar
                    angle = int(360 * hover_progress)
                    cv2.ellipse(canvas, center_pt, (radius, radius), -90, 0, angle, border_color, 4, cv2.LINE_AA)

    def render_cursor(self, canvas, tracker, equipped_tool):
        """Menggambar kursor tangan dinamis atau ikon alat mengambang (Alpha Blended)."""
        cx, cy = tracker.cursor_x, tracker.cursor_y
        is_fist = tracker.is_fist

        if equipped_tool != TOOL_NONE:
            # Mode Membawa Alat: Kursor berubah menjadi gambar ikon alat yang melayang (P4)
            tool_info = self.tool_slots.get(equipped_tool)
            if tool_info:
                icon_img = self.assets.images.get(tool_info["icon"])
                if icon_img is not None:
                    # Floating offset dinamis
                    offset_y = int(math.sin(time.time() * 6.0) * 4)
                    self.assets.overlay_alpha(canvas, icon_img, cx - 32, cy - 32 + offset_y, (64, 64))
                    # Reticle bidik kecil di ujung alat
                    cv2.circle(canvas, (cx, cy), 6, COLOR_NEON_GOLD, 2, cv2.LINE_AA)
        else:
            # Mode Tangan Standar (Mode Geser / Mode Kepal)
            cursor_name = "hand_fist.png" if is_fist else "hand_open.png"
            cursor_img = self.assets.images.get(cursor_name)
            if cursor_img is not None:
                self.assets.overlay_alpha(canvas, cursor_img, cx - 24, cy - 24, (48, 48))
            else:
                # Fallback geometric reticle
                reticle_col = COLOR_NEON_GOLD if is_fist else COLOR_NEON_CYAN
                cv2.circle(canvas, (cx, cy), 16, reticle_col, 2, cv2.LINE_AA)
                cv2.circle(canvas, (cx, cy), 4, reticle_col, -1, cv2.LINE_AA)

    def render_pip_camera(self, canvas, frame, tracker):
        """
        Jendela Picture-in-Picture (PiP) mini di sudut kiri bawah:
        Menampilkan video live webcam + kontur segmentasi masker tangan (P4-P5)
        sehingga pemain mendapatkan umpan balik visual langsung dari gestur tangannya.
        """
        pip_w, pip_h = 160, 120
        pip_x, pip_y = 40, CANVAS_HEIGHT - pip_h - 20

        # Background frame pip
        cv2.rectangle(canvas, (pip_x - 2, pip_y - 2), (pip_x + pip_w + 2, pip_y + pip_h + 2), COLOR_NEON_CYAN, 1)

        # Resize video kamera
        small_cam = cv2.resize(frame, (pip_w, pip_h), interpolation=cv2.INTER_AREA)

        # Overlay kontur tangan jika masker tersedia
        if tracker.latest_mask is not None:
            small_mask = cv2.resize(tracker.latest_mask, (pip_w, pip_h), interpolation=cv2.INTER_NEAREST)
            contours, _ = cv2.findContours(small_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(small_cam, contours, -1, COLOR_NEON_GREEN, 1)

        canvas[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = small_cam

        # Label status gestur
        gesture_str = "FIST (KEPAL)" if tracker.is_fist else "OPEN (BUKA)"
        badge_col = COLOR_NEON_GOLD if tracker.is_fist else COLOR_NEON_GREEN
        cv2.rectangle(canvas, (pip_x, pip_y), (pip_x + pip_w, pip_y + 18), (20, 20, 20), -1)
        cv2.putText(canvas, gesture_str, (pip_x + 6, pip_y + 14), cv2.FONT_HERSHEY_PLAIN, 0.9, badge_col, 1, cv2.LINE_AA)

        # Bar rasio area tangan terhadap referensi
        ratio = min(1.0, tracker.current_area / max(1, tracker.ref_area))
        bar_len = int((pip_w - 10) * ratio)
        cv2.rectangle(canvas, (pip_x + 5, pip_y + pip_h - 8), (pip_x + pip_w - 5, pip_y + pip_h - 4), (40, 40, 40), -1)
        cv2.rectangle(canvas, (pip_x + 5, pip_y + pip_h - 8), (pip_x + 5 + bar_len, pip_y + pip_h - 4), badge_col, -1)


# ==================================================================================================
# 8. KELAS UTAMA PERMAINAN (PUZZLE CAMS GAME CONTROLLER)
# ==================================================================================================
class PuzzleCamsGame:
    """
    State machine dan pengendali alur permainan utama "PUZZLE CAMS".
    Mengintegrasikan kamera webcam, pelacakan tangan, papan puzzle, dan sistem penilaian.
    """
    def __init__(self):
        # Inisialisasi Kamera Webcam
        self.cap = cv2.VideoCapture(0)
        self.using_simulated_camera = False

        if not self.cap.isOpened():
            print("[PERINGATAN] Kamera fisik tidak terdeteksi! Mengaktifkan simulator kamera virtual.")
            self.using_simulated_camera = True
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Komponen Game
        self.assets = AssetManager("assets")
        self.tracker = HandTracker()
        self.puzzle = PuzzleEngine()
        self.obstacles = ObstacleManager()
        self.ui = UIRenderer(self.assets)

        # Status State Game
        self.state = STATE_HOME
        self.stage = 1
        self.score = 0
        self.lives = 3
        self.game_start_time = time.time()
        self.stage_start_time = time.time()

        # Tool yang sedang dipegang
        self.equipped_tool = TOOL_NONE

        # Timer & Tracking Hover
        self.hover_grid_pos = -1
        self.hover_grid_timer = 0.0

        self.hover_tool_id = TOOL_NONE
        self.hover_tool_timer = 0.0

        # Timer Pose Kepal pada Layar Capture
        self.capture_fist_timer = 0.0
        self.capture_countdown = -1.0

        # Efek Visual Flash (Jepretan / Deadlock)
        self.flash_intensity = 0.0
        self.deadlock_flash_timer = 0.0

        # Timer Transisi Stage Clear
        self.stage_clear_timer = 0.0

        # ROI Kalibrasi di Layar HOME
        roi_size = 200
        self.calib_roi = (
            (CANVAS_WIDTH - roi_size) // 2,
            (CANVAS_HEIGHT - roi_size) // 2,
            roi_size,
            roi_size
        )

        # Dukungan Kontrol Mouse (Fallback / Pengujian Demo)
        self.mouse_mode = False
        self.mouse_down = False

    def setup_window(self):
        """Membuat window OpenCV dan mengaitkan callback mouse."""
        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW_TITLE, self._on_mouse_event)

    def _on_mouse_event(self, event, x, y, flags, param):
        """Callback mouse untuk mendukung pengujian tanpa webcam."""
        if self.mouse_mode:
            self.tracker.cursor_x = x
            self.tracker.cursor_y = y
            if event == cv2.EVENT_LBUTTONDOWN:
                self.mouse_down = True
                self.tracker.is_fist = True
            elif event == cv2.EVENT_LBUTTONUP:
                self.mouse_down = False
                self.tracker.is_fist = False

    def read_camera_frame(self):
        """Membaca frame webcam (di-flip horizontal P1) atau membuat frame simulasi."""
        if not self.using_simulated_camera:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return PCVEngine.flip_horizontal(frame)

        # Fallback simulator kamera virtual jika webcam fisik tidak ada
        sim_frame = np.full((480, 640, 3), 40, dtype=np.uint8)
        # Efek grid dinamis bergerak
        t = time.time()
        for i in range(0, 640, 40):
            cv2.line(sim_frame, (i, 0), (i, 480), (50, 50, 60), 1)
        for j in range(0, 480, 40):
            cv2.line(sim_frame, (0, j), (640, j), (50, 50, 60), 1)
        cv2.putText(sim_frame, "SIMULASI KAMERA WEBCAM", (180, 240), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 215, 255), 1)
        return sim_frame

    # ---------------- ALUR STATE MACHINE PERMAINAN ----------------

    def run(self):
        """Looping utama permainan."""
        self.setup_window()
        last_time = time.time()

        while True:
            cur_time = time.time()
            dt = cur_time - last_time
            last_time = cur_time

            # 1. Baca frame kamera
            frame = self.read_camera_frame()

            # 2. Proses pelacakan tangan jika tidak dalam mode mouse murni
            if not self.mouse_mode:
                self.tracker.process_frame(frame, dt)

            # 3. Logika Auto-Drop alat jika tangan terbuka selama >= 0.3 detik
            if self.equipped_tool != TOOL_NONE:
                if not self.tracker.is_fist and self.tracker.open_hand_timer >= AUTO_DROP_OPEN_TIME:
                    self.equipped_tool = TOOL_NONE

            # 4. Kanvas display utama
            canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH, 3), COLOR_BG_DARK, dtype=np.uint8)

            # 5. Eksekusi state aktif
            if self.state == STATE_HOME:
                self._update_and_render_home(canvas, frame, dt)
            elif self.state == STATE_CAPTURE:
                self._update_and_render_capture(canvas, frame, dt)
            elif self.state == STATE_PLAYING:
                self._update_and_render_playing(canvas, frame, dt)
            elif self.state == STATE_STAGE_CLEAR:
                self._update_and_render_stage_clear(canvas, dt)
            elif self.state in (STATE_GAME_OVER, STATE_VICTORY):
                self._update_and_render_end(canvas, dt)

            # 6. Tampilkan ke layar
            cv2.imshow(WINDOW_TITLE, canvas)

            # 7. Penanganan tombol keyboard
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break
            self._handle_keyboard_shortcuts(key, frame)

        # Bersihkan resource saat keluar
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()

    def _handle_keyboard_shortcuts(self, key, frame):
        """Menangani tombol pintas darurat dan pengujian demo."""
        if key == ord(' '):
            if self.state == STATE_HOME:
                # Picu kalibrasi warna HSV
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                success = self.tracker.calibrate_from_roi(hsv, self.calib_roi)
                if success:
                    self.state = STATE_CAPTURE
                    self.capture_fist_timer = 0.0
                    self.capture_countdown = -1.0
            elif self.state == STATE_CAPTURE:
                # Jepret manual
                self._trigger_photo_capture(frame)

        elif key in (ord('n'), ord('N')):
            # [N] INSTANT STAGE CLEAR (PINTAS DEMO & PENILAIAN)
            if self.state == STATE_PLAYING:
                self._complete_current_stage()
            elif self.state == STATE_STAGE_CLEAR:
                self.stage_clear_timer = 0.0  # Langsung lewati transisi 3 detik

        elif key in (ord('r'), ord('R')):
            # [R] RESTART PERMAINAN DARI AWAL
            self.stage = 1
            self.score = 0
            self.lives = 3
            self.equipped_tool = TOOL_NONE
            self.state = STATE_HOME

        elif key in (ord('d'), ord('D')):
            # [D] PAKSA INSTANT DEADLOCK UNTUK TESTING
            if self.state == STATE_PLAYING:
                self._trigger_deadlock()

        elif key in (ord('m'), ord('M')):
            # [M] TOGGLE MOUSE / WEBCAM CONTROL
            self.mouse_mode = not self.mouse_mode

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

    # ---------------- HANDLER PER-STATE GAMEPLAY ----------------

    def _update_and_render_home(self, canvas, frame, dt):
        """STATE_HOME: Layar kalibrasi awal warna HSV dan ukuran tangan."""
        # Tampilkan video kamera layar penuh
        cam_resized = cv2.resize(frame, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_LINEAR)
        canvas[:] = cam_resized

        # Gelapkan sedikit untuk keterbacaan teks
        overlay = np.zeros_like(canvas)
        canvas[:] = cv2.addWeighted(canvas, 0.70, overlay, 0.30, 0)

        # Kotak ROI Kalibrasi di Tengah
        rx, ry, rw, rh = self.calib_roi
        cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), COLOR_NEON_GOLD, 3)

        # Crosshair di tengah ROI
        cx, cy = rx + rw // 2, ry + rh // 2
        cv2.line(canvas, (cx - 15, cy), (cx + 15, cy), COLOR_NEON_CYAN, 2)
        cv2.line(canvas, (cx, cy - 15), (cx, cy + 15), COLOR_NEON_CYAN, 2)

        # Petunjuk Teks
        cv2.putText(canvas, "PUZZLE CAMS - KALIBRASI SENSOR TANGAN", (280, 100), cv2.FONT_HERSHEY_TRIPLEX, 1.0, COLOR_NEON_CYAN, 2, cv2.LINE_AA)
        cv2.putText(canvas, "1. Letakkan telapak tangan terbuka di dalam kotak kuning", (290, 160), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, "2. Tekan tombol [SPACE] untuk mengambil sampel warna HSV & area", (250, 200), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_NEON_GOLD, 1, cv2.LINE_AA)
        cv2.putText(canvas, "(Tombol [M] untuk toggle kontrol Mouse jika tidak ada kamera)", (310, CANVAS_HEIGHT - 60), cv2.FONT_HERSHEY_PLAIN, 1.2, COLOR_TEXT_DIM, 1, cv2.LINE_AA)

    def _update_and_render_capture(self, canvas, frame, dt):
        """STATE_CAPTURE: Pose pemain, kepalkan tangan 1.5s -> Countdown 3..2..1 -> Jepret!"""
        # Tampilkan video kamera live
        cam_resized = cv2.resize(frame, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_LINEAR)
        canvas[:] = cam_resized

        # Bingkai Persegi Jepret di Tengah (450x450)
        bx, by = (CANVAS_WIDTH - 450) // 2, (CANVAS_HEIGHT - 450) // 2
        cv2.rectangle(canvas, (bx, by), (bx + 450, by + 450), COLOR_NEON_CYAN, 3)

        # Header Instruksi
        header_banner = f"STAGE {self.stage}: POSE DAN KEPALKAN TANGAN UNTUK JEPRET!"
        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 70), COLOR_PANEL_BG, -1)
        cv2.putText(canvas, header_banner, (220, 48), cv2.FONT_HERSHEY_TRIPLEX, 0.95, COLOR_NEON_GOLD, 2, cv2.LINE_AA)

        # Petunjuk Teks Bawah
        cv2.putText(canvas, "Kepalkan tangan selama 1.5 detik atau tekan [SPACE] / [C]", (330, CANVAS_HEIGHT - 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        # Logika Deteksi Pose Kepal
        if self.tracker.is_fist:
            self.capture_fist_timer += dt
            if self.capture_fist_timer >= HOLD_TIME_CAPTURE_FIST and self.capture_countdown < 0:
                self.capture_countdown = 3.0  # Mulai hitung mundur 3 detik
        else:
            if self.capture_countdown < 0:
                self.capture_fist_timer = max(0.0, self.capture_fist_timer - dt * 2.0)

        # Indikator Progres Kepal sebelum Countdown
        if self.capture_countdown < 0 and self.capture_fist_timer > 0.0:
            prog = min(1.0, self.capture_fist_timer / HOLD_TIME_CAPTURE_FIST)
            bar_w = int(450 * prog)
            cv2.rectangle(canvas, (bx, by + 455), (bx + bar_w, by + 465), COLOR_NEON_GOLD, -1)

        # Hitung Mundur 3.. 2.. 1.. Jepret!
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

        # Render Jendela PiP Mini
        self.ui.render_pip_camera(canvas, frame, self.tracker)

    def _trigger_photo_capture(self, frame):
        """Memotong foto persegi 450x450 dari tampilan layar, memicu flash putih (P2), dan mengacak puzzle."""
        # Resize frame kamera sesuai skala tampilan kanvas
        cam_resized = cv2.resize(frame, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_LINEAR)
        
        # Koordinat bingkai tengah (450x450) persis seperti yang dilihat pemain di layar
        bx = (CANVAS_WIDTH - BOARD_SIZE) // 2
        by = (CANVAS_HEIGHT - BOARD_SIZE) // 2
        photo_450 = cam_resized[by:by+BOARD_SIZE, bx:bx+BOARD_SIZE].copy()
        
        self.puzzle.set_captured_photo(photo_450)

        # Jumlah langkah acak sah (100% Solvable) sesuai stage:
        # Stage 1: 15 - 17 langkah
        # Stage 2: 19 - 22 langkah
        # Stage 3: 24 - 28 langkah
        if self.stage == 1:
            moves = random.randint(15, 17)
        elif self.stage == 2:
            moves = random.randint(19, 22)
        else:
            moves = random.randint(24, 28)

        self.puzzle.shuffle_legal_moves(moves)
        self.obstacles.reset_for_stage(self.stage)
        self.equipped_tool = TOOL_NONE
        self.stage_start_time = time.time()

        # Picu Efek Flash Putih (P2)
        self.flash_intensity = 1.0
        self.state = STATE_PLAYING

    def _update_and_render_playing(self, canvas, frame, dt):
        """STATE_PLAYING: Gameplay utama, puzzle, kontrol tangan, rintangan, dan deadlock."""
        # 1. Tentukan posisi grid papan yang sedang disorot kursor
        cx, cy = self.tracker.cursor_x, self.tracker.cursor_y
        current_hover_grid = -1

        if (BOARD_X <= cx < BOARD_X + BOARD_SIZE) and (BOARD_Y <= cy < BOARD_Y + BOARD_SIZE):
            col = (cx - BOARD_X) // TILE_SIZE
            row = (cy - BOARD_Y) // TILE_SIZE
            current_hover_grid = int(row * GRID_COLS + col)

        # 2. Tentukan slot alat yang sedang disorot kursor
        current_hover_tool = TOOL_NONE
        for t_id, t_info in self.ui.tool_slots.items():
            tx, ty, tw, th = t_info["rect"]
            if (tx <= cx < tx + tw) and (ty <= cy < ty + th):
                if t_id in self.obstacles.get_stage_settings()["active_tools"]:
                    current_hover_tool = t_id
                    break

        empty_grid_pos = self.puzzle.tiles.index(self.puzzle.empty_val)

        # 3. Update Rintangan & Idle Timer
        self.obstacles.update(dt, current_hover_grid, empty_grid_pos)

        # 4. Cek Kondisi Instant Deadlock
        if self.obstacles.check_deadlock(self.puzzle):
            self._trigger_deadlock()

        # 5. Interaksi Kursor: Mode Geser Puzzle vs Mode Alat
        action_progress = 0.0

        if not self.tracker.is_fist:
            # GESTURE 1 (TANGAN TERBUKA): MODE GESER PUZZLE
            if current_hover_grid != -1 and current_hover_grid != empty_grid_pos:
                can_move = self.puzzle.can_slide(current_hover_grid)
                is_locked = (current_hover_grid in self.obstacles.grid_obstacles)

                if can_move and not is_locked:
                    if current_hover_grid == self.hover_grid_pos:
                        self.hover_grid_timer += dt
                    else:
                        self.hover_grid_pos = current_hover_grid
                        self.hover_grid_timer = 0.0

                    action_progress = min(1.0, self.hover_grid_timer / HOLD_TIME_SLIDE)
                    # Jika ditahan selama 0.4 detik -> Kepingan bergeser!
                    if self.hover_grid_timer >= HOLD_TIME_SLIDE:
                        self.puzzle.slide_tile(current_hover_grid)
                        self.hover_grid_timer = 0.0
                        self.hover_grid_pos = -1

                        # Cek apakah puzzle terpecahkan setelah langkah ini!
                        if self.puzzle.is_solved():
                            self._complete_current_stage()
                            return
                else:
                    self.hover_grid_timer = 0.0
            else:
                self.hover_grid_timer = 0.0
                self.hover_grid_pos = -1

        else:
            # GESTURE 2 (TANGAN MENGEPAL): MODE AMBIL & GUNAKAN ALAT
            # A. Mengambil Alat dari Panel
            if current_hover_tool != TOOL_NONE:
                if current_hover_tool == self.hover_tool_id:
                    self.hover_tool_timer += dt
                else:
                    self.hover_tool_id = current_hover_tool
                    self.hover_tool_timer = 0.0

                action_progress = min(1.0, self.hover_tool_timer / HOLD_TIME_EQUIP)
                # Jika ditahan mengepal selama 0.5 detik -> Ambil alat!
                if self.hover_tool_timer >= HOLD_TIME_EQUIP:
                    self.equipped_tool = current_hover_tool
                    self.hover_tool_timer = 0.0
            else:
                self.hover_tool_timer = 0.0
                self.hover_tool_id = TOOL_NONE

            # B. Menggunakan Alat pada Kepingan Ber-rintangan
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
                    # Jika ditahan mengepal selama 0.8 detik -> Rintangan bersih!
                    if self.hover_grid_timer >= HOLD_TIME_CLEAR:
                        del self.obstacles.grid_obstacles[current_hover_grid]
                        self.hover_grid_timer = 0.0
                        self.hover_grid_pos = -1
                else:
                    self.hover_grid_timer = 0.0
            elif current_hover_tool == TOOL_NONE:
                self.hover_grid_timer = 0.0

        # 6. RENDER ELEMEN GRAFIS GAMEPLAY
        active_tools = self.obstacles.get_stage_settings()["active_tools"]
        elapsed_sec = time.time() - self.stage_start_time

        # Header HUD
        self.ui.render_hud(canvas, self.stage, self.score, self.lives, elapsed_sec)

        # Panel Peralatan Kiri dan Kanan
        tool_hover_prog = action_progress if current_hover_tool != TOOL_NONE else 0.0
        self.ui.render_tool_panels(canvas, active_tools, self.equipped_tool, current_hover_tool, tool_hover_prog)

        # Papan Puzzle & Bingkai Konsol
        tile_hover_prog = action_progress if current_hover_grid != -1 else 0.0
        self.ui.render_puzzle_board(canvas, self.puzzle, self.obstacles.grid_obstacles, current_hover_grid, tile_hover_prog)

        # Jendela PiP Mini Kamera & Masker
        self.ui.render_pip_camera(canvas, frame, self.tracker)

        # Kursor Interaktif & Ikon Mengambang (P4)
        self.ui.render_cursor(canvas, self.tracker, self.equipped_tool)

        # Efek Flash Putih Jepretan (P2)
        if self.flash_intensity > 0.0:
            canvas[:] = PCVEngine.apply_flash_effect(canvas, self.flash_intensity)
            self.flash_intensity = max(0.0, self.flash_intensity - dt * 3.5)

        # Efek Deadlock Layar Merah
        if self.deadlock_flash_timer > 0.0:
            self.deadlock_flash_timer -= dt
            red_overlay = np.zeros_like(canvas)
            red_overlay[:, :, 2] = 230  # Merah pekat
            canvas[:] = cv2.addWeighted(canvas, 0.65, red_overlay, 0.35, 0)

    def _trigger_deadlock(self):
        """
        Mengeksekusi Penalti Instant Deadlock:
        - Layar berkedip merah
        - Nyawa berkurang 1
        - Skor dikurangi 200 poin (minimal 0)
        - Seluruh rintangan dibersihkan
        - Posisi susunan papan TIDAK di-reset
        - Jika nyawa habis (0), masuk ke layar Game Over.
        """
        self.lives -= 1
        self.score = max(0, self.score - 200)
        self.deadlock_flash_timer = 0.5  # Flash merah selama 0.5 detik
        self.obstacles.clear_all()

        if self.lives <= 0:
            self.state = STATE_GAME_OVER

    def _complete_current_stage(self):
        """Menghitung skor dan bonus waktu saat stage berhasil diselesaikan."""
        elapsed = time.time() - self.stage_start_time

        # Poin dasar per stage
        base_points = {1: 300, 2: 600, 3: 900}.get(self.stage, 300)
        # Bonus waktu: max(0, (90 - detik_penyelesaian) * 10)
        time_bonus = max(0, int((90 - elapsed) * 10))

        self.score += (base_points + time_bonus)
        self.stage_clear_timer = 3.0  # Tampilkan foto utuh 3 detik
        self.state = STATE_STAGE_CLEAR

    def _update_and_render_stage_clear(self, canvas, dt):
        """STATE_STAGE_CLEAR: Menampilkan foto lengkap utuh selama 3 detik sebelum lanjut."""
        self.stage_clear_timer -= dt

        # Header Status
        cv2.rectangle(canvas, (0, 0), (CANVAS_WIDTH, 80), COLOR_PANEL_BG, -1)
        clear_title = f"STAGE {self.stage} SELESAI!"
        cv2.putText(canvas, clear_title, (480, 52), cv2.FONT_HERSHEY_TRIPLEX, 1.2, COLOR_NEON_GREEN, 2, cv2.LINE_AA)

        # Tampilkan Foto Lengkap Utuh di Tengah
        if self.puzzle.full_photo is not None:
            canvas[BOARD_Y:BOARD_Y+BOARD_SIZE, BOARD_X:BOARD_X+BOARD_SIZE] = self.puzzle.full_photo

        # Bingkai Papan
        cv2.rectangle(canvas, (BOARD_X - 4, BOARD_Y - 4), (BOARD_X + BOARD_SIZE + 4, BOARD_Y + BOARD_SIZE + 4), COLOR_NEON_GREEN, 3)

        # Rincian Skor
        cv2.putText(canvas, f"TOTAL SKOR: {self.score:05d}", (BOARD_X + 110, BOARD_Y + BOARD_SIZE + 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        # Countdown lanjut stage
        countdown_sec = max(1, int(math.ceil(self.stage_clear_timer)))
        cv2.putText(canvas, f"Melanjutkan dalam {countdown_sec} detik...", (BOARD_X + 100, BOARD_Y + BOARD_SIZE + 70), cv2.FONT_HERSHEY_PLAIN, 1.3, COLOR_NEON_GOLD, 1, cv2.LINE_AA)

        if self.stage_clear_timer <= 0:
            if self.stage < 3:
                self.stage += 1
                self.state = STATE_CAPTURE
                self.capture_fist_timer = 0.0
                self.capture_countdown = -1.0
            else:
                self.state = STATE_VICTORY

    def _update_and_render_end(self, canvas, dt):
        """STATE_END: Layar Game Over (Kuantisasi P1) atau Layar Victory (Setelah Stage 3)."""
        is_victory = (self.state == STATE_VICTORY)

        if is_victory:
            # LAYAR KEMENANGAN (VICTORY)
            title = "SELAMAT! ANDA MENANG (VICTORY)!"
            title_col = COLOR_NEON_GOLD

            # Tampilkan Foto Lengkap
            if self.puzzle.full_photo is not None:
                canvas[BOARD_Y:BOARD_Y+BOARD_SIZE, BOARD_X:BOARD_X+BOARD_SIZE] = self.puzzle.full_photo

            cv2.rectangle(canvas, (BOARD_X - 4, BOARD_Y - 4), (BOARD_X + BOARD_SIZE + 4, BOARD_Y + BOARD_SIZE + 4), COLOR_NEON_GOLD, 3)

            # Predikat Peringkat (Rank)
            if self.score >= 2600:
                rank = "RANK: S (MASTER VISION)"
            elif self.score >= 1800:
                rank = "RANK: A (EXPERT)"
            else:
                rank = "RANK: B (NOVICE)"
            cv2.putText(canvas, rank, (BOARD_X + 90, BOARD_Y + BOARD_SIZE + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.85, COLOR_NEON_CYAN, 1, cv2.LINE_AA)

        else:
            # LAYAR GAME OVER (P1 Low Bit-Depth Quantization)
            title = "GAME OVER - NYAWA HABIS"
            title_col = COLOR_NEON_RED

            if self.puzzle.full_photo is not None:
                # Kuantisasi citra 3-bit (8 level intensitas) untuk efek retro 8-bit hancur
                quantized_photo = PCVEngine.quantize_bit_depth(self.puzzle.full_photo, bits=3)
                canvas[BOARD_Y:BOARD_Y+BOARD_SIZE, BOARD_X:BOARD_X+BOARD_SIZE] = quantized_photo

            cv2.rectangle(canvas, (BOARD_X - 4, BOARD_Y - 4), (BOARD_X + BOARD_SIZE + 4, BOARD_Y + BOARD_SIZE + 4), COLOR_NEON_RED, 3)

        # Judul Layar
        (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_TRIPLEX, 1.2, 2)
        cv2.putText(canvas, title, ((CANVAS_WIDTH - tw) // 2, 110), cv2.FONT_HERSHEY_TRIPLEX, 1.2, title_col, 2, cv2.LINE_AA)

        # Skor Akhir
        score_text = f"SKOR AKHIR: {self.score:05d}"
        cv2.putText(canvas, score_text, (BOARD_X + 120, BOARD_Y + BOARD_SIZE + 75), cv2.FONT_HERSHEY_DUPLEX, 0.85, COLOR_TEXT_WHITE, 1, cv2.LINE_AA)

        # Petunjuk Mulai Ulang
        prompt_text = "Tekan [R] untuk Main Lagi atau [Q] untuk Keluar"
        cv2.putText(canvas, prompt_text, (BOARD_X + 20, BOARD_Y + BOARD_SIZE + 110), cv2.FONT_HERSHEY_DUPLEX, 0.7, COLOR_NEON_GOLD, 1, cv2.LINE_AA)


# ==================================================================================================
# TITIK MASUK PROGRAM (MAIN ENTRY POINT)
# ==================================================================================================
if __name__ == "__main__":
    print("================================================================")
    print("            MEMULAI PERMAINAN PUZZLE CAMS                       ")
    print("================================================================")
    print("Materi PCV Aktif: P1 (Spasial/Kuantisasi), P2 (Point/LUT/Gamma),")
    print("                 P3 (Sobel/Median/Blur/Unsharp), P4 (HSV/Blend),")
    print("                 P5 (Morfologi/CCStats/Gestur).                 ")
    print("Pintas Demo: [N] Instant Stage Clear | [D] Deadlock | [R] Restart")
    print("================================================================")

    game = PuzzleCamsGame()
    game.run()
