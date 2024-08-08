import cv2
import os
import pickle
import face_recognition
import numpy as np
import cvzone
from datetime import datetime

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "<paste here>",
        # database URL
        "storageBucket": "<paste here>",
    },
)

bucket = storage.bucket()

capture = cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # width .... CAP_PROP_FRAME_WIDTH ---> 3
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # height .... CAP_PROP_FRAME_HEIGHT ---> 4

imgBackground = cv2.imread("static/Files/Resources/background.png")

# for modes
folderModePath = "static/Files/Resources/Modes/"
modePathList = os.listdir(folderModePath)
imgModeList = []

for path in modePathList:
    imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))


# encoding loading ---> to identify if the person is in our database or not.... to detect faces that are known or not

file = open("EncodeFile.p", "rb")
encodeListKnownWithIds = pickle.load(file)
file.close()
encodedFaceKnown, studentIds = encodeListKnownWithIds
# print(studentIds)

modeType = 0
id = -1
imgStudent = []
counter = 0


while True:
    success, img = capture.read()

    # take the encoding and check with the new faces if they are matching or not
    imgSmall = cv2.resize(
        img, (0, 0), None, 0.25, 0.25
    )  # scale values not the actual values # resize to make it computationally viable
    imgSmall = cv2.cvtColor(
        imgSmall, cv2.COLOR_BGR2RGB
    )  # because the face recognition system takes the rgb values

    faceCurrentFrame = face_recognition.face_locations(
        imgSmall
    )  # to identify the current location of the face
    encodeCurrentFrame = face_recognition.face_encodings(
        imgSmall, faceCurrentFrame
    )  # for new faces # we pass the image and current location of the image

    # this should be in top as we are overlaying the rectangle in the imgBackground
    imgBackground[162 : 162 + 480, 55 : 55 + 640] = img
    imgBackground[44 : 44 + 633, 808 : 808 + 414] = imgModeList[modeType]

    if faceCurrentFrame:
        for encodeFace, faceLocation in zip(encodeCurrentFrame, faceCurrentFrame):
            matches = face_recognition.compare_faces(
                encodedFaceKnown, encodeFace
            )  # the one from the pickle file will be compared with the current encodeFace
            faceDistance = face_recognition.face_distance(encodedFaceKnown, encodeFace)
            # print('matches', matches)
            # print('faceDistance', faceDistance)

            matchIndex = np.argmin(faceDistance)
            # print('matchIndex', matchIndex)

            y1, x2, y2, x1 = faceLocation
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4

            bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1

            imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

            if matches[matchIndex] == True:
                # print('Known Face Detected')
                # print(studentIds[matchIndex])
                id = studentIds[matchIndex]
                # print(id)
                if counter == 0:
                    cvzone.putTextRect(
                        imgBackground, "Face Detected", (65, 200), thickness=2
                    )
                    # cv2.imshow("Face Attendance", imgBackground)
                    cv2.waitKey(1)
                    counter = 1
                    modeType = 1

            else:
                cvzone.putTextRect(
                    imgBackground, "Face Detected", (65, 200), thickness=2
                )
                cv2.waitKey(3)
                cvzone.putTextRect(
                    imgBackground, "Face Not Found", (65, 200), thickness=2
                )
                modeType = 4
                counter = 0
                imgBackground[44 : 44 + 633, 808 : 808 + 414] = imgModeList[modeType]


        if counter != 0:
            if counter == 1:
                # get the data
                studentInfo = db.reference(f"Students/{id}").get()
                # print(studentInfo)

                # get the image from the storage
                blob = bucket.get_blob(f"static/Files/Images/{id}.jpg")
                array = np.frombuffer(blob.download_as_string(), np.uint8)
                imgStudent = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)

                # update data of attendance
                datetimeObject = datetime.strptime(
                    studentInfo["last_attendance_time"], "%Y-%m-%d %H:%M:%S"
                )
                secondElapsed = (datetime.now() - datetimeObject).total_seconds()
                # print(secondElapsed)

                if secondElapsed > 30:
                    ref = db.reference(f"Students/{id}")
                    studentInfo["total_attendance"] += 1
                    ref.child("total_attendance").set(studentInfo["total_attendance"])
                    ref.child("last_attendance_time").set(
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                else:
                    modeType = 3
                    counter = 0
                    imgBackground[44 : 44 + 633, 808 : 808 + 414] = imgModeList[
                        modeType
                    ]

            if modeType != 3:
                if 10 < counter <= 20:
                    modeType = 2

                imgBackground[44 : 44 + 633, 808 : 808 + 414] = imgModeList[modeType]

                if counter <= 10:
                    cv2.putText(
                        imgBackground,
                        str(studentInfo["total_attendance"]),
                        (861, 125),
                        cv2.FONT_HERSHEY_COMPLEX,
                        1,
                        (255, 255, 255),
                        1,
                    )
                    cv2.putText(
                        imgBackground,
                        str(studentInfo["major"]),
                        (1006, 550),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )
                    cv2.putText(
                        imgBackground,
                        str(id),
                        (1006, 493),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )
                    cv2.putText(
                        imgBackground,
                        str(studentInfo["standing"]),
                        (910, 625),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.6,
                        (100, 100, 100),
                        1,
                    )
                    cv2.putText(
                        imgBackground,
                        str(studentInfo["year"]),
                        (1025, 625),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.6,
                        (100, 100, 100),
                        1,
                    )
                    cv2.putText(
                        imgBackground,
                        str(studentInfo["starting_year"]),
                        (1125, 625),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.6,
                        (100, 100, 100),
                        1,
                    )

                    (w, h), _ = cv2.getTextSize(
                        str(studentInfo["name"]), cv2.FONT_HERSHEY_COMPLEX, 1, 1
                    )

                    offset = (414 - w) // 2
                    cv2.putText(
                        imgBackground,
                        str(studentInfo["name"]),
                        (808 + offset, 445),
                        cv2.FONT_HERSHEY_COMPLEX,
                        1,
                        (50, 50, 50),
                        1,
                    )

                    imgStudentResize = cv2.resize(imgStudent, (216, 216))

                    imgBackground[175 : 175 + 216, 909 : 909 + 216] = imgStudentResize

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = []
                    imgStudent = []
                    imgBackground[44 : 44 + 633, 808 : 808 + 414] = imgModeList[
                        modeType
                    ]

    else:
        modeType = 0
        counter = 0

    cv2.imshow("Face Attendance", imgBackground)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
