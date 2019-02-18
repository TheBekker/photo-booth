#!/usr/bin/env python

#Imports
import datetime
import os
import shutil
from glob import glob
from time import sleep
from PIL import Image
from resizeimage import resizeimage

import RPi.GPIO as GPIO
import picamera

#############
### Save to USB ###
#############
#This function copies a file onto any USB storage devices that have been plugged in.
def copy_to_usb(filename):
  #Get directories which correspond to USB storage
  for dir in glob('/media/pi/*/'):

    #Need to exclude directories that include the string "SETTING", as these are system directories
    if "SETTING" not in dir:
    
      #Directory we will be saving to:
      copy_to_dir = dir + "photo-booth/"

      #Does the directory already exist?
      if not os.path.exists( copy_to_dir ):

        #Create directory to save photos in:
        os.makedirs( copy_to_dir )

      #Copy file into directory
      shutil.copy2(filename, copy_to_dir)


#############
### Debug ###
#############
# These options allow you to run a quick test of the app.
# Both options must be set to 'False' when running as proper photobooth
TESTMODE_AUTOPRESS_BUTTON = False # Button will be pressed automatically, and app will exit after 1 photo cycle
TESTMODE_FAST             = False # Reduced wait between photos and 2 photos only

########################
### Variables Config ###
########################
pin_camera_btn = 17 # pin that the 'take photo' button is attached to
pin_exit_btn   = 2 # pin that the 'exit app' button is attached to (OPTIONAL BUTTON FOR EXITING THE APP)
pin_flash_warm = 23
pin_flash_cold = 24
flash_warm_default = 5
flash_cold_default = 5
total_pics = 3      # number of pics to be taken
prep_delay = 5      # number of seconds as users prepare to have photo taken
photo_w = 3280     # take photos at this resolution
photo_h = 1845
screen_w = 1920      # resolution of the photo booth display
screen_h = 1080
thumbsTemp = []
capturedFilesTemp = []

if TESTMODE_FAST:
    total_pics = 2     # number of pics to be taken
    prep_delay = 2     # number of seconds at step 1 as users prep to have photo taken

##############################
### Setup Objects and Pins ###
##############################
#Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_camera_btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_exit_btn  , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_flash_warm, GPIO.OUT)
GPIO.setup(pin_flash_cold, GPIO.OUT)
pwm_flash_warm = GPIO.PWM(pin_flash_warm, 100)
pwm_flash_warm.start(0)
pwm_flash_cold = GPIO.PWM(pin_flash_cold, 100)
pwm_flash_cold.start(0)

#Setup Camera
camera = picamera.PiCamera()
camera.rotation = 270
camera.annotate_text_size = 160
camera.resolution = (photo_w, photo_h)
camera.hflip = True # When preparing for photos, the preview will be flipped horizontally.

####################
### Other Config ###
####################
REAL_PATH = os.path.dirname(os.path.realpath(__file__))

########################
### Helper Functions ###
########################
def print_overlay(string_to_print):
    """
    Writes a string to both [i] the console, and [ii] camera.annotate_text
    """
    print(string_to_print)
    camera.annotate_text = string_to_print

def get_base_filename_for_images():
    """
    For each photo-capture cycle, a common base filename shall be used,
    based on the current timestamp.

    Example:
    ${ProjectRoot}/photos/2017-12-31_23-59-59

    The example above, will later result in:
    ${ProjectRoot}/photos/2017-12-31_23-59-59_1of4.png, being used as a filename.
    """
    base_filename = REAL_PATH + '/photos/' + str(datetime.datetime.now()).split('.')[0]
    base_filename = base_filename.replace(' ', ' Kl.')
    base_filename = base_filename.replace(':', ':')
    return base_filename

