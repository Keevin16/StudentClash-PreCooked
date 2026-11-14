# Pythagoras: piano implementativo della Proof of Concept

**Team Pythagoras** · challenge StudentClash, direzione *Assessment* · specifica in [`docs/SPEC.md`](docs/SPEC.md)

## 0. Cosa cambia rispetto alla spec

| Spec originale | PoC Pythagoras |
|---|---|
| Uno studente, colloquio di 10 min | **Colloquio di gruppo**: tutti gli autori del progetto entrano nella stessa *chiamata* con l'agent |
| CLI / dashboard | **Web app**: area professore (prepara, avvia, legge il pacchetto) + stanza di chiamata per gli studenti |
| Report PDF + codice di ML | **Caso pilota: `Leo.pdf`** (Homework 3 "Polimi 2.0", 3 autori, report senza codice) |
| Voce come step finale | **Voce real-time sin dall'inizio**: è il cuore della demo |
| Lingua configurabile | **Inglese** |
| Servizi cloud | **Tutto in locale**: gira su un Mac per la demo finale (§2.1) |
| LLM Claude | **Qualsiasi provider**: basta inserire una chiave (§2.2) |
| Report per studente | **Report unico per il gruppo** |

Il caso pilota sta in `cases/leo/` (ignorato da git: il PDF contiene nomi e matricole). Il syllabus è quello di [Creativity, Science and Innovation](https://dynamicpoli.polimi.it/formazione/passion-in-action/dettaglio/creativity-science-and-innovation) (Passion in Action, prof. Santambrogio). La pagina non elenca learning objectives formali, quindi in `cases/leo/syllabus/syllabus.md` ne abbiamo derivati 5 (problem framing, design, fattibilità, pensiero critico, comunicazione), marcati come non ufficiali.

## 1. Cosa deve dimostrare la PoC

Ipotesi: **un agent vocale, in una chiamata con tutto il gruppo, capisce quanto il gruppo conosce davvero il progetto che presenta, e consegna al professore un unico report di gruppo con prove verificabili.**

| # | Criterio | Come lo misuriamo |
|---|---|---|
| C1 | Domande specifiche del progetto | Ogni topic del piano ha un'àncora in `Leo.pdf` (sezione, tabella, figura) |
| C2 | Il planner trova i punti deboli veri | Trova almeno 4 dei 7 punti della §3 senza che glieli suggeriamo |
| C3 | Partecipa tutto il gruppo | Ogni membro ha almeno il 20% del tempo di parola e risponde ad almeno una domanda diretta |
| C4 | Distingue chi conosce il progetto da chi no | Sessione di controllo: una persona esterna "difende" Leo; deve fermarsi a Bloom ≤ 2 sui topic critici |
| C5 | Ogni affermazione è verificabile | 100% delle evidenze ha timestamp, **nome di chi parla** e citazione presente nella trascrizione |
| C6 | Conversazione naturale | Una domanda per volta rivolta per nome, nessuna interruzione durante le pause, latenza percepita < 1,5 s |

**Fuori scope:** voto, consiglio di 3 LLM, login/SSO, multi-corso, analisi automatica della webcam (solo pochi minuti di video registrato + eventi di perdita del focus), practice mode.

## 2. Architettura

```
 PROFESSORE (browser)                    STUDENTI (browser, cuffie + webcam)
  │ carica syllabus + Leo.pdf              │ link d'invito → consenso → test cam/mic/cuffie
  │ rivede / modifica il piano             │ video: primi X min registrati nel browser (X < 10)
  │ avvia la sessione                      ▼
  ▼                                   ┌──────────────────────────────┐
 ┌───────────────────────┐  token     │  LiveKit server (locale)     │
 │ Web app (Next.js)     │◄──────────►│  1 traccia audio/video       │
 │ /prof /join /room     │  HTTPS     │  PER PARTECIPANTE            │
 │ /package              │  (mkcert)  └──────────────┬───────────────┘
 └──────────┬────────────┘                           │ audio per membro
            │ REST                                   ▼
 ┌──────────▼────────────┐            ┌───────────────────────────────┐
 │ API (FastAPI)         │  avvia ──► │ Agent worker (SDK livekit rtc)│
 │ pythagoras.planner       │            │ VAD + Smart Turn → mlx-whisper│
 │ pythagoras.report        │◄─ stato ───│ turn manager + supervisor     │
 │ storage: cases/<id>/  │  per turno │ talker → Kokoro TTS           │
 └───────────────────────┘            │ WAV per partecipante          │
                                      └───────────────────────────────┘
          planner / supervisor / talker / report ──► pythagoras.llm ──► qualsiasi provider
```

**Perché LiveKit:** con più persone nella stessa chiamata dà **una traccia audio per partecipante**, quindi sappiamo *chi* parla senza diarizzazione. Ha già stanze, webcam e componenti React per la UI. Il motore del boilerplate (`supervisor`, regole Bloom, `report`) resta uguale: cambia solo il "trasporto".

### 2.1 Stack locale

Requisiti: gratis, real-time, nessuna quota che si esaurisce durante la demo. Macchina della demo: Mac M4, 16 GB.

| Pezzo | Scelta | Perché |
|---|---|---|
| Chiamata | **LiveKit server** open source, in locale (`livekit-server --dev`) | Gratis; una traccia per partecipante; WebRTC dal browser |
| HTTPS | **mkcert**: certificato locale per l'IP o hostname del Mac | I browser danno accesso a microfono e webcam solo su HTTPS o `localhost` |
| Agent | **Worker Python custom** sull'SDK `livekit` (rtc): un `AudioStream` per partecipante + il nostro turn manager | L'`AgentSession` di LiveKit Agents segue **un solo** partecipante ([issue #6795](https://github.com/livekit/agents/issues/6795), [#3657](https://github.com/livekit/agents/issues/3657)) |
| Fine turno | **Silero VAD + Smart Turn v3** (ONNX, standalone), con soglia di silenzio di 2,5 s come rete di sicurezza | Smart Turn lavora sull'**audio**: sente intonazione ed esitazioni ("so… uhm"), quindi non interrompe chi sta pensando. È locale, multilingue, BSD-2. Il turn detector di LiveKit lavora sul testo ed è legato ad `AgentSession`, che non usiamo |
| STT | **mlx-whisper**, una trascrizione per enunciato | Gratis, nessuna quota, l'audio non esce dal Mac; ~0,2 s per il modello *small* su M4 |
| TTS | **Kokoro-82M** (Apache-2.0, pacchetto `kokoro`; port MLX se serve più velocità) | Gratis, voci inglesi buone, molto più veloce del tempo reale |
| LLM | **Qualsiasi provider** (§2.2) | Si sceglie con una chiave |
| Web app | Next.js + `@livekit/components-react` | La stanza con video e audio è già pronta |

**Assunzioni della demo:**
- **Tutti usano le cuffie.** Niente eco della voce dell'agent nei microfoni, quindi niente logica anti-eco. La pagina di ingresso chiede di confermarlo.
- **Stessa rete del Mac** (demo in presenza). Per collegamenti da remoto: LiveKit Cloud (free tier) cambiando solo URL e chiavi.
- **Video registrato solo per i primi X minuti** (`VIDEO_MINUTES`, default 5, massimo 9), nel browser di ciascuno (MediaRecorder) e caricato alla fine. L'**audio** invece è registrato tutto dall'agent, perché serve per le evidenze.

### 2.2 LLM indipendente dal provider

Obiettivo: si mette **una chiave qualsiasi** (Anthropic, OpenAI, Google, Mistral, Groq, OpenRouter, o un modello locale con Ollama) e tutto funziona senza toccare il codice.

**Design di `pythagoras/llm.py`:**
- **Due funzioni pubbliche**, invariate rispetto al boilerplate: `parse(role, Schema, system, content)` e `say(system, prompt)`. Planner, supervisor e report non sanno quale provider c'è sotto.
- **Due backend:**
  1. **Anthropic nativo** (SDK `anthropic`), già scritto. Usa PDF nativi e structured outputs.
  2. **OpenAI-compatibile** (SDK `openai` con `base_url`). Copre OpenAI, Google Gemini (endpoint compatibile), Mistral, Groq, OpenRouter, DeepSeek e Ollama in locale.
- **Rilevamento automatico:** all'avvio guarda quale chiave è presente (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, …) e carica il **preset** di quel provider da `pythagoras/providers.toml`. Il preset dice quale modello usare per ogni ruolo (planner, supervisor, talker) e il `base_url`.
- **Override per ruolo:** ad esempio `PYTHAGORAS_TALKER_MODEL=ollama/llama3.1` per avere il talker locale e il resto su un altro provider.

**Come lo rendiamo affidabile con qualsiasi modello:**

| Problema | Soluzione |
|---|---|
| Non tutti i provider supportano lo schema JSON rigoroso | Si usa lo schema JSON quando c'è, altrimenti la modalità JSON. In ogni caso l'output viene **validato con Pydantic**; se non è valido, si ritenta **una o due volte** passando l'errore al modello |
| Non tutti accettano PDF | Il testo viene estratto localmente con `pypdf` (con numeri di pagina, per le àncore); il PDF nativo si usa solo dove è supportato |
| Parametri diversi (effort, thinking, fallback di Anthropic) | Restano **dentro** il backend Anthropic; il backend generico usa solo parametri standard |
| Un modello troppo lento per il talker | `python -m pythagoras check`: una chiamata di prova per ruolo, misura la latenza e avvisa se il talker supera 1 s |
| Errori di rete o di quota durante la demo | Retry con backoff; se il supervisor fallisce, la mossa successiva è "chiedi un esempio concreto", così il colloquio non si blocca |

**Nota sui dati:** il provider lo sceglie chi inserisce la chiave. I free tier (ad esempio Gemini gratis) possono usare i prompt per addestrare i modelli: per i dati di studenti reali serve un piano a pagamento o un modello locale. Il comando `check` lo ricorda quando rileva una chiave di questo tipo.

**Riuso del boilerplate:**
- `planner.py` e `report.py`: invariati nella logica, con lo schema esteso (§5).
- `llm.py`: diventa lo strato provider-agnostico descritto sopra.
- `supervisor.py`: le regole Bloom restano **per topic, a livello di gruppo**. In più sceglie a chi rivolgere la domanda.
- `interview.py` (terminale): diventa un **simulatore di gruppo** per testare le regole senza voce (`Kevin> …`, `Raul> …`).

## 3. Caso pilota: cosa deve trovare il planner in `Leo.pdf`

È il test di accettazione di C2. Non lo diamo al planner: controlliamo se ci arriva da solo.

| # | Punto | Àncora | Livello Bloom atteso |
|---|---|---|---|
| 1 | Incoerenza: "10 di 16 vivono in residenza", ma poco dopo "tutti e 5 in affitto privato (8 di 11 in residenza)", cioè 11 | §4.2 | 4 Analyze |
| 2 | F1 = 0.94 misurato su etichette prodotte da un assistente AI, non da umani: cosa misura davvero? | §4.1 | 5 Evaluate |
| 3 | "Le opzioni di fiducia corrispondono all'answer contract", ma "dice quando non è sicuro" e "una persona può controllare" sono al 7% e al 13% | §4.2, Tab. 2 | 5 Evaluate |
| 4 | Campione di convenienza (n = 16, raccolto nel dormitorio Galileo Galilei, sbilanciato su DSU) usato per scegliere i topic | §4.2 | 4 Analyze |
| 5 | Come funziona il "check che verifica che il passaggio citato supporti l'affermazione"? Non è descritto | §5 | 3 Apply |
| 6 | Riferimento [2] (Moffatt v. Air Canada) in bibliografia ma mai citato nel testo: cosa doveva sostenere? | Riferimenti | 2 Understand |
| 7 | Break-even (1.600-4.000 query/anno): da dove vengono i €5-10 per query gestita da una persona? | §5, Tab. 3 | 4 Analyze |

Domande di ownership, da fare a membri diversi: chi ha scritto lo scraper e il detector (§4.1)? Chi ha progettato il sondaggio (§4.2)? Chi ha fatto la stima dei costi (Tab. 3)?

## 4. Il colloquio di gruppo (design)

1. **Apertura (~1 min):** l'agent dichiara di essere un'AI (AI Act, art. 50), spiega le regole (una domanda per volta, "non so" va bene, nessun voto) e chiede a ciascuno, per nome, quale parte del progetto ha curato. Così otteniamo la **mappa di ownership**.
2. **Domande dirette per nome:** "Raul, in section 4.1…". Le domande su una sezione vanno prima a chi l'ha curata. Il livello Bloom raggiunto è **del gruppo**: dopo una risposta debole, l'agent rilancia a **un altro membro** ("Osama, would you like to add something?") prima di dare un indizio e chiudere il topic.
3. **Rotazione equa:** il turn manager tiene il tempo di parola di ciascuno e sceglie il destinatario della domanda successiva per bilanciarlo. Se risponde una persona diversa da quella interpellata, la risposta viene attribuita a chi ha parlato, e la domanda viene riproposta alla persona originale una volta.
4. **Turni:** l'agent parla solo quando la persona interpellata ha finito (Smart Turn v3, §2.1). Se più persone parlano insieme, l'agent aspetta. L'agent non si interrompe se qualcuno parla mentre lui sta parlando.
5. **Latenza:** appena lo studente finisce, il talker dice subito una frase breve ("Thanks, Raul.") mentre il supervisor valuta la risposta; poi arriva la domanda successiva.
6. **Durata:** circa 5 minuti per membro, quindi **~15 min per 3 persone**, con un budget per topic come nella spec.
7. **Report: unico per il gruppo.** Stessa struttura dell'Output 3 della spec: livello Bloom raggiunto dal gruppo per ogni topic, evidenze con timestamp e citazione (con il nome di chi ha parlato, solo per poterle verificare), incoerenze con il deliverable, domande suggerite per l'orale. Nessuna valutazione per singolo membro.

## 5. Modifiche al boilerplate (✅ fatte, vedi `CONTRIBUTING.md` per lo stato)

- `models.py`:
  - `Participant(id, name, claimed_sections)`.
  - `Move.addressee`.
  - `Turn.speaker_id`.
  - `InterviewPlan.authors`.
  - `TopicState` e `InterviewReport` restano a livello di gruppo.
- `llm.py`: strato provider-agnostico (§2.2) + `providers.toml` + comando `python -m pythagoras check`.
- `supervisor.next_move`:
  - sceglie topic **e** destinatario (ownership + equità del tempo di parola);
  - dopo il primo fallimento rilancia a un altro membro invece di chiedere un esempio concreto;
  - **fix:** con un'incoerenza, prima applica le regole al verdetto della risposta, poi fa il controllo sul deliverable (oggi il verdetto si perde).
- **Stato salvato su disco dopo ogni turno** (`session.json`), non solo alla fine: se qualcosa crasha durante la demo, il colloquio non si perde.
- **Timestamp** misurati dall'inizio della registrazione audio, così "clicca e riascolta" punta al punto giusto.
- `planner.py`: estrae gli autori dal deliverable e le domande di ownership; syllabus opzionale; testo del PDF con numeri di pagina per le àncore.
- `interview.py`: simulatore di gruppo in terminale.
- `tests/test_supervisor.py`: casi di gruppo (rotazione, risposta dalla persona sbagliata, rilancio, fix dell'incoerenza).

## 6. Piano tecnico

Lavoro diviso tra **due persone**: **P1** colloquio live (voce + motore), **P2** preparazione, report e web app. Task, criteri di completamento e punti di sincronizzazione sono in [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Fase 0: fondamenta (mezza giornata; struttura del repo ✅ fatta)
1. `brew install python@3.12` (MLX richiede Python 3.10-3.12), ambiente virtuale, `pip install -e .`.
2. Struttura del repo:
   ```
   pythagoras/          core (già c'è)
   pythagoras/agent/    worker vocale
   pythagoras/api/      FastAPI
   web/              Next.js
   Procfile          livekit-server + api + agent + web (avvio con honcho)
   ```
3. Certificato HTTPS locale con mkcert per l'IP o hostname del Mac.

### Fase 1: core su Leo (P2: LLM e planner; P1: regole di gruppo e simulatore)
4. Strato LLM provider-agnostico (§2.2) e comando `check`; smoke test con almeno due provider diversi.
5. Schema di gruppo in `models.py` (§5).
6. Planner: syllabus opzionale, autori e domande di ownership, testo del PDF con pagine, fase di apertura.
7. **Test di accettazione C2:** il planner su `Leo.pdf` trova almeno 4 dei 7 punti della §3. Il controllo si fa a mano su `plan.json`, con ogni provider che vogliamo supportare.
8. Supervisor: scelta del destinatario, rilancio a un altro membro, fix dell'incoerenza, salvataggio dopo ogni turno.
9. Test offline per i casi di gruppo.
10. Simulatore di gruppo in terminale che usa lo stesso motore.

### Fase 2: spike voce (P1, in parallelo con la fase 1; è il rischio più grosso)
11. `livekit-server --dev` raggiungibile in LAN su HTTPS, più una pagina minima che genera i token.
12. Worker Python con l'SDK `livekit`: entra nella stanza e si iscrive alla traccia audio di ogni partecipante; l'identità del partecipante è il nome dell'autore.
13. Per ogni traccia: Silero VAD, poi Smart Turn v3 (con soglia di silenzio di 2,5 s come rete di sicurezza), poi l'enunciato va in una **coda unica** verso mlx-whisper (MLX usa una GPU sola; va bene perché parla una persona alla volta).
14. Kokoro genera l'audio, pubblicato come traccia dell'agent.
15. Il worker salva un WAV per ogni partecipante, con lo zero dei timestamp all'inizio della registrazione.
16. **Misure:** latenza da fine turno a inizio voce dell'agent, CPU e RAM con 3 persone, qualità della trascrizione inglese con accenti diversi (glossario del deliverable passato a Whisper come `initial_prompt`).
17. Test senza tre persone: l'agent riceve dei WAV registrati come partecipanti finti. Serve anche per provare la demo.

### Fase 3: agent completo (P1, dopo gli step 8 e 16)
18. Turn manager: la mossa scelta passa al talker e poi al TTS; la risposta trascritta passa al supervisor.
19. Frase breve immediata mentre il supervisor valuta (§4.5).
20. Script di apertura (dichiarazione AI, giro di ownership) e di chiusura (ringraziamento, fine del timer).
21. Data message di LiveKit verso il frontend: chi è interpellato, timer, sottotitoli dal vivo.
22. Flag di integrità: il frontend segnala la perdita del focus della scheda, l'agent la aggiunge a `integrity_flags` con il timestamp.

### Fase 4: API (P2)
23. Endpoint FastAPI:

| Metodo | Endpoint | Cosa fa |
|---|---|---|
| `POST` | `/cases` | Carica il deliverable e il syllabus |
| `POST` | `/cases/{id}/plan` | Genera il piano in background (può richiedere 1-2 minuti), con stato da interrogare |
| `GET` / `PUT` | `/cases/{id}/plan` | Il professore legge e modifica il piano |
| `POST` | `/cases/{id}/session` | Crea la stanza, i token per ogni autore e avvia l'agent come sottoprocesso |
| `POST` | `/cases/{id}/video/{participant}` | Riceve i pochi minuti di video registrati da ogni browser |
| `GET` | `/cases/{id}/package` | Restituisce i 3 output, i WAV e i video |

24. Storage su file (`cases/<id>/`): niente database per la PoC.

### Fase 5: web app (P2)
25. Next.js con `@livekit/components-react`.
26. Pagine:
    - `/prof`: upload, revisione e modifica del piano, avvio della sessione, link d'invito;
    - `/join/:id`: lo studente sceglie il proprio nome tra gli autori, dà il consenso (dichiarazione AI e registrazione), conferma le cuffie, prova camera e microfono;
    - `/room/:id`: video dei partecipanti, chi è interpellato, timer, sottotitoli; registrazione video dei primi `VIDEO_MINUTES` minuti;
    - `/package/:id`: PDF incorporato accanto all'Output 2 e all'Output 3; le evidenze sono cliccabili e fanno partire il WAV dal timestamp giusto.

Le fasi 4 e 5 non bloccano niente fino alla fase 3: si sviluppano contro `plan.json` e `session.json` d'esempio.

### Fase 6: report (P2)
27. `report.py` unico di gruppo: le evidenze riportano chi ha parlato e i timestamp sono allineati ai WAV.
28. Controllo C5 con uno script: ogni evidenza deve avere un timestamp e una citazione presente davvero nella trascrizione. Così il controllo non dipende dal modello.

### Fase 7: valutazione e demo
29. Sessione pilota con i 3 autori di Leo, poi sessione di controllo con una persona esterna. Si compilano le tabelle C3 e C4.
30. Preparazione della demo: piano già generato, hotspot dedicato, modalità solo testo come piano B, prova generale con i WAV registrati.

### Percorso critico
**0 → 1 e 2 in parallelo → 3 → 6 → 7.** Se lo spike vocale (step 11-16) non regge per latenza o carico sul Mac, le alternative pronte sono: modello Whisper più piccolo, talker locale, LiveKit Cloud per la chiamata.

## 7. Decisioni

- Lingua: **inglese**.
- Syllabus: *Creativity, Science and Innovation* (learning objectives derivati, non ufficiali; da confermare con il docente se serve).
- Server: **in locale**, solo per la demo finale, HTTPS con **mkcert**.
- Chiamata: **cuffie obbligatorie**; video registrato solo per i primi **X < 10 minuti**; audio registrato tutto.
- Fine turno: **Silero VAD + Smart Turn v3**.
- STT/TTS: **locali e gratuiti** (mlx-whisper, Kokoro).
- LLM: **qualsiasi provider**, scelto dalla chiave inserita.
- Stato salvato **dopo ogni turno**.
- Frontend: **Next.js**.
- Durata: **15 min** per 3 persone.
- Report: **unico per il gruppo**.
- Ruoli: li decidono gli studenti.

## 8. Rischi

| Rischio | Mitigazione |
|---|---|
| Più persone parlano insieme | Tracce separate per membro; l'agent aspetta il silenzio di tutti; la persona interpellata ha la precedenza |
| Un membro domina la conversazione | Rotazione basata sul tempo di parola; domande dirette per nome |
| STT su accenti e termini locali | Glossario dal deliverable passato a Whisper come `initial_prompt`; nel pacchetto il professore può riascoltare l'audio |
| Il Mac non regge 3 STT + TTS + LLM insieme | Misurato nello spike (step 16); fallback: modello Whisper più piccolo o STT solo sul membro che sta parlando |
| Un provider LLM restituisce output non validi o è lento | Validazione Pydantic con retry; comando `check` prima della demo; talker su un modello veloce |
| Latenza del supervisor | Frase breve immediata; il supervisor lavora mentre il talker parla |
| Rete della demo (Wi-Fi dell'aula blocca WebRTC) | Hotspot dedicato; piano B: LiveKit Cloud free tier |
| Qualcuno senza cuffie | La pagina di ingresso chiede di confermarle; altrimenti l'agent può trascrivere la propria voce |
| Dati personali (nomi, matricole, audio, video) | `cases/*` e le registrazioni sono fuori da git; consenso esplicito all'ingresso; video limitato a pochi minuti; provider LLM a pagamento o locale per dati reali |
| Il planner inventa punti deboli | Obbligo di citazione; test di accettazione della §3 |
| AI Act (alto rischio, Allegato III) | Nessun voto, flag solo come prompt per il professore, nessuna emotion recognition |
