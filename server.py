import face_recognition
import cv2
import numpy as np
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from streamer import Streamer
from dotenv import dotenv_values
import requests
import os
from datetime import datetime, timedelta

config = dotenv_values(".env")

port = 3030
streamer = Streamer(port, stream_res=(640,480))

# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)


# Переменные для контроля спама
last_unknown_face_time = None
MIN_EVENT_INTERVAL = timedelta(minutes=1)  # Минимальный интервал между событиями

known_face_encodings = []
known_face_names = []

def load_images():
    clients_json = requests.get(f"http://{config.get("WEB")}/clients/json")
    clients = clients_json.json()
    for client in clients:
        photo_request = requests.get(f"http://{config.get("WEB")}/client/photo/{client['id']}")
        if not os.path.exists("imgs"):
            os.makedirs("imgs")
        path = os.path.abspath(os.path.join("imgs", f"{client['id']}.jpg"))
        with open(path, 'wb') as f:
            f.write(photo_request.content)
        image = face_recognition.load_image_file(path)
        face_encoding = face_recognition.face_encodings(image)[0]
        known_face_encodings.append(face_encoding)
        known_face_names.append(f"{client['id']}")

load_images()

def check_and_send_unknown_face_event():
    global last_unknown_face_time
    
    current_time = datetime.now()
    unknown_faces_present = "Unknown" in face_names
    
    if unknown_faces_present:
        # Если неизвестное лицо в кадре и прошло достаточно времени с последнего события
        if last_unknown_face_time is None or (current_time - last_unknown_face_time) > MIN_EVENT_INTERVAL:
            send_event("Неопознанное лицо в кадре", f"Неопознанное лицо обнаружено {current_time}")
            last_unknown_face_time = current_time
    else:
        # Если неизвестных лиц нет, сбрасываем таймер
        last_unknown_face_time = None

# Create arrays of known face encodings and their names


# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True

last_face_names = []
last_face_names_flag = False

def send_event(msg, desc):
    print(f"{msg} {desc}")
    event_request_data = {
        "title": msg,
        "description": desc
    }
    event_request = requests.post(f"http://{config.get("WEB")}/event/add", json=event_request_data)
    if not event_request.ok:
        print(f"Событие не отправлено. Ошибка {event_request.status_code}")

def event_handler():
    for face_name in last_face_names:
        if face_name == "Unknown":
            send_event("Неопознанное лицо в кадре", f"Неопознанное лицо в кадре {datetime.now()}")

while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()

    # Only process every other frame of video to save time
    if process_this_frame:
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]
        rgb_small_frame = cv2.cvtColor(rgb_small_frame , cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)   
        
        # Find all the faces and face encodings in the current frame of video
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            # # If a match was found in known_face_encodings, just use the first one.
            # if True in matches:
            #     first_match_index = matches.index(True)
            #     name = known_face_names[first_match_index]

            # Or instead, use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]

            face_names.append(name)

    # Проверяем и отправляем событие при необходимости
    check_and_send_unknown_face_event()

    process_this_frame = not process_this_frame


    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    streamer.update_frame(frame)

    if not streamer.is_streaming:
        streamer.start_streaming()

    cv2.waitKey(30)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
video_capture.release()