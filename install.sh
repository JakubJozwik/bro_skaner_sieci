#!/bin/bash

# 1. Sprawdzenie uprawnień roota
if [ "$EUID" -ne 0 ]; then 
  echo "BŁĄD: Proszę uruchomić: curl ... | sudo bash"
  exit 1
fi

echo "==========================================================="
echo " SYSTEM SKANOWANIA SIECI N01 - AUTOMATYCZNA INSTALACJA"
echo "==========================================================="

# 2. Czyszczenie starych pozostałości (Autonaprawa)
echo "[1/6] Czyszczenie poprzednich prób i blokad..."
# Próbujemy zatrzymać stary projekt jeśli istnieje
docker compose -p greenbone-community-edition down -v --remove-orphans 2>/dev/null
# Usuwamy folder, aby pobrać wszystko na świeżo
rm -rf /opt/bso_skaner

# 3. Instalacja pakietów
echo "[2/6] Instalacja wymaganych narzędzi..."
apt-get update
apt-get install -y curl python3 python3-pip cron docker.io
# Instalacja wtyczki compose jeśli jej nie ma
apt-get install -y docker-compose-v2 2>/dev/null 

# Instalacja bibliotek Python
pip3 install gvm-tools lxml --break-system-packages 

# 4. Przygotowanie folderu i plików
echo "[3/6] Pobieranie konfiguracji z GitHub..."
mkdir -p /opt/bso_skaner
cd /opt/bso_skaner

curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml

# NAPRAWA PORTU (Zawsze ustawiamy na 8085 dla stabilności)
sed -i 's/- 127.0.0.1:[0-9]*:/- 127.0.0.1:8085:/g' compose.yaml

# Pobieranie Twojego skryptu Python
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py
chmod +x skaner.py

# 5. Uruchomienie kontenerów (Wymuszony czysty start)
echo "[4/6] Uruchamianie kontenerów w tle..."
# Używamy nowej komendy 'docker compose' bez myślnika
docker compose -p greenbone-community-edition up -d --force-recreate

# 6. Konfiguracja harmonogramu Cron
echo "[5/6] Konfiguracja harmonogramu zadań..."
(crontab -l 2>/dev/null | grep -v "skaner.py" ; echo "0 2 * * 0 /usr/bin/python3 /opt/bso_skaner/skaner.py >> /var/log/bso_skaner.log 2>&1") | crontab -

echo "[6/6] Finalizacja..."
echo "==========================================================="
echo " INSTALACJA ZAKOŃCZONA SUKCESEM"
echo "==========================================================="
echo "System jest gotowy. Za ok. 15-20 min bazy danych zostaną"
echo "załadowane i będzie można wykonać skanowanie:"
echo "sudo python3 /opt/bso_skaner/skaner.py"
echo "==========================================================="
