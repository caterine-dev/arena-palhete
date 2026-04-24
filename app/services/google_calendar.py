import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Escopo de permissão para ler e escrever na agenda
SCOPES = ['https://www.googleapis.com/auth/calendar']

# AQUI VOCÊ VAI COLOCAR O SEU EMAIL DO GOOGLE OU O ID DO CALENDÁRIO COMPARTILHADO
CALENDAR_ID = 'arenapalhete@gmail.com' 

def get_calendar_service():
    """Lê o arquivo JSON com a chave secreta e conecta no Google."""
    creds = None
    # O arquivo deve ficar na pasta raiz do seu projeto (junto com run.py)
    key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credenciais_google.json')
    
    if os.path.exists(key_path):
        creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    else:
        print("⚠️ Arquivo credenciais_google.json não encontrado na raiz do projeto!")
        return None

def criar_evento(reserva, cliente_nome):
    """Cria o bloco colorido na agenda do Google."""
    service = get_calendar_service()
    if not service: return None

    try:
        # O Google exige o formato de data ISO com Fuso Horário de Brasília (-03:00)
        inicio_iso = f"{reserva.data.isoformat()}T{reserva.hora_inicio.isoformat()}-03:00"
        fim_iso = f"{reserva.data.isoformat()}T{reserva.hora_fim.isoformat()}-03:00"

        evento = {
            'summary': f'Arena: {cliente_nome}',
            'description': f'Reserva: {reserva.tipo.upper()}\nStatus: {reserva.status.upper()}',
            'start': {'dateTime': inicio_iso, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': fim_iso, 'timeZone': 'America/Sao_Paulo'},
            'colorId': '11', # Cor vermelha no Google Calendar
        }

        # Dispara o evento para o Google
        evento_criado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
        return evento_criado.get('id')

    except Exception as e:
        print(f"❌ Erro ao criar evento no Google Calendar: {e}")
        return None