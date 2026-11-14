# Piano di implementazione: Galileo → Pythagoras

Obiettivo: rinominare il progetto da "Galileo" a "Pythagoras" ovunque, senza cambiare il comportamento.

## Passi

1. **Package Python**: `galileo/` → `pythagoras/` (`git mv`, storia preservata). Avvio: `python -m pythagoras serve`.
2. **Testi, UI e docs**: sostituzione case-preserving (`galileo`→`pythagoras`, `Galileo`→`Pythagoras`, `GALILEO`→`PYTHAGORAS`) in codice, HTML/JS/CSS, test, `README.md`, `CLAUDE.md`, `PLAN.md`, `docs/`.
3. **Configurazione**: `pyproject.toml` (nome progetto, `packages.find`, `package-data`), variabili d'ambiente `GALILEO_*` → `PYTHAGORAS_*` in `.env.example` e nel codice, cookie `galileo_prof` → `pythagoras_prof`, worklet `GalileoPCM` → `PythagorasPCM`.
4. **Eccezione voluta**: in `PLAN.md` il "dormitorio Galileo Galilei" resta così: è un luogo reale, non il nome del progetto.
5. **Verifica**: `git grep -i galileo` restituisce solo l'eccezione sopra; `pytest` passa; `PYTHAGORAS_FAKE_LLM=1 python -m pythagoras check` gira.
6. **Integrazione**: commit e push, poi ripetizione della verifica.

## Migrazione per chi ha già un ambiente

- Aggiornare `.env`: rinominare ogni `GALILEO_*` in `PYTHAGORAS_*`.
- Reinstallare il pacchetto: `pip install -e ".[voice,dev]"` (il vecchio egg-info `galileo` può essere cancellato).
- Il login professore usa un nuovo cookie: serve rifare il login.
