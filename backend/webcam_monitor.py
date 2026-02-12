"""
Local webcam monitor for a student machine.

What it does:
1. Captures frames from webcam.
2. Detects face absence / multiple faces (OpenCV Haar Cascade).
3. Optionally detects phone (if ultralytics YOLO is installed).
4. Sends violations to backend /notify.

Run:
    python backend/webcam_monitor.py --student-id student_01
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict
from urllib import parse, request


def send_violation(server_url: str, student_id: str, violation_type: str, violation_data: str) -> None:
    payload = parse.urlencode(
        {
            "student_id": student_id,
            "violation_type": violation_type,
            "violation_data": violation_data,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    ).encode("utf-8")

    req = request.Request(
        url=f"{server_url.rstrip('/')}/notify",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(req, timeout=5) as resp:
        resp.read()


def build_phone_detector():
    """
    Returns YOLO model if available, otherwise None.
    COCO class id for cell phone is 67.
    """
    try:
        from ultralytics import YOLO

        return YOLO("yolov8n.pt")
    except Exception:
        return None


def phone_present(model, frame) -> bool:
    if model is None:
        return False

    try:
        results = model.predict(source=frame, verbose=False, conf=0.4)
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            cls_values = boxes.cls.tolist() if boxes.cls is not None else []
            for class_id in cls_values:
                if int(class_id) == 67:
                    return True
    except Exception:
        return False

    return False


def open_camera(cv2, requested_index: int, search_max: int):
    candidates = [requested_index] if requested_index >= 0 else []
    candidates.extend(i for i in range(search_max + 1) if i not in candidates)

    for idx in candidates:
        if sys.platform.startswith("win"):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(idx)
        else:
            cap = cv2.VideoCapture(idx)

        if cap.isOpened():
            return cap, idx
        cap.release()

    return None, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Webcam monitor client")
    parser.add_argument("--student-id", required=True, help="Unique student id")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000", help="Backend URL")
    parser.add_argument("--camera-index", type=int, default=-1, help="Webcam index (-1 = auto)")
    parser.add_argument("--camera-search-max", type=int, default=5, help="Max camera index for auto-search")
    parser.add_argument(
        "--fail-on-no-camera",
        action="store_true",
        help="Exit with code 1 if camera is not found (default: keep process alive).",
    )
    parser.add_argument("--cooldown", type=float, default=8.0, help="Seconds between same alerts")
    parser.add_argument(
        "--enable-phone-detection",
        action="store_true",
        help="Enable YOLO phone detection (requires ultralytics)",
    )
    args = parser.parse_args()

    try:
        import cv2
    except Exception:
        print("ERROR: OpenCV is not installed. Install with: pip install opencv-python")
        return 1

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    if face_cascade.empty():
        print("ERROR: Could not load Haar Cascade for face detection.")
        return 1

    yolo_model = build_phone_detector() if args.enable_phone_detection else None
    if args.enable_phone_detection and yolo_model is None:
        print("Phone detection disabled: install ultralytics (`pip install ultralytics`) to enable.")

    cap, active_camera_index = open_camera(cv2, args.camera_index, args.camera_search_max)
    if cap is None:
        message = (
            f"Could not open webcam. Tried indices 0..{args.camera_search_max} "
            f"(requested={args.camera_index})."
        )
        if args.fail_on_no_camera:
            print(f"ERROR: {message}")
            return 1

        print(f"WARN: {message}")
        print("WARN: Running in no-camera mode. Violation detection from webcam is disabled.")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        return 0

    print("Webcam monitor started.")
    print(
        json.dumps(
            {
                "student_id": args.student_id,
                "server_url": args.server_url,
                "camera_index": active_camera_index,
                "phone_detection": bool(yolo_model),
                "cooldown_seconds": args.cooldown,
            },
            ensure_ascii=True,
        )
    )
    print("Press 'q' in preview window to stop.")

    last_sent: Dict[str, float] = {}

    def should_send(v_type: str) -> bool:
        now = time.time()
        prev = last_sent.get(v_type, 0.0)
        if now - prev >= args.cooldown:
            last_sent[v_type] = now
            return True
        return False

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.2)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
            face_count = len(faces)

            if face_count == 0 and should_send("face_not_found"):
                try:
                    send_violation(args.server_url, args.student_id, "face_not_found", "No face detected")
                    print("ALERT sent: face_not_found")
                except Exception as exc:
                    print(f"WARN: Failed to send face_not_found: {exc}")

            if face_count > 1 and should_send("multiple_faces"):
                try:
                    send_violation(
                        args.server_url,
                        args.student_id,
                        "multiple_faces",
                        f"{face_count} faces detected",
                    )
                    print("ALERT sent: multiple_faces")
                except Exception as exc:
                    print(f"WARN: Failed to send multiple_faces: {exc}")

            if yolo_model is not None and phone_present(yolo_model, frame) and should_send("phone_detected"):
                try:
                    send_violation(args.server_url, args.student_id, "phone_detected", "Phone-like object detected")
                    print("ALERT sent: phone_detected")
                except Exception as exc:
                    print(f"WARN: Failed to send phone_detected: {exc}")

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 0), 2)

            cv2.putText(
                frame,
                f"faces: {face_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )
            cv2.imshow("Student Webcam Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
