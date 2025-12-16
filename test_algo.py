import cv2
try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    print("SUCCESS: LBPH initialized")
except AttributeError:
    print("ERROR: cv2.face not found")
except Exception as e:
    print(f"ERROR: {e}")
