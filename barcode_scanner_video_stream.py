#import the necessary packages
import threading
from smbus import SMBus
from imutils.video import VideoStream
from pyzbar import pyzbar
from flask import Response
from flask import Flask
from flask import render_template
import argparse
import datetime
import imutils
import time
import cv2
from webstreaming import detect_motion

#initiate the I2C bus and choosing the address
addr=0x08
bus=SMBus(1)

#initialize the output frame and a lock used to ensure thread-safe exchanges of the output frames (useful when multiple browsers/tabs are viewing the stream)
outputFrame = None
lock = threading.Lock()

#initialize a flask object
app = Flask(__name__)

#construct the argument parser and parse the arguments
ap= argparse.ArgumentParser()
ap.add_argument("-o", "--output", type=str, default="barcodes1.csv", help="path to output CSV file containing barcodes")
args= vars(ap.parse_args())

#initialize the video stream and allow the camera sensor to warm up 
print("[INFO] starting video stream ...")
vs=VideoStream(usePiCamera=1).start()
time.sleep(2.0)

@app.route("/")
def index():
    #return the rendered template (du coup pas oublie de le faire dans l'arborescence du fichier)
    return render_template("index.html")

#open the output CSV file for writing and initialize the set of barcodes found thus far
csv = open(args["output"], "w")
found = set()

#loop over the frames from the video stream 
while True:

    #grab the frame from the threaded video stream and resize it to have a maximum width of 400 pixels
    frame = vs.read()
    frame = imutils.resize(frame, width=400)

    #acquire the lock, set the output frame, and release the lock 
    with lock:
        outputFrame = frame.copy()
    
    #find the barcodes in the frame and decode each of the barcodes
    barcodes = pyzbar.decode(frame)

    #loop over the detected barcodes
    for barcode in barcodes:
        #extract the bounding box location of the barcode and draw the bounding box surrounding the barcode on the image
        (x, y, w, h) = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        #the barcode data is a bytes object so if we want to draw it on our output image we need to convert it to a string first
        barcodeData = barcode.data.decode("utf-8")
        barcodeType = barcode.type

        #draw the barcode data and barcode type on the image
        text = "{} ({})".format(barcodeData, barcodeType)
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        #if the barcode text is currently not in our CSV file, write the timestamp + barcode to disk and update the set
        if barcodeData not in found:
            csv.write("{} ({})\n".format(datetime.datetime.now(), barcodeData))
            csv.flush()
            found.add(barcodeData)

        if barcodeData == "RIGHT":
            print("Go right!")
        if barcodeData == "LEFT":
            print("Go left!")
        if barcodeData == "SOUND":
            print("Make some noiiiise")
        if barcodeData == "LIGHT":
            print("May the dark never reigns over my land")
        if barcodeData == "5MENAVANT":
            print("Tout droit mais sur 5m")
            bus.write_byte(addr, 3)
        if barcodeData == "TOURNESURSOI":
            print("Tourner tourner tourner!")
            bus.write_byte(addr, 4)
        if barcodeData == "TOUTDROIT":
            print("Tout droit pour l'éternité")
            bus.write_byte(addr, 10)
    
    #show the output frame 
    cv2.imshow("Barcode Scanner", frame)
    key = cv2.waitKey(1) & 0xFF

    #if the q key is pressed, break from the loop
    if key == ord("q"):
        break

def generate():
    #grab global references to the output frame and lock variables
    global outputFrame, lock

    #loop over frames from the output stream
    while True:
        #wait until lock is acquired 
        with lock:
            #check if the output frame is available, otherwise skip the iteration of the loop 
            if outputFrame is None:
                continue

            #encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            #ensure the frame was successfully encoded
            if not flag:
                continue

        #yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    #return the response generated along with the specific media type 
    return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

#check to see if this is the main thread of execution
if __name__ = '__main__':
    #construct the argument parser and parse command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, required=True, help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, required=True, help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-f", "--frame-count", type=int, default=32, help="# of frames used to construct the background model")
    args = vars(ap.parse_args())

    #start a thread that will perform nothing even though it is written motion_detection
    t = threading.Thread(target=detect_motion, args=(args["frame_count"],))
    t.daemon = True
    t.start()

    #start the flask app
    app.run(host=args["ip"], port=args["ports"], debug=True, threaded=True, use_reloader=False)



#close the output CSV file and do a little bit of cleanup
print("[INFO] cleaning up ...")
csv.close()
cv2.destroyAllWindows()
vs.stop()

