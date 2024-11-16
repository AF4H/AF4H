#!/bin/bash

# A script to install the `hamclock` program (https://www.clearskyinstitute.com/ham/HamClock/)
# after configuring a very minimal GUI environment. 
#
# Inspiration comes from this page: 
#   https://github.com/josfaber/debian-kiosk-installer/blob/master/kiosk-installer.sh
#
# I began with a clean installation of Debian Bullseye (11), which consists of
# "Standard System Utilities" and "SSH Server". Notably unselected is the GUI
# environment.
#
# My system is a VM running on Proxmox VE with 1 CPU core and 512MB RAM,
# using a USB monitor and no keyboard/mouse

#TODO: Logic to ensure that this script is running as `root`
#TODO: Catch errors and abort as appropriate

HAMCLOCK_SOURCE='https://www.clearskyinstitute.com/ham/HamClock/ESPHamClock.zip'

# Starting with ensuring our system is up to date:
apt update --fix-missing

# Now to install some dependencies (IE: a GUI):
apt install \
	vim \
	xorg \
	openbox \
	lightdm \
	locales \
	curl \
	make \
	g++ \
	unzip \
	xorg-dev \
	tightvncserver \
	-y 	#comment this line out if you prefer a manual approval of
		#packages to install

# USB Monitor support
cd
wget https://www.synaptics.com/sites/default/files/Ubuntu/pool/stable/main/all/synaptics-repository-keyring.deb
apt install synaptics-repository-keyring.deb
apt install displaylink-driver

# Kiosk user and group additions
groupadd kiosk
# Add kiosk user if only it doesn't exist
id -u kiosk &>/dev/null || useradd -m kiosk -g kiosk -s /bin/bash

# Start setting up our user environment:
mkdir -p /home/kiosk/.config/openbox
# remove virtual consoles
if [ -e "/etc/X11/xorg.conf" ]; then
  mv /etc/X11/xorg.conf /etc/X11/xorg.conf.backup
fi
cat > /etc/X11/xorg.conf << EOF
Section "ServerFlags"
    Option "DontVTSwitch" "true"
EndSection
EOF

# create config
if [ -e "/etc/lightdm/lightdm.conf" ]; then
  mv /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.backup
fi
cat > /etc/lightdm/lightdm.conf << EOF
[SeatDefaults]
autologin-user=kiosk
user-session=openbox
EOF

# Fetch and build HamClock
cd /home/kiosk/
curl -O ${HAMCLOCK_SOURCE}
unzip `echo ${HAMCLOCK_SOURCE} | awk 'BEGIN { FS = "/" } ; { print $NF }'`
cd ESPHamClock 
make hamclock-1600x960
make install
cd 

# create autostart
if [ -e "/home/kiosk/.config/openbox/autostart" ]; then
  mv /home/kiosk/.config/openbox/autostart /home/kiosk/.config/openbox/autostart.backup
fi
cat > /home/kiosk/.config/openbox/autostart << EOF
#!/bin/bash

while :
do
  xrandr --auto
  hamclock
  sleep 5
done &
EOF

# Ensure ~kiosk/ perms are good
chown -R kiosk:kiosk /home/kiosk

echo "Done!"
