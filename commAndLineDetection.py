import numpy as np
import cv2
from smbus import SMBus

addr=0x08
bus = SMBus(1)
video_capture = cv2.VideoCapture(-1)
video_capture.set(3, 160)
video_capture.set(4, 120)

while(True):
    
    #capture the frames
    ret, frame = video_capture.read()
    
    #crop the image to the bottom half of the initial frame
    crop_img = frame[60:120, 0:160]
    
    #convert to grayscale
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    
    #gaussian blur
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    #color threshold
    ret, thresh = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY_INV)
    
    #find the contours of the frame
    contours, hierarchy = cv2.findContours(thresh.copy(), 1, cv2.CHAIN_APPROX_NONE)
    
    #find the biggest contour (if detected)
    if len(contours) > 0:
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])
        
        #draw the contours and lines onto the initial cropped image
        cv2.line(crop_img, (cx, 0), (cx, 720), (255, 0, 0), 1)
        cv2.line(crop_img, (0, cy), (1280, cy), (255, 0, 0), 1)
        
        cv2.drawContours(crop_img, contours, -1, (0, 255, 0), 1)
        
        #the robot detectsthe positioning of the line and figures out which way to turn
        if cx >= 120:
            print ("Turn Left!")
            bus.write_byte(addr, 1)

            
        if cx < 120 and cx >50:
            print ("On Track!")
            bus.write_byte(addr, 2)
            
        if cx <= 50:
            print ("Turn Right!")
            bus.write_byte(addr, 3)
                
        else:
            print ("I don't see the line")
            
    #display the resolution frame
    cv2.imshow('frame', crop_img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    