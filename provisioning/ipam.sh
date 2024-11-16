#!/bin/bash

. .common.sh

apt -y install apache2 php php-cli libapache2-mod-php php-curl php-mysql php-curl php-gd php-intl php-pear php-imap php-apcu php-pspell php-tidy php-xmlrpc php-mbstring php-gmp php-json php-xml php-ldap php-common php-snmp php-fpm git

echo "update date.timezone - press any key to vim it"
read 
vim /etc/php/*/fpm/php.ini
systemctl restart php*-fpm.service

echo "Enter the password you would like the phpipam SQL user to have: "
read SQLPASS
cat > /root/Downloads/phpipam-provision.sql<< EOF
CREATE DATABASE phpipam;
GRANT ALL ON phpipam.* TO 'phpipam'@'%' IDENTIFIED BY '${SQLPASS}';
FLUSH PRIVILEGES;
EXIT
EOF
echo "MySQL 'root' user password: "
mysql -u root -p < /root/Downloads/phpipam-provision.sql

git clone --recursive https://github.com/phpipam/phpipam.git /var/www/phpipam

cp /var/www/phpipam/config.{dist.php,php}
echo "update DB connection details - press any key "
read
vim /var/www/phpipam/config.php

cat > /etc/apache2/sites-available/phpipam.conf <<EOF
<VirtualHost *:80>
    ServerAdmin af4h@af4h.net
    DocumentRoot "/var/www/phpipam"
    ServerName ipam1.hamshack.af4h.net
    ServerAlias www.ipam1.hamshack.af4h.net
    <Directory "/var/www/phpipam">
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog "/var/log/apache2/phpipam-error_log"
    CustomLog "/var/log/apache2/phpipam-access_log" combined
</VirtualHost>
EOF

chown -R www-data:www-data /var/www/phpipam/

a2enmod rewrite
a2ensite phpipam
apachectl -t
echo "Everything OK?"
read
systemctl restart apache2

echo "This will be the MySQL root password:"
mysql -u root -p phpipam < /var/www/phpipam/db/SCHEMA.sql

#default credentials Username: admin and Password: ipamadmin
