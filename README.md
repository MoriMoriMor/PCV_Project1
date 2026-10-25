# PUZZLE CAMS - Webcam Arcade Puzzle Game
**Game Komputer Berbasis Pengolahan Citra dan Visi (PCV)**

Game puzzle geser (sliding puzzle) 3x3 interaktif yang dikendalikan secara real-time menggunakan kamera webcam dan gestur tangan pemain. Mengimplementasikan konsep nyata materi kuliah Pengolahan Citra dan Visi (P1 sampai P5) untuk gameplay, efek visual rintangan, dan deteksi gestur.

---

## 🚀 Cara Menjalankan Game

Pastikan Python dan library OpenCV serta NumPy sudah terinstal di komputer Anda:
```bash
pip install opencv-python numpy
```

Jalankan game menggunakan terminal/command prompt:
```bash
python puzzle_cams.py
```
*(Atau gunakan python path yang sesuai jika memiliki beberapa instalasi Python)*

---

## 🎮 Kontrol & Interaksi Tangan (1 Tangan)

Game ini melacak satu tangan pemain di depan webcam secara real-time:

| Gestur | Kondisi Area | Fungsi Utama |
| :--- | :--- | :--- |
| **Tangan Terbuka** | Area $\ge$ 65% area referensi ($A_{ref}$) | **Mode Geser Puzzle**: Tahan kursor 0.4 detik pada kepingan di samping kotak kosong untuk menggesernya. Mengarahkan kursor ke atas kepingan juga mereset idle timer semak. |
| **Tangan Mengepal** | Area $<$ 65% area referensi ($A_{ref}$) | **Mode Ambil / Pakai Alat**: Tahan mengepal 0.5 detik di panel alat untuk mengambil alat. Tahan mengepal 0.8 detik di atas kepingan yang terkunci rintangan untuk membersihkannya dengan alat yang cocok. |
| **Auto-Drop** | Buka tangan $\ge$ 0.3 detik | Alat yang sedang dipegang otomatis terlepas kembali ke mode geser puzzle. |

> **Mode Hybrid (Mouse Fallback):** Tekan tombol **`[M]`** pada keyboard untuk mengaktifkan kendali mouse (gerak kursor via mouse, klik kiri tahan untuk gestur mengepal). Berguna untuk evaluasi atau jika ruangan minim cahaya.

---

## 🧠 Penerapan Materi Pengolahan Citra & Visi (PCV)

| Materi | Implementasi Nyata pada Game |
| :--- | :--- |
| **[P1] Dasar Citra Digital & Operasi Spasial** | • **Horizontal Flip (Mirroring):** `cv2.flip(frame, 1)` agar gerakan tangan selaras secara intuitif.<br>• **Cropping Grid:** Pemotongan foto persegi 450x450 dan pembagian matriks grid 3x3 (9 kepingan 150x150).<br>• **Kuantisasi Bit-Depth:** Reduksi 8-bit menjadi 3-bit (8 level warna) untuk efek grafis retro pada layar Game Over. |
| **[P2] Operasi Titik & Transformasi Kontras** | • **White Flash Blending:** Efek kilatan blitz kamera saat jepret foto (`cv2.addWeighted`).<br>• **Look-Up Table (LUT) Negatif:** Efek transformasi warna rintangan *Es Beku* (`cv2.LUT`).<br>• **Transformasi Gamma 4.0:** Transformasi non-linear daya untuk menggelapkan rintangan *Kutukan Gelap*.<br>• **Transformasi Gamma 0.45:** Transformasi daya pembalik kontras untuk efek alat *Senter*. |
| **[P3] Filter Spasial & Frekuensi** | • **Filter Sobel:** Deteksi magnitudo gradien tepi ($G_x, G_y$) untuk rintangan *Semak*.<br>• **Median Filter:** Filter non-linear penghalus kristal es rintangan *Es Beku* (`cv2.medianBlur`).<br>• **Gaussian Blur 15x15:** Filter low-pass penghasil rintangan *Kabut Tebal* (`cv2.GaussianBlur`).<br>• **Unsharp Masking:** Filter high-pass sharpening untuk alat *Spons* pembersih kabut. |
| **[P4] Segmentasi Warna & Blending** | • **HSV Color Masking:** Segmentasi adaptif ruang warna HSV berdasarkan sampel kalibrasi (`cv2.inRange`).<br>• **Alpha Blending Multi-Channel:** Penempelan ikon alat mengambang pada kursor dan pewarnaan rintangan. |
| **[P5] Morfologi Citra & Analisis Bentuk** | • **Morfologi Opening & Closing:** Menghilangkan salt-noise dan menutup celah kontur tangan.<br>• **Connected Components:** `cv2.connectedComponentsWithStats` untuk menghitung centroid kursor dan luas area piksel.<br>• **Dilasi:** Menumbuhkan ketebalan sulur rintangan *Semak*.<br>• **Erosi:** Menerapkan efek pemotongan oleh alat *Pisau*.<br>• **Analisis Area Relatif:** Rasio luas area ($< 65\%$ vs $\ge 65\%$) untuk mendeteksi gestur mengepal vs terbuka. |

