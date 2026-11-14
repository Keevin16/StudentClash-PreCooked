# Piano di implementazione: voce e fine risposta

## 1. La risposta finisce solo con "I'm done"

Oggi il server chiude la risposta da solo dopo una pausa (Silero VAD + Smart Turn, 1-2,5 s di silenzio): una pausa per pensare interrompe il team.

1. `pythagoras/voice.py`: il `TurnDetector` del WebSocket non chiude più il turno da solo (silenzio illimitato, Smart Turn spento). La risposta si chiude solo col messaggio `finish`, cioè il pulsante "I'm done" o la barra spaziatrice. Resta il tetto di sicurezza `MAX_ANSWER_S` (120 s).
2. `pythagoras/static/interview.js` e `interview.html`: i testi non dicono più "it notices when you've finished" ma "press I'm done".
3. `scripts/smoke.py`: lo studente sintetico, finito di parlare, manda `finish` come farebbe il pulsante.
4. Verifica: `pytest` e `scripts/smoke.py` (intervista parlata completa).

## 2. Voce sgranata su Firefox / Zen (non in questo giro)

L'audio generato dal server è pulito (24 kHz, nessun clipping): il degrado avviene nel browser quando il microfono è aperto con la cancellazione dell'eco. Su richiesta non si adatta per Firefox; per la demo usare Chrome.
Se servirà: aprire il microfono con `echoCancellation: false` (l'intervista è già half-duplex: il microfono non invia audio mentre Pythagoras parla).

## 3. Come viene valutata la risposta (nessuna modifica)

Ogni risposta è giudicata subito, durante l'intervista: dopo la trascrizione `supervisor.py` (modello judge) confronta la risposta con i punti attesi del piano e decide la mossa successiva (salire di livello, approfondire, dare un aiuto, cambiare topic); `talker.py` formula la frase. Il piano con domande e punti attesi è preparato prima da `planner.py`; il report finale per il professore (`report.py`) arriva dopo la fine.