#generate thumbnail using get_thumbnail_file_path_from_orignal_file_path()
def create_thumbnail(filePath):
    # thumbFilePath = get_thumbnail_file_path_from_orignal_file_path(filePath)
    # thumbsPath = os.path.split(thumbFilePath)[0]
    
    # #check if thumbnail folder exists, if not create
    # if not os.path.exists(thumbsPath):
    #     os.makedirs(thumbsPath)

    #open file, resize and save
    with open(filePath, 'r') as f:
        with Image.open(f) as image:
            image.thumbnail([1920, 1080], resample=3)
            return image
            # resizeimage.resize_cover(image, [1920, 1080])
            # cover = resizeimage.resize_cover(image, [1920, 1080])
            # cover.save(thumbFilePath, image.format)

#Generate path to thumbnail from original file path
def get_thumbnail_file_path_from_orignal_file_path(originalFilePath):
    #Get orignal path and add /thumbs/
    thumbsPath = os.path.split(originalFilePath)[0] + "/thumbs/"
    #Get orignal file extension for later easier filename change
    fileExt = os.path.splitext(originalFilePath)[1]
    #Get original filename (without full path)
    orgFilename = os.path.split(originalFilePath)[1]
    #Create thumbnail filename
    thumbFilename = orgFilename.replace(fileExt, "_thumb" + fileExt)
    #Return path and filename combined
    return thumbsPath + thumbFilename

def remove_overlay(overlay_id):
    """
    If there is an overlay, remove it
    """
    if overlay_id != -1:
        camera.remove_overlay(overlay_id)

# overlay on image from path on screen
def overlay_image_from_path(image_path, duration=0, layer=3):
    return overlay_image_from_object(Image.open(image_path), duration, layer)