---

## ⚔️ Rintangan (Obstacles) & Alat Pembebas (Tools)

| Rintangan | Visual PCV | Alat Pembebas | Efek Alat |
| :--- | :--- | :--- | :--- |
| **Semak Belukar** | Filter Sobel (P3) + Dilasi (P5) + Tint Hijau (P4) | **Pisau** (Slot 1) | Erosi Morfologi (P5) |
| **Es Beku** | LUT Negatif (P2) + Median Filter (P3) + Tint Biru | **Hairdryer** (Slot 2) | Pelelehan Termal (P2/P4) |
| **Kutukan Gelap** | Transformasi Gamma 4.0 (P2) + Vignette Ungu | **Senter** (Slot 3) | Peningkatan Gamma 0.45 (P2) |
| **Kabut Tebal** | Gaussian Blur 15x15 (P3) + Overlay Putih Susu | **Spons** (Slot 4) | Unsharp Masking (P3) |

---

## 🏆 Alur Stage & Pengacakan 100% Solvable

Papan puzzle 3x3 diacak menggunakan metode **Random Legal Moves** (hanya melakukan langkah geser sah berturut-turut dari kondisi terpecahkan), sehingga dijamin **100% solvable**:
- **Stage 1:** 15 – 17 langkah acak. Rintangan: Hanya Semak. Alat aktif: Pisau.
- **Stage 2:** 19 – 22 langkah acak. Rintangan: Semak & Es Beku. Alat aktif: Pisau & Hairdryer.
- **Stage 3:** 24 – 28 langkah acak. Rintangan: Semua 4 rintangan aktif. Seluruh 4 alat aktif.

### Sistem Poin & Deadlock
- **Poin Selesai Stage:** Stage 1 (+300), Stage 2 (+600), Stage 3 (+900).
- **Bonus Kecepatan Waktu:** $\max(0, (90 - \text{detik}) \times 10)$.
- **Instant Deadlock:** Terjadi jika seluruh tetangga di sekeliling Kotak Kosong terkunci rintangan, ATAU $\ge 6$ kepingan tertutup rintangan secara bersamaan.
  - Layar berkedip merah.
  - Nyawa berkurang 1.
  - Penalti skor: -200 poin (minimal 0).
  - Seluruh rintangan di papan langsung bersih, tetapi **posisi susunan puzzle TIDAK di-reset** (pemain lanjut dari posisi terakhir).

---

## 🎨 Kustomisasi Aset Gambar (Folder `assets/`)

Program ini telah dilengkapi **Asset Generator otomatis**. Jika folder `assets/` kosong atau belum ada, program otomatis menggambar representasi grafis prosedural berkualitas tinggi berformat PNG 4-channel (BGRA).

Untuk mengganti ikon dengan gambar buatan sendiri atau dari web:
1. Siapkan file gambar PNG dengan latar transparan.
2. Simpan di folder `assets/` dengan nama file berikut:
   - `knife.png` (Ukuran disarankan: 128x128)
   - `hairdryer.png` (Ukuran disarankan: 128x128)
   - `flashlight.png` (Ukuran disarankan: 128x128)
   - `sponge.png` (Ukuran disarankan: 128x128)
   - `hand_open.png` (Ukuran disarankan: 128x128)
   - `hand_fist.png` (Ukuran disarankan: 128x128)
   - `heart.png` (Ukuran disarankan: 128x128)
   - `frame.png` (Ukuran disarankan: 490x490)

---

## ⌨️ Tombol Pintas Demo & Pengujian

- **`[SPACE]`** : Kalibrasi di layar HOME / Jepret foto di layar CAPTURE.
- **`[N]`** : **Instant Stage Clear** (Lompat langsung ke stage berikutnya untuk kebutuhan demonstrasi/penilaian penguji).
- **`[D]`** : **Paksa Deadlock** (Menguji penalti nyawa, pengurangan poin, dan flash layar merah).
- **`[R]`** : **Restart Permainan** kembali ke layar awal (Stage 1).
- **`[1..4]`**: Pintas cepat memilih Tool (1: Pisau, 2: Hairdryer, 3: Senter, 4: Spons).
- **`[0]`** : Lepas tool yang sedang dipegang.
- **`[M]`** : Toggle mode kontrol Mouse / Kamera.
- **`[Q]` / `[ESC]`** : Keluar dari permainan.
