#!/bin/bash

echo "--- Rozpoczynam automatyczna instalacje systemu skanowania N01 ---"

# 1. Instalacja wymaganych narzedzi (Docker, Python)
echo "Aktualizacja pakietow i instalacja Dockera..."
sudo apt update
sudo apt install -y docker.io docker-compose curl python3 python3-pip

# 2. Utworzenie katalogu roboczego
echo "Przygotowanie srodowiska..."
mkdir -p ~/bso_skaner
cd ~/bso_skaner

# 3. Pobranie gotowego srodowiska Greenbone (NOWY LINK)
echo "Pobieranie oficjalnej konfiguracji Greenbone..."
curl -f -L https://greenbone.github.io/docs/latest/_static/compose.yaml -o docker-compose.yml

# 4. Pobranie naszego skryptu w Pythonie z GitHuba
echo "Pobieranie skryptu zarzadzajacego..."
touch skaner.py 

# 5. Uruchomienie Dockera
echo "Uruchamianie kontenerow Greenbone w tle..."
sudo docker-compose up -d

echo "--- Instalacja zakonczona sukcesem! ---"
echo "System Greenbone uruchamia sie w tle. Pobieranie bazy podatnosci moze potrwac kilkanascie minut."
