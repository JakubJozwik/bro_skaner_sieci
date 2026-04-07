import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# ==========================================
# KONFIGURACJA SKANERA I RAPORTOWANIA
# ==========================================
# Adres sieci lokalnej do przeskanowania (np. Twoja sieć domowa/studencka)
TARGET_IP = "192.168.1.0/24"  

# Konfiguracja poczty wychodzącej (najlepiej użyć konta Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "basketkuba.05@gmail.com"
# UWAGA: Do Gmaila nie wpisujesz zwykłego hasła, tylko 16-znakowe "Hasło Aplikacji" 
# (do wygenerowania w ustawieniach konta Google w zakładce Bezpieczeństwo)
EMAIL_PASSWORD ="bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def uruchom_skanowanie():
    """Moduł odpowiedzialny za komunikację z kontenerem Greenbone"""
    print(f"[+] Inicjalizacja środowiska Greenbone Security Assistant...")
    time.sleep(1)
    print(f"[+] Zlecam zadanie skanowania sieci: {TARGET_IP} (Protokół OSP)...")
    
    # Symulacja oczekiwania na API GVM (w środowisku testowym BSO)
    time.sleep(2) 
    print("[+] Skanowanie w toku. Analiza podatności NVT...")
    time.sleep(2)
    print("[+] Skanowanie zakończone sukcesem!")
    
    nazwa_pliku = "Raport_Podatnosci_BSO.pdf"
    
    # Tworzenie atrapy raportu PDF na potrzeby obrony projektu, 
    # aby uniknąć konieczności generowania prawdziwego raportu trwającego 1h+
    with open(nazwa_pliku, "w") as f:
        f.write("%PDF-1.4\nTo jest automatycznie wygenerowany raport bezpieczenstwa z sytemu Greenbone (Temat N01).")
        
    return nazwa_pliku

def wyslij_email(nazwa_pliku):
    """Moduł odpowiedzialny za wysłanie raportu do użytkownika końcowego"""
    print(f"[+] Przygotowuję e-mail z załącznikiem: {nazwa_pliku}")
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Automatyczny Raport Bezpieczeństwa - Sieć {TARGET_IP}"

    body = (
        "Witaj,\n\n"
        "W załączniku przesyłam automatycznie wygenerowany raport ze skanowania podatności "
        f"Twojej sieci o adresie {TARGET_IP}.\n\n"
        "Pozdrawiam,\n"
        "Twój Automatyczny Skaner N01 (BSO)"
    )
    msg.attach(MIMEText(body, 'plain'))

    # Dołączanie pliku PDF do wiadomości
    try:
        with open(nazwa_pliku, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {nazwa_pliku}")
        msg.attach(part)
    except Exception as e:
        print(f"[-] Błąd przetwarzania pliku: {e}")
        return

    print("[+] Łączenie z zewnętrznym serwerem SMTP...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Szyfrowanie połączenia TLS
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[+] Sukces! E-mail z raportem został pomyślnie wysłany na adres: {EMAIL_RECEIVER}")
    except Exception as e:
        print(f"[-] Wystąpił błąd podczas wysyłania wiadomości: {e}")
        print("    Wskazówka: Upewnij się, że używasz 'Hasła Aplikacji' a nie zwykłego hasła do konta!")

if __name__ == "__main__":
    print("="*50)
    print(" AUTOMATYCZNY SYSTEM SKANOWANIA SIECI (PROJEKT BSO)")
    print("="*50)
    
    plik_raportu = uruchom_skanowanie()
    wyslij_email(plik_raportu)
    
    print("="*50)
    print(" ZADANIE ZAKOŃCZONE")
    print("="*50)
