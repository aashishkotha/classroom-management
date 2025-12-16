import cv2
import sys

print("Testing camera access...")
print(f"OpenCV version: {cv2.__version__}")

# Try to open camera
for index in [0, 1, 2]:
    print(f"\nTrying camera index {index}...")
    cap = cv2.VideoCapture(index)
    
    if cap.isOpened():
        print(f"✓ Camera {index} opened successfully!")
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            print(f"✓ Successfully read frame: {frame.shape}")
        else:
            print(f"✗ Failed to read frame from camera {index}")
        
        cap.release()
        sys.exit(0)
    else:
        print(f"✗ Failed to open camera {index}")
        cap.release()

print("\n✗ No working camera found!")
print("\nPossible solutions:")
print("1. Check if webcam is connected")
print("2. Check if another application is using the camera")
print("3. Check camera permissions in Windows settings")
print("4. Try running as administrator")
