# Wykorzystanie agentów sztucznej inteligencji do automatyzacji procesów informacyjnych w branży e-commerce

Repozytorium zawiera kod źródłowy systemu eksperckiego **Agent_MVP**, stworzonego na potrzeby pracy licencjackiej. Aplikacja realizuje zadania z zakresu autonomicznej i inteligentnej automatyzacji procesów posprzedażowych w sektorze e-commerce z wykorzystaniem technologii chmurowych Google Cloud Platform (GCP).

## O projekcie
System został zaprojektowany jako w pełni autonomiczny agent konwersacyjny, którego zadaniem jest wsparcie klienta końcowego oraz personelu e-commerce w analizie statusów zamówień, opóźnień logistycznych oraz problemów z płatnościami. Agent potrafi interpretować surowe, systemowe statusy bazodanowe i przekładać je na naturalny, zrozumiały dla człowieka język biznesowy.

## Architektura i Logika Biznesowa

Implementacja w pliku źródłowym opiera się na zaawansowanych mechanizmach kontroli przepływu informacji:

1. **Zarządzanie sesją i kontekstem:** Wykorzystanie usługi `InMemorySessionService` do utrzymywania ciągłości konwersacji w ramach asynchronicznego strumieniowania (`asyncio`).
2. **Dynamiczna Identyfikacja (Regex):** System automatycznie filtruje zapytania i wychwytuje 32-znakowe, alfanumeryczne identyfikatory zamówień. Wykrycie nowego ID skutkuje natychmiastowym zresetowaniem kontekstu dla bezpieczeństwa danych.
3. **Zabezpieczenia (Guardrails):** 
   * Rygorystyczna walidacja struktury ID zamówienia.
   * Blokada domeny konwersacji wyłącznie do zagadnień e-commerce.
   * Formalny ton w przypadku roszczeń finansowych i jasne informowanie o braku uprawnień do alokacji rekompensat.
   * Unikanie nadmiarowości i żargonu technicznego w komunikatach wyjściowych.

## Środowisko technologiczne
* **Język programowania:** Python 3.10+ (asynchroniczne przetwarzanie `asyncio`)
* **Sercem systemu (LLM):** `gemini-2.5-pro` za pośrednictwem Vertex AI Preview Reasoning Engines
* **Framework integracyjny:** Google ADK (`google.adk.agents`, `AdkApp`)
* **Integracja z danymi (Tooling):** Protokół MCP (`McpToolset`, `StreamableHTTPConnectionParams`) łączący agenta bezpośrednio z Google BigQuery API.
* **Baza danych (Zbiór produkcyjny POC):** `project-5c8e83d8-2504-46c5-afc` (zbiór `agent_AI_ecommerce_poc`).

## Instrukcja uruchomienia w Google Cloud Shell

Projekt został przystosowany do uruchomienia bezpośrednio w środowisku Google Cloud Shell z wykorzystaniem uprawnień zalogowanego użytkownika GCP.

### 1. Klonowanie repozytorium
```bash
git clone https://github.com/szymonsrogosz/automatyzacja-ecommerce-licencjat.git
cd automatyzacja-ecommerce-licencjat
