import cv2
import mediapipe as mp
from mediapipe.framework.formats import image_format_pb2
from mediapipe.tasks.python.vision.core import image_processing_options as image_processing_options_module
import numpy as np
import time 
import math

MODEL_PATH = "hand_landmarker.task"
VELOCITY_THRESHOLD = 0.12  # Higher threshold to avoid false triggers
GUARD_DISTANCE = 0.25
MIN_FOLDED_FINGERS = 3

# Hand landmark connections (MediaPipe standard)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),      # Index
    (0, 9), (9, 10), (10, 11), (11, 12), # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17), (5, 13),  # Palm
]

def ai_process(command_queue, stop_event):
    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    Image = mp.Image
    ImageProcessingOptions = image_processing_options_module.ImageProcessingOptions

    prev_cords = {}
    current_landmarks = None

    def draw_landmarks(frame, hand_landmarks_list, h, w):
        """Vẽ các landmark (điểm) tay lên frame"""
        if not hand_landmarks_list:
            return frame
        
        frame_copy = frame.copy()
        
        for hand_idx, hand_landmarks in enumerate(hand_landmarks_list):
            # Vẽ các điểm (landmarks)
            for lm_idx, landmark in enumerate(hand_landmarks):
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                # Vẽ điểm tay: đỏ nếu là đầu ngón, xanh nếu là khớp
                color = (0, 0, 255) if lm_idx in [4, 8, 12, 16, 20] else (0, 255, 0)
                cv2.circle(frame_copy, (x, y), 5, color, -1)
        
        return frame_copy

    def result_callback(result, output_image, timestamp_ms):
        nonlocal current_landmarks
        try:
            if stop_event.is_set():
                return
            
            # Store landmarks để vẽ
            current_landmarks = result.hand_landmarks
            
            print(f"[DEBUG] Callback triggered. Hands detected: {len(result.hand_landmarks) if result.hand_landmarks else 0}")
            
            command = []
            left_hand_wrist = None
            right_hand_wrist = None

            if result.hand_landmarks:
                print(f"[DEBUG] Processing {len(result.hand_landmarks)} hand(s)")
                for i, hand_landmarks in enumerate(result.hand_landmarks):
                    try:
                        print(f"[DEBUG] Hand {i}: Processing landmarks (total: {len(hand_landmarks)})")
                        
                        handedness = 'Unknown'
                        if result.handedness and len(result.handedness) > i:
                            # result.handedness[i] is a list of categories
                            handedness_list = result.handedness[i]
                            if handedness_list and len(handedness_list) > 0:
                                handedness = handedness_list[0].category_name
                                handedness = "Right" if handedness == "Right" else "Left"
                                print(f"[DEBUG] Hand {i}: Raw handedness={handedness_list[0].category_name}, Normalized={handedness}")
                        
                        wrist = hand_landmarks[0]  # First landmark is the wrist
                        print(f"[DEBUG] Hand {i}: Handedness={handedness}, Wrist=({wrist.x:.2f}, {wrist.y:.2f})")

                        if handedness == "Left": left_hand_wrist = wrist
                        if handedness == "Right": right_hand_wrist = wrist

                        prev = prev_cords.get(handedness, (wrist.x, wrist.y))
                        velocity = math.sqrt((wrist.x - prev[0])**2 + (wrist.y - prev[1])**2)
                        prev_cords[handedness] = (wrist.x, wrist.y)
                        print(f"[DEBUG] Hand {i}: Velocity={velocity:.3f}")

                        tips = [8, 12, 16, 20]
                        mcps = [5, 9, 13, 17]
                        folded = 0
                        for t, m in zip(tips, mcps):
                            dist_t = math.hypot(
                                hand_landmarks[t].x - wrist.x, hand_landmarks[t].y - wrist.y)
                            dist_m = math.hypot(
                                hand_landmarks[m].x - wrist.x, hand_landmarks[m].y - wrist.y)
                            if dist_t < dist_m:
                                folded += 1
                        is_fist = folded >= MIN_FOLDED_FINGERS
                        print(f"[DEBUG] Hand {i}: Folded fingers={folded}, Is fist={is_fist}, Velocity={velocity:.3f} (threshold={VELOCITY_THRESHOLD})")

                        if is_fist and velocity > VELOCITY_THRESHOLD:
                            # Detect punch direction based on wrist movement
                            prev_x, prev_y = prev_cords.get(handedness, (wrist.x, wrist.y))
                            dx = wrist.x - prev_x
                            dy = wrist.y - prev_y
                            
                            # Straight punch: small lateral movement
                            if 0.35 < wrist.x < 0.7:
                                command.append("PUNCH_S")
                                print(f"[DEBUG] Detected PUNCH_S from hand {i}, velocity={velocity:.3f}")
                            # Hook punch: large horizontal movement
                            elif abs(dx) > abs(dy) * 1.5:
                                # Right hand moving right or Left hand moving left
                                if (handedness == "Right" and dx > 0) or (handedness == "Left" and dx < 0):
                                    cmd = "PUNCH_R" if handedness == "Right" else "PUNCH_L"
                                # Otherwise opposite side
                                else:
                                    cmd = "PUNCH_L" if handedness == "Right" else "PUNCH_R"
                                command.append(cmd)
                                print(f"[DEBUG] Detected {cmd} (hook) from hand {i}, velocity={velocity:.3f}, dx={dx:.3f}")
                            # Default: normal punch
                            else:
                                cmd = "PUNCH_R" if handedness == "Right" else "PUNCH_L"
                                command.append(cmd)
                                print(f"[DEBUG] Detected {cmd} from hand {i}, velocity={velocity:.3f}")
                    except Exception as e:
                        print(f"[ERROR] Processing hand {i}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue

                # Guard logic
                if left_hand_wrist and right_hand_wrist:
                    dist = math.hypot(
                        left_hand_wrist.x - right_hand_wrist.x,
                        left_hand_wrist.y - right_hand_wrist.y)
                    if dist < GUARD_DISTANCE:
                        command.append("DEFEND_ON")
                        print(f"[DEBUG] Guard detected: distance={dist:.3f}")
                    else:
                        command.append("DEFEND_OFF")
                else:
                    command.append("DEFEND_OFF")

                # Send command to queue
                try:
                    if not command_queue.full():
                        final_cmd = None
                        if "PUNCH_S" in command:
                            final_cmd = "PUNCH_S"
                        elif "PUNCH_L" in command:
                            final_cmd = "PUNCH_L"
                        elif "PUNCH_R" in command:
                            final_cmd = "PUNCH_R"
                        elif "DEFEND_ON" in command:
                            final_cmd = "DEFEND_ON"
                        else:
                            final_cmd = "DEFEND_OFF"
                        
                        if final_cmd:
                            try:
                                command_queue.put_nowait(final_cmd)
                                print(f"[DEBUG] Sent command: {final_cmd}")
                            except Exception as q_err:
                                print(f"[ERROR] Queue error: {q_err}")
                except Exception as cmd_err:
                    print(f"[ERROR] Command processing: {cmd_err}")
        except Exception as e:
            print(f"[ERROR] Callback error: {e}")
            import traceback
            traceback.print_exc()

    # Create the HandLandmarker and start the camera loop (outside the callback)
    try:
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=result_callback,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        landmarker = HandLandmarker.create_from_options(options)
    except Exception as e:
        print(f"Failed to create HandLandmarker: {e}")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("AI Controller started.")

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp_ms = int(time.time() * 1000)
            
            # Create MediaPipe Image object with proper format
            mp_image = Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Provide image dimensions to avoid landmark projection warning
            image_processing_options = ImageProcessingOptions(
                region_of_interest=None
            )
            landmarker.detect_async(mp_image, timestamp_ms, image_processing_options)
            
            # Chỉ hiển thị camera feed, không vẽ landmarks (để tránh delay)
            cv2.imshow('AI Controller', cv2.flip(frame, 1))
            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                stop_event.set()
                break
    except Exception as e:
        print(f"Camera loop error: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
                