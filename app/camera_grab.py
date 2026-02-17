"""
Camera-based file grabbing using gesture recognition.
Point camera at files displayed on screen and gesture to grab them.
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import os


class CameraGrab:
    def __init__(self):
        self.config_dir = Path.home() / '.myshare'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.grab_file = self.config_dir / 'grabbed_file.json'
        self.watched_dirs = [
            Path.home() / 'Downloads',
            Path.home() / 'Desktop',
            Path.home() / 'Pictures',
        ]

    def list_available_files(self, limit=8):
        """Get list of files from common directories."""
        files = []
        for directory in self.watched_dirs:
            if directory.exists():
                try:
                    dir_files = sorted(
                        [f for f in directory.glob('*') if f.is_file()],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )[:limit]
                    files.extend(dir_files)
                except Exception:
                    pass
        
        # Remove duplicates and limit
        seen = set()
        unique_files = []
        for f in files:
            if f.absolute() not in seen:
                seen.add(f.absolute())
                unique_files.append(f)
        
        return unique_files[:limit]

    def detect_hand_position(self, frame, mask):
        """Detect hand position in frame."""
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, None
        
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Return hand center position
        hand_x = x + w // 2
        hand_y = y + h // 2
        
        return hand_x, hand_y

    def start_camera_grab(self):
        """
        Open camera and show files on screen.
        User points hand at a file and moves hand UP to grab it.
        """
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return None, "Cannot access camera"
        
        available_files = self.list_available_files()
        selected_index = 0
        grab_confirmed = False
        hand_y_history = []
        
        print("\n" + "="*60)
        print("📹 CAMERA GRAB MODE")
        print("="*60)
        print("✊ Point your hand at a file to select")
        print("👆 Move hand UP to GRAB the file")
        print("❌ Press 'q' to QUIT")
        print("="*60 + "\n")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Flip frame for selfie view
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            # Detect hand/skin tone
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_skin = np.array([0, 20, 70])
            upper_skin = np.array([20, 255, 255])
            mask = cv2.inRange(hsv, lower_skin, upper_skin)
            
            # Detect hand position
            hand_x, hand_y = self.detect_hand_position(frame, mask)
            
            # Update selection based on hand position
            if hand_x is not None:
                # Map hand position to file selection
                file_y_start = 100
                file_height = 50
                
                for i in range(len(available_files)):
                    file_y = file_y_start + i * file_height
                    if hand_y > file_y - 25 and hand_y < file_y + 25:
                        selected_index = i
                        break
                
                # Track upward motion for grab
                hand_y_history.append(hand_y)
                if len(hand_y_history) > 5:
                    hand_y_history.pop(0)
                
                # Detect upward motion (grab gesture)
                if len(hand_y_history) >= 5:
                    motion = hand_y_history[0] - hand_y_history[-1]  # Positive = upward
                    if motion > 50:  # Significant upward motion
                        grab_confirmed = True
            
            # Display title
            cv2.putText(frame, "GRAB A FILE (point hand at file, move UP to grab)", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display available files with selection indicator
            file_y_start = 100
            for i, file in enumerate(available_files):
                file_y = file_y_start + i * 50
                
                if i == selected_index:
                    # Highlight selected file
                    cv2.rectangle(frame, (10, file_y - 25), (w - 10, file_y + 25), (0, 255, 0), 2)
                    color = (0, 255, 0)
                    prefix = "👉 "
                else:
                    color = (150, 150, 150)
                    prefix = "   "
                
                # Show file name and path
                display_name = file.name
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."
                
                cv2.putText(frame, f"{prefix}{display_name}", (20, file_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
            
            # Show instructions
            cv2.putText(frame, "Press 'q' to quit", (10, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow('📷 Camera Grab', frame)
            
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                cap.release()
                cv2.destroyAllWindows()
                return None, "Cancelled by user"
            
            # Check if user grabbed a file
            if grab_confirmed and selected_index < len(available_files):
                selected_file = available_files[selected_index]
                cap.release()
                cv2.destroyAllWindows()
                return str(selected_file.absolute()), None
        
        cap.release()
        cv2.destroyAllWindows()
        return None, "Camera error"

    def grab_by_path(self, file_path):
        """Store grabbed file path (traditional method)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        state = {
            'file_path': str(path.absolute()),
            'file_name': path.name,
            'grabbed_at': datetime.now().isoformat(),
            'method': 'path'
        }
        
        with open(self.grab_file, 'w') as f:
            json.dump(state, f)

    def grab_by_camera(self):
        """Grab file using camera gesture."""
        file_path, error = self.start_camera_grab()
        
        if error:
            raise Exception(error)
        
        if file_path:
            state = {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'grabbed_at': datetime.now().isoformat(),
                'method': 'camera'
            }
            
            with open(self.grab_file, 'w') as f:
                json.dump(state, f)
            
            return file_path

    def get_grabbed(self):
        """Get currently grabbed file path."""
        if not self.grab_file.exists():
            return None
        
        try:
            with open(self.grab_file, 'r') as f:
                state = json.load(f)
            
            file_path = state.get('file_path')
            if file_path and Path(file_path).exists():
                return file_path
            else:
                self.release()
                return None
        except Exception:
            return None
    
    def release(self):
        """Clear grabbed file."""
        if self.grab_file.exists():
            self.grab_file.unlink()
    
    def show_grabbed(self):
        """Display currently grabbed file."""
        grabbed = self.get_grabbed()
        if grabbed:
            return f"📎 Grabbed: {Path(grabbed).name}\n   Path: {grabbed}"
        else:
            return "No file grabbed yet"

