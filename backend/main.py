"""
UPDATED SERVER CODE - Replace your existing server with this
Properly handles violation notifications from monitoring client
"""

from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
import json

app = FastAPI()

# ======================
# STATIC FILES (for screenshots)
# ======================
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# ======================
# HTTP: upload (архив)
# ======================
BASE_DIR = "storage/screenshots"
os.makedirs(BASE_DIR, exist_ok=True)

@app.post("/upload")
async def upload_screenshot(
    file: UploadFile,
    student_id: str = Form(...)
):
    student_dir = os.path.join(BASE_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(student_dir, f"{timestamp}.jpg")

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    return JSONResponse({"status": "ok"})


# ======================
# HTTP: List screenshots
# ======================
@app.get("/api/screenshots/list")
async def list_screenshots():
    """
    List all screenshots organized by student
    """
    students = {}
    
    if os.path.exists(BASE_DIR):
        for student_folder in os.listdir(BASE_DIR):
            student_path = os.path.join(BASE_DIR, student_folder)
            if os.path.isdir(student_path):
                screenshots = sorted([
                    f for f in os.listdir(student_path)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                ])
                if screenshots:
                    students[student_folder] = screenshots
    
    return JSONResponse({"students": students})


# ======================
# WebSocket: LIVE
# ======================

active_students = {}     # student_id -> ws
last_frames = {}         # student_id -> image(base64)
teachers = set()         # Set of teacher websockets
active_violations = []   # Track violations

@app.websocket("/ws/student")
async def student_ws(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()
    student_id = data["student_id"]

    active_students[student_id] = ws
    print(f"🟢 {student_id} online")

    try:
        while True:
            msg = await ws.receive_json()

            if msg["type"] == "screen":
                last_frames[student_id] = msg["image"]

                for t in list(teachers):
                    await t.send_json({
                        "type": "screen",
                        "student_id": student_id,
                        "image": msg["image"]
                    })

    except WebSocketDisconnect:
        active_students.pop(student_id, None)
        print(f"🔴 {student_id} offline")



@app.websocket("/ws/teacher")
async def teacher_ws(ws: WebSocket):
    await ws.accept()
    teachers.add(ws)
    print(f"👨‍🏫 Teacher connected. Total teachers: {len(teachers)}")

    try:
        while True:
            msg = await ws.receive_json()

            if msg["type"] == "subscribe":
                student_id = msg["student_id"]
                if student_id in last_frames:
                    await ws.send_json({
                        "type": "screen",
                        "student_id": student_id,
                        "image": last_frames[student_id]
                    })
    except WebSocketDisconnect:
        teachers.discard(ws)
        print(f"👨‍🏫 Teacher disconnected. Total teachers: {len(teachers)}")


# ======================
# NEW: Violation Notification
# ======================
@app.post("/notify")
async def notify_violation(
    student_id: str = Form(...),
    violation_type: str = Form(...),
    violation_data: str = Form(...),
    timestamp: str = Form(...)
):
    """
    Receive violation notifications from student monitoring client
    and broadcast to all connected teachers
    """
    
    violation_msg = {
        "type": "violation_alert",
        "student_id": student_id,
        "violation_type": violation_type,
        "violation_data": violation_data,
        "timestamp": timestamp
    }
    
    # Log the violation
    print(f"🚨 VIOLATION DETECTED!")
    print(f"   Student: {student_id}")
    print(f"   Type: {violation_type}")
    print(f"   Data: {violation_data}")
    print(f"   Time: {timestamp}")
    
    # Store violation
    active_violations.append(violation_msg)
    
    # Broadcast to all connected teachers
    if teachers:
        print(f"📢 Broadcasting to {len(teachers)} teacher(s)...")
        for teacher_ws in list(teachers):
            try:
                await teacher_ws.send_json(violation_msg)
                print(f"   ✅ Sent to teacher")
            except Exception as e:
                print(f"   ❌ Failed to send to teacher: {e}")
    else:
        print(f"⚠️  No teachers connected to receive notification")
    
    return JSONResponse({
        "status": "ok",
        "teachers_notified": len(teachers)
    })


@app.get("/violations")
async def get_violations():
    """
    Get all recorded violations
    """
    return JSONResponse({"violations": active_violations})


@app.get("/violations/{student_id}")
async def get_student_violations(student_id: str):
    """
    Get violations for specific student
    """
    student_violations = [v for v in active_violations if v["student_id"] == student_id]
    return JSONResponse({"violations": student_violations})
