import os
import warnings

os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

import logging
import asyncio
import google.auth
import google.auth.transport.requests
import uuid
import sys
import re

from google.adk.agents import llm_agent
from google.adk.sessions import in_memory_session_service
from vertexai.preview.reasoning_engines import AdkApp
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("vertexai").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)

class EcomAgentManager:
    def __init__(self):
        self.app = None
        self.memory = in_memory_session_service.InMemorySessionService()

    def register_operations(self):
        return {"stream": ["stream_query", "async_stream_query"]}

    def session_service_builder(self):
        return self.memory

    def set_up(self):
        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req) 
        except Exception as e:
            logging.error(f"Błąd autoryzacji GCP: {e}")
            sys.exit(1)
            
        root_agent = llm_agent.LlmAgent(
            name='Agent_MVP',
            model='gemini-2.5-pro',
            description='Autonomiczny system ekspercki wspomagający procesy obsługi posprzedażowej w sektorze e-commerce.',
            sub_agents=[],
            instruction=(
                "Działasz jako w pełni autonomiczny system ekspercki, którego głównym zadaniem jest wsparcie "
                "oraz automatyzacja obsługi procesów posprzedażowych w sektorze e-commerce.\n\n"
                "Wytyczne operacyjne i proceduralne:\n\n"
                "1. Zarządzanie przepływem konwersacji i identyfikacja:\n"
                "   - Czekaj na pytanie użytkownika. Jeśli pytanie dotyczy konkretnego zamówienia, a użytkownik NIE podał "
                "jeszcze 32-znakowego, alfanumerycznego identyfikatora (ID), grzecznie poproś o jego podanie, zanim udzielisz odpowiedzi.\n"
                "   - Kiedy otrzymasz poprawne ID, odpowiedz STRICTE na zadane pytanie. NIE wypisuj wszystkich dostępnych informacji "
                "o zamówieniu, chyba że użytkownik wyraźnie o to poprosi.\n"
                "   - Rejestracja nowego identyfikatora skutkuje bezwarunkowym zresetowaniem dotychczasowego kontekstu dla bieżącego wątku.\n\n"
                "2. Środowisko bazodanowe i analiza danych:\n"
                "   - Przestrzeń robocza systemu jest ściśle ograniczona do bazy danych 'project-5c8e83d8-2504-46c5-afc' "
                "(zbiór: 'agent_AI_ecommerce_poc').\n"
                "   - Koreluj aktywny identyfikator zamówienia z odpowiednimi atrybutami, dokonując agregacji powiązanych rekordów.\n\n"
                "3. Standaryzacja logiki biznesowej:\n"
                "   - Proaktywnie analizuj każdy techniczny status zamówienia (np. w systemie logistycznym lub magazynowym). Wywnioskuj jego rzeczywiste znaczenie biznesowe (np. opóźnienie w transporcie, braki w magazynie, odrzucenie płatności) i na tej podstawie sformułuj adekwatny, zrozumiały komunikat dla klienta. Unikaj surowego, systemowego żargonu.\n"
                "   - Rygorystycznie selekcjonuj przekazywane informacje. Zanim wygenerujesz odpowiedź, przeprowadź wewnętrzną analizę tego, co jest faktycznie istotne w danym kontekście. Kategorycznie unikaj nadmiarowości – nie podawaj danych (np. przewidywanej daty dostawy), jeśli kłócą się one z obecnym statusem (np. braki magazynowe, anulowanie) lub jeśli klient o nie nie pytał. Odpowiadaj zwięźle i na temat.\n"
                "   - Podczas obsługi roszczeń zachowaj sformalizowany, obiektywny ton. Informuj o braku uprawnień do alokacji rekompensat.\n\n"
                "4. Ograniczenia i zabezpieczenia systemowe (Guardrails):\n"
                "   - Walidacja: Identyfikator zamówienia musi składać się z DOKŁADNIE 32 znaków alfanumerycznych. Wykrycie anomalii "
                "przerywa proces i generuje żądanie korekty.\n"
                "   - Brak referencji w bazie danych sygnalizuj klauzulą: 'Zamówienie o podanym identyfikatorze nie zostało odnalezione w systemie.'\n"
                "   - Domenę interakcji zawęź wyłącznie do wsparcia procesów e-commerce.\n\n"
                "5. Formatowanie strumienia wyjściowego:\n"
                "   - Odpowiedzi formułuj z poprawną polszczyzną, dbając o interpunkcję i ortografię.\n"
                "   - Tłumacz techniczne statusy na język zrozumiały dla klienta i formatuj tekst w czytelnej formie."
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

app_instance = EcomAgentManager()

async def handle_request(query: str, session_id: str, current_order_id: str = None):
    full_response = ""
    try:
        has_text = False
        
        if current_order_id:
            enriched_query = f"[Kontekst systemowy: Aktywny identyfikator: {current_order_id}]\nTreść zapytania: {query}"
        else:
            enriched_query = query
            
        async for chunk in app_instance.stream_query(enriched_query, session_id=session_id):
            text_chunk = ""
            
            if isinstance(chunk, dict):
                parts = chunk.get('content', {}).get('parts', [])
                for part in parts:
                    if 'text' in part: 
                        text_chunk = part['text']
            elif hasattr(chunk, 'text'):
                text_chunk = chunk.text

            if text_chunk:
                if not has_text:
                    print("\n" + "-" * 60)
                    has_text = True
                
                clean_chunk = text_chunk.replace("**", "")
                print(clean_chunk, end="", flush=True)
                full_response += clean_chunk
                
    except Exception as e:
        logging.error(f"Błąd przetwarzania żądania: {e}")
        print(f"\n[BŁĄD] Wystąpił problem podczas obsługi zapytania. Sprawdź logi systemowe.")
        
    return full_response

async def main():
    print("Trwa inicjalizacja środowiska systemowego...")
    app_instance.set_up()
    print("Nawiązano połączenie z bazą danych.\n" + "=" * 60)
    
    session_id = str(uuid.uuid4())
    is_first = True
    current_order_id = None 
    
    while True:
        if is_first:
            prompt_text = "\n> W czym mogę pomóc?: "
        else:
            if current_order_id:
                prompt_text = f"\n\n> Kolejne pytanie (Aktywne ID: {current_order_id[:8]}... | Wpisz 'exit' by zakończyć): "
            else:
                prompt_text = "\n\n> Podaj numer zamówienia (Wpisz 'exit' by zakończyć): "
        
        try:
            user_input = input(prompt_text).strip()
        except EOFError: 
            break
        
        if user_input.lower() in ['exit']:
            print("\nZakończenie pracy systemu.")
            break 

        if user_input.lower() == 'reset':
            session_id = str(uuid.uuid4())
            is_first = True
            current_order_id = None
            print("Parametry sesji zostały przywrócone do ustawień początkowych.")
            continue
            
        if not user_input: 
            continue

        match = re.search(r'\b[a-zA-Z0-9]{32}\b', user_input)
        if match:
            current_order_id = match.group(0)

        response_text = await handle_request(user_input, session_id, current_order_id)
        
        if response_text and "nie zostało odnalezione" in response_text:
            current_order_id = None

        is_first = False
        print("\n\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
