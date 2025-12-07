import cv2

def test_camera():
    print("Testing camera access...")
    
    # Try different camera indices
    for index in [0, 1, 2]:
        print(f"\nTrying camera index {index}...")
        cap = cv2.VideoCapture(index)
        
        if cap.isOpened():
            print(f"Camera {index} opened successfully!")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"Successfully captured frame from camera {index}")
                print(f"Frame dimensions: {frame.shape}")
                
                # Show the camera feed for 3 seconds
                print("Showing camera feed for 3 seconds...")
                for i in range(3):
                    ret, frame = cap.read()
                    if ret:
                        cv2.imshow(f'Camera {index}', frame)
                        cv2.waitKey(1000)
                    else:
                        print(f"Failed to read frame {i}")
                
                cv2.destroyAllWindows()
                cap.release()
                return True
            else:
                print(f"Failed to read frame from camera {index}")
                cap.release()
        else:
            print(f"Failed to open camera {index}")
    
    print("\nNo working camera found!")
    print("Possible solutions:")
    print("1. Make sure your webcam is connected")
    print("2. Check if another app is using the camera")
    print("3. Try running as administrator")
    print("4. Check camera permissions in Windows settings")
    return False

if __name__ == "__main__":
    test_camera()
