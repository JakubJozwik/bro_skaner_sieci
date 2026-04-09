#!/bin/bash
# System Skanowania N01 - Skrypt Instalacyjny
# Autorzy: Jakub Józwik, Mateusz Kotowski

if [ "$EUID" -ne 0 ]; then 
    echo "BŁĄD: Uruchom jako: curl ... | sudo bash"
    exit 1
fi

echo "--- ROZPOCZYNAM INSTALACJE SYSTEMU N01 (BSO) ---"

# 1. Porządki i przygotowanie
PROJECT_NAME="bso-n01"
INSTALL_DIR="/opt/bso_skaner"

# Usuwamy stare śmieci, jeśli istnieją
docker compose -p $PROJECT_NAME down -v --remove-orphans 2>/dev/null
rm -rf $INSTALL_DIR
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 2. Instalacja pakietów systemowych
echo "[+] Instalacja narzędzi..."
apt-get update -qq
apt-get install -y curl python3 python3-pip cron docker.io docker-compose-v2 -qq
pip3 install gvm-tools lxml --break-system-packages -q

# 3. Konfiguracja kontenerów
echo "[+] Pobieranie i konfiguracja silnika Greenbone..."
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml

# Ustawienie bezpiecznego portu 54321 (unikamy konfliktów na Windows)
sed -i 's/- 127.0.0.1:[0-9]*:8080/- 54321:8080/g' compose.yaml

# 4. Pobieranie skryptu skanującego
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py
chmod +x skaner.py

# 5. Uruchomienie Dockera
echo "[+] Uruchamianie kontenerów (Project: $PROJECT_NAME)..."
docker compose -p $PROJECT_NAME up -d --force-recreate

# 6. Harmonogram Cron (co niedzielę o 02:00)
(crontab -l 2>/dev/null | grep -v "skaner.py" ; echo "0 2 * * 0 /usr/bin/python3 $INSTALL_DIR/skaner.py >> /var/log/bso_skaner.log 2>&1") | crontab -

echo "==========================================================="
echo " INSTALACJA ZAKOŃCZONA SUKCESEM"
echo "==========================================================="
echo "WAŻNE: Skaner potrzebuje ok. 15-20 min na załadowanie baz."
echo "Po tym czasie uruchom: sudo python3 $INSTALL_DIR/skaner.py"
echo "==========================================================="
