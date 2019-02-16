# Raspberry Pi Photo Booth
The code for oury Raspberry Pi Photo Booth

Automatically launching the Photo Booth app when the Pi starts:
sudo nano /etc/xdg/autostart/autostart_photobooth.desktop

enter:
[Desktop Entry]
Type=Application
Name=camera.py
Comment=Raspberry Pi Photo Booth
NoDisplay=false
Exec=sudo python /home/pi/photo-booth/camera.py
NotShowIn=GNOME;KDE;XFCE;
Name[en_US]= camera.py


# Disable autostart, by moving the file into home directory instead
sudo mv /etc/xdg/autostart/autostart_photobooth.desktop ~/autostart_photobooth.desktop

# Re-enable autostart, by moving file back into autostart directory
sudo mv ~/autostart_photobooth.desktop /etc/xdg/autostart/autostart_photobooth.desktop 