# overlay one image on screen
def overlay_image_from_object(imgObject, duration=0, layer=3):
    """
    Add an overlay (and sleep for an optional duration).
    If sleep duration is not supplied, then overlay will need to be removed later.
    This function returns an overlay id, which can be used to remove_overlay(id).
    """

    # "The camera`s block size is 32x16 so any image data
    #  provided to a renderer must have a width which is a
    #  multiple of 32, and a height which is a multiple of
    #  16."
    #  Refer: http://picamera.readthedocs.io/en/release-1.10/recipes1.html#overlaying-images-on-the-preview

    # Create an image padded to the required size with
    # mode 'RGB'
    pad = Image.new('RGB', (
        ((imgObject.size[0] + 31) // 32) * 32,
        ((imgObject.size[1] + 15) // 16) * 16,
    ))

    # Paste the original image into the padded one
    pad.paste(imgObject, (0, 0))

    #Get the padded image data
    try:
        padded_img_data = pad.tobytes()
    except AttributeError:
        padded_img_data = pad.tostring() # Note: tostring() is deprecated in PIL v3.x

    # Add the overlay with the padded image as the source,
    # but the original image's dimensions
    o_id = camera.add_overlay(padded_img_data, size=imgObject.size)
    o_id.layer = layer

    if duration > 0:
        sleep(duration)
        camera.remove_overlay(o_id)
        return -1 # '-1' indicates there is no overlay
    else:
        return o_id # we have an overlay, and will need to remove it later

def flash(duty_cycle_warm, duty_cycle_cold):
    pwm_flash_warm.ChangeDutyCycle(duty_cycle_warm)
    pwm_flash_cold.ChangeDutyCycle(duty_cycle_cold)

###############
### Screens ###
###############

def prep_for_photo_screen(photo_number):
    """
    Prompt the user to get ready for the next photo
    """

    #Get ready for the next photo
    get_ready_image = REAL_PATH + "/assets/get_ready_"+str(photo_number)+".png"
    overlay_image_from_path(get_ready_image, prep_delay)

def taking_photo(photo_number, filename_prefix):
    """
    This function captures the photo
    """

    #get filename to use
    filename = filename_prefix + ' Nr.' + str(photo_number) + ' af '+ str(total_pics)+'.jpg'

    #countdown from 3, and display countdown on screen
    for counter in range(3,0,-1):
        flash(50,100)
        print_overlay("             ..." + str(counter))
        sleep(1)

    #Take still
    camera.annotate_text = ''
    print("Capture")
    camera.capture(filename)
    print("flash")
    flash(flash_warm_default, flash_cold_default)
    print("Photo (" + str(photo_number) + ") saved: " + filename)
    return filename


def playback_screen(thumbs):
    """
    Final screen before main loop restarts
    """

    #Processing
    print("Processing...")
    processing_image = REAL_PATH + "/assets/processing.png"
    overlay_image_from_path(processing_image, 2)
    
    #Playback
    prev_overlay = False
    for thumb in thumbs:
        #display thumbnail
        this_overlay = overlay_image_from_object(thumb, False, 3+total_pics)
        # The idea here, is only remove the previous overlay after a new overlay is added.
        if prev_overlay:
            remove_overlay(prev_overlay)
        sleep(2)
        prev_overlay = this_overlay
    remove_overlay(prev_overlay)
    
    #All done
    print("All done!")
    finished_image = REAL_PATH + "/assets/all_done_delayed_upload.png"
    overlay_image_from_path(finished_image, 5)


def main():
    """
    Main program loop
    """
    flash(flash_warm_default, flash_cold_default)
    #Start Program
    print("Welcome to the photo booth!")
    print("Press the button to take a photo")

    #Show splash screen
    overlay_1 = overlay_image_from_path(REAL_PATH + "/assets/Setup.png", 10, 3)

    #Start camera preview
    camera.start_preview(resolution=(screen_w, screen_h))

    #Wait for press
    GPIO.wait_for_edge(pin_camera_btn, GPIO.FALLING)

    #Display intro screen
    intro_image_1 = REAL_PATH + "/assets/intro_1.png"
    intro_image_2 = REAL_PATH + "/assets/intro_2.png"
    overlay_1 = overlay_image_from_path(intro_image_1, 0, 3)
    overlay_2 = overlay_image_from_path(intro_image_2, 0, 4)

    #Wait for someone to push the button
    i = 0
    blink_speed = 5
    while True:

        #Use falling edge detection to see if button is pushed
        is_pressed = GPIO.wait_for_edge(pin_camera_btn, GPIO.FALLING, timeout=100)
        exit_button = GPIO.wait_for_edge(pin_exit_btn, GPIO.FALLING, timeout=100)

        if exit_button is not None:
            return #Exit the photo booth

        if TESTMODE_AUTOPRESS_BUTTON:
            is_pressed = True

        #Stay inside loop, until button is pressed
        if is_pressed is None:
            
            #After every 5 cycles, alternate the overlay
            i = i+1
            if i==blink_speed:
                overlay_2.alpha = 255
            elif i==(2*blink_speed):
                overlay_2.alpha = 0
                i=0
            
            #Regardless, restart loop
            continue

        #Button has been pressed!
        filename_prefix = get_base_filename_for_images()
        print("Button pressed! Get ready!!")
        remove_overlay(overlay_2)
        remove_overlay(overlay_1)

        capturedFilesTemp = list()
        thumbsTemp = list()

        for photo_number in range(1, total_pics + 1):
            prep_for_photo_screen(photo_number)
            capturedFilesTemp.append(taking_photo(photo_number, filename_prefix))

        #Save to usb and make thumbs
        processing_overlay = overlay_image_from_path(REAL_PATH + "/assets/processing.png")
        for filepath in capturedFilesTemp:
            print("copy to usb")
            copy_to_usb(filepath)
            print("Create thumb")
            thumbsTemp.append(create_thumbnail(filepath))

        remove_overlay(processing_overlay)

        #thanks for playing
        playback_screen(thumbsTemp)
        
        # If we were doing a test run, exit here.
        if TESTMODE_AUTOPRESS_BUTTON:
            break

        # Otherwise, display intro screen again
        overlay_1 = overlay_image_from_path(intro_image_1, 0, 3)
        overlay_2 = overlay_image_from_path(intro_image_2, 0, 4)
        print("Press the button to take a photo")

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("goodbye")

    except Exception as exception:
        print("unexpected error: ", str(exception))

    finally:
        camera.stop_preview()
        camera.close()
        pwm_flash_cold.stop()
        pwm_flash_warm.stop()
        GPIO.cleanup()

