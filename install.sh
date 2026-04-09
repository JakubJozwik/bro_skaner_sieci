#!/bin/bash

echo "==========================================================="
echo " Rozpoczynam automatyczna instalacje systemu skanowania N01"
echo "==========================================================="

echo "1/6 Czyszczenie starych wersji Dockera..."
sudo apt-get remove -y docker.io docker-compose docker-doc podman-docker containerd runc 2>/dev/null

echo "2/6 Instalacja wymaganych narzedzi (Python, gvm-tools)..."
sudo apt-get update
sudo apt-get install -y curl python3 python3-pip cron

# Na nowych systemach (np. Ubuntu 24.04/Debian 12) wymagana jest flaga --break-system-packages
sudo pip3 install gvm-tools lxml --break-system-packages 

echo "3/6 Instalacja najnowszego Dockera v2..."
curl -fsSL https://get.docker.com | sudo sh

echo "4/6 Przygotowanie srodowiska Greenbone..."
mkdir -p /root/bso_skaner
cd /root/bso_skaner
rm -f docker-compose.yml compose.yaml skaner.py

# Pobranie compose file ze źródła producenta
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml

# UWAGA: Tutaj wstaw prawidlowy adres swojego skryptu z GitHuba
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py
chmod +x skaner.py

echo "5/6 Uruchamianie kontenerow (Wymuszam prawidlowa nazwe wolumenu!)..."
# Parametr -p gwarantuje, że wolumen nazwie się 'greenbone-community-edition'
sudo docker compose -p greenbone-community-edition up -d

echo "6/6 Konfiguracja harmonogramu (Cron)..."
# Uruchamianie skanu w każdą niedzielę o 2:00 w nocy z logowaniem wyjścia
(sudo crontab -l 2>/dev/null; echo "0 2 * * 0 /usr/bin/python3 /root/bso_skaner/skaner.py >> /var/log/bso_skaner.log 2>&1") | sudo crontab -

echo "==========================================================="
echo " INSTALACJA ZAKONCZONA SUKCESEM! "
echo "==========================================================="
echo "UWAGA: Greenbone rozpoczyna pobieranie definicji wirusow i podatnosci (NVT/SCAP/CERT)."
echo "Proces ten musi sie zakonczyc przed pierwszym uruchomieniem skanera."
echo "Zostaw serwer wlaczony na ok. 60-120 minut."
echo ""
echo "Aby wykonac skan recznie dla testu, wpisz:"
echo "sudo python3 /root/bso_skaner/skaner.py"
echo "==========================================================="
