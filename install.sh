#!/bin/bash
if [ "$EUID" -ne 0 ]; then echo "BŁĄD: Uruchom jako: curl ... | sudo bash"; exit 1; fi

echo "--- CZYSZCZENIE I INSTALACJA N01 ---"
docker compose -p greenbone-community-edition down -v --remove-orphans 2>/dev/null
rm -rf /opt/bso_skaner

apt-get update
apt-get install -y curl python3 python3-pip cron docker.io docker-compose-v2
pip3 install gvm-tools lxml --break-system-packages 

mkdir -p /opt/bso_skaner
cd /opt/bso_skaner

# Pobieranie konfiguracji
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml
# Naprawa portu na 8085
# Ta wersja usuwa '127.0.0.1' i ustawia port 54321
sed -i 's/- 127.0.0.1:[0-9]*:8080/- 54321:8080/g' compose.yaml

# Pobieranie skryptu Python (Upewnij się, że link jest poprawny!)
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py
chmod +x skaner.py

echo "--- URUCHAMIANIE DOCKERA ---"
docker compose -p greenbone-community-edition up -d --force-recreate

# Harmonogram Cron
(crontab -l 2>/dev/null | grep -v "skaner.py" ; echo "0 2 * * 0 /usr/bin/python3 /opt/bso_skaner/skaner.py >> /var/log/bso_skaner.log 2>&1") | crontab -

echo "--- GOTOWE! ODCZEKAJ 20 MINUT I ODPAL SKANER ---"
