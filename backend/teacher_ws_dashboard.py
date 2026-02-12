"""
Teacher Dashboard - Real-time violation alerts via WebSocket
Run this on teacher's side to receive live notifications
"""

import asyncio
import websockets
import json
from datetime import datetime

TEACHER_WS_URL = "ws://127.0.0.1:8000/ws/teacher"

async def connect_and_listen():
    """Connect to teacher WebSocket and listen for violations"""
    
    print("👨‍🏫 Teacher Dashboard - Connecting...")
    
    try:
        async with websockets.connect(TEACHER_WS_URL) as websocket:
            print("✅ Connected to server!")
            print("🎧 Listening for violation alerts...\n")
            print("="*70)
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data.get("type") == "violation_alert":
                        # Display violation alert
                        student_id = data.get("student_id", "Unknown")
                        violation_type = data.get("violation_type", "").upper()
                        violation_data = data.get("violation_data", "Unknown")
                        timestamp = data.get("timestamp", "")
                        
                        print(f"\n🚨🚨🚨 VIOLATION ALERT 🚨🚨🚨")
                        print(f"  ⏰ Time:     {timestamp}")
                        print(f"  👤 Student:  {student_id}")
                        print(f"  🚫 Type:     {violation_type}")
                        print(f"  📍 Details:  {violation_data}")
                        print("="*70)
                    
                    elif data.get("type") == "screen":
                        # Handle screen updates (if implemented)
                        print(f"📸 Screen update from {data.get('student_id')}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing message: {e}")
                    continue
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("⏳ Reconnecting in 5 seconds...")
        await asyncio.sleep(5)
        await connect_and_listen()

if __name__ == "__main__":
    print("=" * 70)
    print("         👨‍🏫 TEACHER VIOLATION MONITOR - WebSocket")
    print("=" * 70)
    print()
    
    try:
        asyncio.run(connect_and_listen())
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user")
