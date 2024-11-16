#!/bin/bash

#TODO: Documentation/Comments in-line
#TODO: Verify running as `root`
#TODO: Error handling

# Inspired by https://computingforgeeks.com/install-powerdns-and-powerdns-admin-on-debian/

source ./common.sh

apt -y install curl git libpq-dev software-properties-common gnupg1

curl --output_dir=/root/Downloads -LsS -O https://downloads.mariadb.com/MariaDB/mariadb_repo_setup
bash /root/Downloads/mariadb_repo_setup

apt -y update --fix-missing
apt -y install mariadb-server mariadb-client
mysql_secure_installation
systemctl start mariadb
systemctl enable mariadb

echo "Please input your preferred MySQL password for \'powerdns_user\': "
read SQLPASS
cat > /root/Downloads/PowerDNS-Provision.sql << EOF
CREATE DATABASE powerdns;
GRANT ALL ON powerdns.* TO 'powerdns_user'@'%' IDENTIFIED BY '${SQLPASS}';
FLUSH PRIVILEGES;
EXIT
EOF
mysql -u root -p < /root/Downloads/PowerDNS-Provision.sql

systemctl stop systemd-resolved
systemctl disable systemd-resolved
unlink /etc/resolv.conf
echo 'nameserver 8.8.8.8' > /etc/resolv.conf

#TODO: Verify Debian version
# This Repo is for #11 "bullseye"
echo 'deb [arch=amd64] http://repo.powerdns.com/debian bullseye-auth-46 main' | tee /etc/apt/sources.list.d/pdns.list
curl -fsSL https://repo.powerdns.com/FD380FBB-pub.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/pdns.gpg
cat >/etc/apt/preferences.d/pdns << EOF
Package: pdns-*
Pin: origin repo.powerdns.com
Pin-Priority: 600
EOF

apt -y update --fix-missing
apt -y install pdns-server pdns-backend-mysql

mysql -u powerdns_user -p powerdns < /usr/share/pdns-backend-mysql/schema/schema.mysql.sql

mysql -u powerdns_user -p powerdns -e 'ALTER TABLE records ADD COLUMN change_date int(10) DEFAULT NULL;'

cat > /etc/powerdns/pdns.d/pdns.local.gmysql.conf << EOF
# MySQL Configuration
# Launch gmysql backend
launch+=gmysql
# gmysql parameters
gmysql-host=127.0.0.1
gmysql-port=3306
gmysql-dbname=powerdns
gmysql-user=powerdns_user
gmysql-password=${SQLPASS}
gmysql-dnssec=yes
# gmysql-socket=
EOF
chown pdns: /etc/powerdns/pdns.d/pdns.local.gmysql.conf
chmod 640 /etc/powerdns/pdns.d/pdns.local.gmysql.conf

systemctl stop pdns.service
pdns_server --daemon=no --guardian=no --loglevel=9

systemctl restart pdns
systemctl enable pdns

ss -alnp4 | grep pdns
