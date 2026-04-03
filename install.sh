#!/bin/bash

echo "--- Rozpoczynam automatyczna instalacje systemu skanowania N01 ---"

# 1. Instalacja wymaganych narzedzi
echo "Aktualizacja pakietow i instalacja Dockera..."
sudo apt update
sudo apt install -y docker.io docker-compose curl python3 python3-pip

# 2. Przygotowanie czystego środowiska
echo "Przygotowanie srodowiska..."
mkdir -p ~/bso_skaner
cd ~/bso_skaner
rm -f docker-compose.yml compose.yaml # Usuwamy smieci po ew. starych probach

# 3. Pobranie Dockera prosto z kodu zrodlowego Greenbone (GWARANTOWANY LINK)
echo "Pobieranie konfiguracji Greenbone..."
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o docker-compose.yml

# 4. Przygotowanie pliku na nasz skrypt w Pythonie
echo "Tworzenie bazy pod skrypt zarzadzajacy..."
touch skaner.py 

# 5. Uruchomienie calosci
echo "Uruchamianie kontenerow Greenbone w tle..."
sudo docker-compose up -d

echo "--- Instalacja zakonczona sukcesem! ---"
echo "System Greenbone dziala w tle. Pobieranie bazy podatnosci zajmie chwile."
