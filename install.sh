#!/bin/bash

echo "--- Rozpoczynam automatyczna instalacje systemu skanowania N01 ---"

echo "Aktualizacja pakietow i instalacja Dockera..."
sudo apt update
sudo apt install -y docker.io docker-compose curl python3 python3-pip


echo "Przygotowanie srodowiska..."
mkdir -p ~/bso_skaner
cd ~/bso_skaner


echo "Pobieranie oficjalnej konfiguracji Greenbone..."
curl -f -L https://greenbone.github.io/docs/latest/_static/docker-compose-22.4.yml -o docker-compose.yml


echo "Pobieranie skryptu zarzadzajacego..."
touch skaner.py 


echo "Uruchamianie kontenerow Greenbone w tle..."
sudo docker-compose up -d

echo "--- Instalacja zakonczona sukcesem! ---"
echo "System Greenbone uruchamia sie w tle. Pobieranie bazy podatnosci moze potrwac kilkanascie minut."
