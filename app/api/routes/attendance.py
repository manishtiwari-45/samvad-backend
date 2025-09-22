from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
from pydantic import BaseModel
# import face_recognition  # Temporarily disabled for deployment
# import numpy as np  # Temporarily disabled for deployment
import io
from PIL import Image
import json
import base64

from app.core.secure_error_handler import SecureErrorHandler, SecureValidator
from app.db.database import get_session
from app.db.models import User, AttendanceRecord
from app.api.deps import get_current_user

router = APIRouter()

# Helper function to convert string back to numpy array
# Face recognition functions temporarily disabled for deployment
# def string_to_encoding(encoding_str: str) -> np.ndarray:
#     return np.array([float(val) for val in encoding_str.split(',')])

# Face recognition attendance temporarily disabled for deployment
# # WebSocket ka URL ab general ho gaya hai
# @router.websocket("/ws/general")
# async def attendance_websocket(websocket: WebSocket, notes: str = "General Attendance", db: Session = Depends(get_session)):
#     await websocket.accept()
    
#     # 1. Sabhi enrolled students (jinka face data hai) ko database se load karein
#     all_enrolled_users = db.exec(select(User).where(User.face_encoding != None)).all()
    
#     known_face_encodings = []
#     known_face_users = []
    
#     for user in all_enrolled_users:
#         known_face_encodings.append(string_to_encoding(user.face_encoding))
#         known_face_users.append(user)

#     if not known_face_encodings:
#         await websocket.close(code=1008, reason="No enrolled faces found in the system.")
#         return

#     try:
#         while True:
#             # 2. Frontend se image data receive karein
#             data = await websocket.receive_text()
            
#             header, encoded = data.split(",", 1)
#             image_data = base64.b64decode(encoded)
#             image = Image.open(io.BytesIO(image_data)).convert("RGB")
#             image_np = np.array(image)

#             # 3. Image mein face dhoondhein aur recognize karein
#             face_locations = face_recognition.face_locations(image_np)
#             unknown_encodings = face_recognition.face_encodings(image_np, face_locations)

#             recognized_user = None
#             for encoding in unknown_encodings:
#                 matches = face_recognition.compare_faces(known_face_encodings, encoding, tolerance=0.5)
                
#                 if True in matches:
#                     first_match_index = matches.index(True)
#                     recognized_user = known_face_users[first_match_index]
                    
#                     # 4. Check karein ki kya is user ki attendance aaj pehle se mark ho chuki hai
#                     today = date.today()
#                     start_of_day = datetime.combine(today, time.min)
#                     end_of_day = datetime.combine(today, time.max)
                    
#                     existing_record = db.exec(
#                         select(AttendanceRecord).where(
#                             AttendanceRecord.user_id == recognized_user.id,
#                             AttendanceRecord.timestamp >= start_of_day,
#                             AttendanceRecord.timestamp <= end_of_day,
#                             AttendanceRecord.event_id == None # Sirf general attendance check karein
#                         )
#                     ).first()
                    
#                     if not existing_record:
#                         # 5. Nayi attendance mark karein
#                         new_record = AttendanceRecord(user_id=recognized_user.id, notes=notes)
#                         db.add(new_record)
#                         db.commit()
#                         await websocket.send_json({"status": "SUCCESS", "name": recognized_user.full_name, "id": recognized_user.id})
#                     else:
#                         await websocket.send_json({"status": "ALREADY_MARKED", "name": recognized_user.full_name, "id": recognized_user.id})
                    
#                     break
            
#             if not recognized_user:
#                 await websocket.send_json({"status": "NOT_FOUND"})

#     except WebSocketDisconnect:
#         SecureErrorHandler.log_error(Exception("WebSocket disconnected"), "General Attendance WebSocket")
#     except Exception as e:
#         SecureErrorHandler.log_error(e, "General Attendance WebSocket")
#         await websocket.close(code=1011, reason="An internal error occurred")