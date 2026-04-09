#!/bin/bash
if [ "$EUID" -ne 0 ]; then echo "BŁĄD: Uruchom jako: curl ... | sudo bash"; exit 1; fi

PROJECT_NAME="bso-n01"
INSTALL_DIR="/opt/bso_skaner"

echo "--- INSTALACJA SYSTEMU N01 (PROJEKT: $PROJECT_NAME) ---"

# 1. Pakiety
apt-get update -qq
apt-get install -y curl python3 python3-pip cron docker.io docker-compose-v2 -qq
pip3 install gvm-tools lxml --break-system-packages -q

# 2. Folder i pliki
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml
# Naprawa portu (Ustawiamy 54321 dla uniknięcia konfliktów na Windows)
sed -i 's/- 127.0.0.1:[0-9]*:8080/- 54321:8080/g' compose.yaml

curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py
chmod +x skaner.py

# 3. Start Dockera (Wymuszona nazwa projektu)
docker compose -p $PROJECT_NAME up -d --force-recreate

# 4. Cron
(crontab -l 2>/dev/null | grep -v "skaner.py" ; echo "0 2 * * 0 /usr/bin/python3 $INSTALL_DIR/skaner.py >> /var/log/bso_skaner.log 2>&1") | crontab -

echo "--- INSTALACJA ZAKONCZONA. ODCZEKAJ 20 MINUT I ODPAL SKANER ---"
