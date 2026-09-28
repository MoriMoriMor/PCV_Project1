# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 01:24:50 2026

@author: yoga
"""

import cv2
import numpy as np

def main():
    cap = cv2.VideoCapture(0)
    
    print("Memulai...")
    print("Tekan 'Q' untuk keluar.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Gagal menangkap frame dari kamera.")
            break

        frame = cv2.flip(frame, 1)
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        lower_color = np.array([90, 50, 50])
        upper_color = np.array([130, 255, 255])
        
        mask = cv2.inRange(hsv, lower_color, upper_color)
        
        cv2.putText(frame, "Status: Menunggu...", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Hand Color Tracking", frame)
        cv2.imshow("Mask Warna Tangan", mask)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()