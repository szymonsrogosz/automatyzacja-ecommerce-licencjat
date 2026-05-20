import os
import warnings
import logging

os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("vertexai").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)

import asyncio
import google.auth
import google.auth.transport.requests
import uuid
import sys

from google.adk.agents import llm_agent
from google.adk.sessions import in_memory_session_service
from vertexai.preview.reasoning_engines import AdkApp
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

class AgentClass:
    def __init__(self):
        self.app = None
        self.memory = in_memory_session_service.InMemorySessionService()

    def register_operations(self):
        return {"stream": ["stream_query", "async_stream_query"]}

    def session_service_builder(self):
        return self.memory

    def set_up(self):
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req) 
        
        root_agent = llm_agent.LlmAgent(
            name='Ecom_Final_Pro',
            model='gemini-2.5-pro',
            description='Inteligentny asystent BOK eCommerce.',
            sub_agents=[],
            instruction=(
                'Jesteś profesjonalnym i empatycznym doradcą klienta sklepu eCommerce. TWOJE ZASADY:\n'
                '1. KONTEKST: Zawsze sprawdzaj historię rozmowy. Jeśli znasz ID zamówienia, nie pytaj o nie. '
                'Jeśli użytkownik poda NOWE ID zamówienia, zapomnij o poprzednim i skup się na nowym.\n'
                '2. STATUS "unavailable": Oznacza anulowanie/brak towaru. Poinformuj, że procesujesz zwrot środków, '
                'bo zamówienie nie dotrze. Nie wspominaj o 14 dniach od dostawy.\n'
                '3. JĘZYK I FORMATOWANIE: Używaj wyłącznie języka polskiego. Tłumacz statusy na polski. '
                'Zawsze pogrubiaj ważne dane, takie jak **numery zamówień**, **kwoty** oraz **statusy**, używając składni Markdown.\n'
                '4. BAZA DANYCH: Pracujesz na projekcie project-5c8e83d8-2504-46c5-afc, zbiór agent_AI_ecommerce_poc.\n'
                '5. RABATY, REKLAMACJE I EMOCJE: Jeśli klient jest zdenerwowany, używa wulgaryzmów lub prosi o rabat/rekompensatę, '
                'zachowaj spokój i profesjonalizm. Poinformuj, że jako asystent nie masz uprawnień do przyznawania zniżek. '
                'KRYTYCZNE: Podczas łagodzenia sytuacji NIGDY nie proś klienta o ponowne podanie numeru zamówienia '
                'ani opisywanie problemu, jeśli to zamówienie było już przed chwilą omawiane w historii czatu. '
                'Zawsze odnoś się do obecnego kontekstu.\n'
                '6. INNE ZAMÓWIENIA KLIENTA: Jeśli klient pyta o swoje inne zakupy, a Ty masz już aktywne ID zamówienia, '
                'NIE PROŚ go o kolejne ID. Zamiast tego odpytaj bazę o dane klienta (np. email lub user_id) przypisane do '
                'obecnego zamówienia, a następnie użyj tych danych, by znaleźć w bazie jego pozostałe zamówienia.\n'
                '7. BARIERY OCHRONNE I WALIDACJA (KRYTYCZNE): Prawidłowe ID zamówienia ma 32 znaki. Jeśli użytkownik poda krótkie ID, '
                'NIE ODPYTUJ BAZY. Poproś o poprawne. Jeśli odpytasz bazę o 32-znakowe ID i wynik będzie pusty, powiedz: '
                '"Nie znalazłem zamówienia o tym numerze". Kategorycznie odmawiaj dyskusji na tematy niezwiązane ze sklepem '
                '(historia, polityka, broń). Odpowiadaj wtedy: "Przepraszam, ale pomagam tylko w sprawach Twoich zamówień."'
            ),
            tools=[
                McpToolset(
                    connection_params=StreamableHTTPConnectionParams(
                        url='https://bigquery.googleapis.com/mcp',
                        headers={
                            "Authorization": f"Bearer {creds.token}", 
                            "Content-Type": "application/json"
                        }
                    ),
                )
            ],
        )
        self.app = AdkApp(agent=root_agent, session_service_builder=self.session_service_builder)

    async def stream_query(self, message: str, session_id: str):
        async for chunk in self.app.async_stream_query(message=message, user_id=session_id):
            yield chunk

app_instance = AgentClass()

async def handle_request(query, session_id, current_order_id=None):
    """Obsługuje przesyłanie strumieniowe odpowiedzi od agenta."""
    try:
        has_text = False
      
        if current_order_id:
            enriched_query = f"[Kontekst systemowy: Pamiętaj, że aktualnie omawiane ID zamówienia to {current_order_id}]\nKlient pisze: {query}"
        else:
            enriched_query = query
            
        async for chunk in app_instance.stream_query(enriched_query, session_id=session_id):
            text_chunk = ""
            
            try:
                if isinstance(chunk, dict):
                    parts = chunk.get('content', {}).get('parts', [])
                    for part in parts:
                        if 'text' in part: 
                            text_chunk = part['text']
                elif hasattr(chunk, 'text'):
                    text_chunk = chunk.text
            except Exception:
                pass

            if text_chunk:
                if not has_text:
                    print("\n" + "─" * 20 + " ODPOWIEDŹ AGENTA " + "─" * 20)
                    has_text = True
                print(text_chunk, end="", flush=True)
                
    except Exception as e:
        print(f"\n Wystąpił błąd: {e}")

async def main():
    """Główna pętla interfejsu użytkownika."""
    app_instance.set_up()
    print("\033[92m Połączono z BigQuery. Możesz wpisać zapytanie.\033[0m")
  
    session_id = str(uuid.uuid4())
    is_first = True
    current_order_id = None 
    
    while True:
        if is_first:
            prompt_text = "\n Podaj ID zamówienia: "
        else:
            if current_order_id:
                prompt_text = f"\n\n Jak mogę jeszcze pomóc? (Aktywne ID: {current_order_id[:8]}... | wpisz 'exit' by wyjść): "
            else:
                prompt_text = "\n\n Jak mogę jeszcze pomóc? (wpisz 'exit' by wyjść): "
        
        try:
            user_input = input(prompt_text).strip()
        except EOFError: 
            break

        if user_input.lower() in ['exit']:
            print("\n\033[94m Dziękujemy za kontakt. Zamykanie sesji...\033[0m")
            return 

        if user_input.lower() == 'reset':
            session_id = str(uuid.uuid4())
            is_first = True
            current_order_id = None
            print("\033[93m Sesja zresetowana. Agent zapomniał poprzednie zamówienia.\033[0m")
            continue
            
        if not user_input: 
            continue

        if len(user_input) == 32 and user_input.isalnum():
            current_order_id = user_input

        await handle_request(user_input, session_id, current_order_id)
        is_first = False
        print("\n" + "═" * 58)

if __name__ == "__main__":
    asyncio.run(main())
