#!/bin/bash
set -euo pipefail

# Wymagane uruchomienie jako root
if [ "$EUID" -ne 0 ]; then
  echo "Skrypt musi być uruchomiony jako root (użyj sudo)."
  exit 1
fi

echo "--- Instalacja systemu skanowania N01 (Greenbone + Python) ---"

echo "1/7 Czyszczenie starych wersji Dockera..."
apt-get remove -y docker.io docker-compose docker-doc podman-docker containerd runc >/dev/null 2>&1 || true

echo "2/7 Instalacja narzędzi (curl, python, cron)..."
apt-get update
apt-get install -y curl python3 python3-pip cron

# Instalacja gvm-tools
pip3 install gvm-tools --break-system-packages || pip3 install gvm-tools

echo "3/7 Instalacja najnowszego Dockera..."
curl -fsSL https://get.docker.com | sh

echo "4/7 Przygotowanie katalogu /opt/bso_skaner..."
DIR="/opt/bso_skaner"
mkdir -p "$DIR"
cd "$DIR"

echo "5/7 Pobieranie compose.yaml (Greenbone)..."
curl -f -sL "https://raw.githubusercontent.com/greenbone/docs/main/src/_static/compose.yaml" -o compose.yaml

# Podmiana portu panelu webowego z 9392 na 8085 w celu zachowania spójności z dokumentacją projektową
sed -i 's/9392:80/8085:80/g' compose.yaml

echo "6/7 Pobieranie skryptu skanera..."
curl -f -sL "https://raw.githubusercontent.com/JakubJozwik/bro_skaner_sieci/main/skaner.py" -o skaner.py
chmod +x "$DIR/skaner.py"

echo "7/7 Konfiguracja .env (dane e-mail i zakres skanowania)..."
ENV_FILE="$DIR/.env"

# Jeśli zmienne nie są podane w środowisku — zapytaj (z /dev/tty, bo skrypt może być przekazywany potokiem)
if [ -z "${EMAIL_SENDER:-}" ]; then
  read -rp "Podaj EMAIL_SENDER (np. Gmail): " EMAIL_SENDER </dev/tty
fi
if [ -z "${EMAIL_PASSWORD:-}" ]; then
  read -rsp "Podaj EMAIL_PASSWORD (hasło aplikacji): " EMAIL_PASSWORD </dev/tty
  echo
fi
if [ -z "${EMAIL_RECEIVER:-}" ]; then
  read -rp "Podaj EMAIL_RECEIVER: " EMAIL_RECEIVER </dev/tty
fi
if [ -z "${TARGET_IP:-}" ]; then
  read -rp "Podaj TARGET_IP (np. 127.0.0.1): " TARGET_IP </dev/tty
fi

cat > "$ENV_FILE" <<EOF
EMAIL_SENDER=${EMAIL_SENDER}
EMAIL_PASSWORD=${EMAIL_PASSWORD}
EMAIL_RECEIVER=${EMAIL_RECEIVER}
TARGET_IP=${TARGET_IP}
GVM_USER=admin
GVM_PASSWORD=admin
PATH_TO_SOCKET=/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EOF

echo "Uruchamianie Greenbone..."
docker compose -f compose.yaml up -d

echo "Czekam na gvmd socket..."
SOCKET_PATH="/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock"
until [ -S "$SOCKET_PATH" ]; do
  sleep 10
done

echo "Ustawianie hasła admin (w tle)..."
# Używamy || true, aby skrypt w Bashu NIGDY się tu nie zatrzymał, nawet jeśli baza jeszcze wstaje.
# Domyślnie kontenery Community i tak mają hasło admin/admin, więc ten krok to tylko formalność.
docker compose -f compose.yaml exec -T gvmd gvmd --user=admin --new-password="admin" >/dev/null 2>&1 || true

echo "Konfiguracja Cron (co niedzielę 2:00)..."
CRON_JOB="0 2 * * 0 /bin/bash -lc 'set -a; source $DIR/.env; set +a; /usr/bin/python3 $DIR/skaner.py >> $DIR/skaner.log 2>&1'"
(crontab -l 2>/dev/null | grep -v "skaner.py" || true; echo "$CRON_JOB") | crontab - || true

echo "--- Instalacja zakończona ---"
echo "Uwaga: pobieranie baz NVT może trwać 30–120 minut."
echo "Test ręczny: sudo /usr/bin/python3 $DIR/skaner.py"
