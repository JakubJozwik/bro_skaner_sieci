#!/bin/bash

echo "--- Rozpoczynam automatyczna instalacje systemu skanowania N01 ---"

echo "1/5 Czyszczenie starych wersji Dockera..."
sudo apt-get remove -y docker.io docker-compose docker-doc podman-docker containerd runc 2>/dev/null

echo "2/5 Instalacja wymaganych narzedzi (Python, Curl, GVM-Tools)..."
sudo apt-get update
sudo apt-get install -y curl python3 python3-pip python3-gmp-parser
sudo pip3 install gvm-tools --break-system-packages

echo "3/5 Instalacja najnowszego Dockera v2 z oficjalnego zrodla..."
curl -fsSL https://get.docker.com | sudo sh

echo "4/5 Przygotowanie srodowiska Greenbone..."
mkdir -p ~/bso_skaner
cd ~/bso_skaner
rm -f docker-compose.yml compose.yaml
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml

# Przygotowanie czystego pliku pod skrypt w Pythonie
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/refs/heads/main/skaner.py" -o skaner.py

echo "5/5 Uruchamianie kontenerow w tle (nowy Docker Compose v2)..."
sudo docker compose up -d

echo "--- Instalacja zakonczona sukcesem! ---"
echo "System Greenbone dziala w tle. Baza podatnosci pobierze sie automatycznie."
