#!/bin/bash

# Sprawdzenie czy skrypt jest uruchomiony z uprawnieniami roota
if [ "$EUID" -ne 0 ]; then 
  echo "BŁĄD: Proszę uruchomić skrypt z sudo: curl ... | sudo bash"
  exit 1
fi

echo "==========================================================="
echo " SYSTEM SKANOWANIA SIECI N01 - INSTALACJA AUTOMATYCZNA"
echo "==========================================================="

echo "[1/5] Instalacja pakietów systemowych..."
apt-get update
apt-get install -y curl python3 python3-pip cron docker.io docker-compose
# Instalacja bibliotek Python (z obejściem dla nowych systemów)
pip3 install gvm-tools lxml --break-system-packages 

echo "[2/5] Przygotowanie środowiska w /opt/bso_skaner..."
mkdir -p /opt/bso_skaner
cd /opt/bso_skaner

# Pobieranie oficjalnego pliku Docker Compose od Greenbone
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml

# --- NAPRAWA KONFLIKTU PORTÓW (Ważne dla Windows/VMware) ---
# Zamieniamy port 443 na 9392, aby uniknąć błędu "Port already in use"
# Ta komenda znajdzie dowolny port zmapowany na 127.0.0.1 i zamieni go na 8085
sed -i 's/- 127.0.0.1:[0-9]*:/- 127.0.0.1:8085:/g' compose.yaml

# Pobieranie Twojego skryptu skanującego z GitHuba
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py
chmod +x skaner.py

echo "[3/5] Uruchamianie silnika skanera (Docker)..."
# Wymuszamy nazwę projektu, aby ścieżka do wolumenu w skaner.py zawsze się zgadzała
docker compose -p greenbone-community-edition up -d

echo "[4/5] Konfiguracja harmonogramu Cron (Co niedzielę o 02:00)..."
(crontab -l 2>/dev/null; echo "0 2 * * 0 /usr/bin/python3 /opt/bso_skaner/skaner.py >> /var/log/bso_skaner.log 2>&1") | crontab -

echo "[5/5] Finalizacja..."
echo "==========================================================="
echo " INSTALACJA ZAKOŃCZONA SUKCESEM"
echo "==========================================================="
echo "1. System Greenbone uruchamia się w tle (Docker)."
echo "2. Pierwsze pobieranie bazy podatności zajmuje ok. 15-30 min."
echo "3. Aby przetestować system ręcznie, wpisz:"
echo "   sudo python3 /opt/bso_skaner/skaner.py"
echo "==========================================================="
