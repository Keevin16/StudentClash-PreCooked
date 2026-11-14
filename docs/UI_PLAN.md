# Piano di implementazione: ritocchi UI

1. **Topbar**: in `pythagoras/static/index.html` si toglie "Pythagoras never grades" (punto verde e divisore compresi); resta il link "Professor ↗".
2. **Logo**: in tutte le pagine (`index`, `interview`, `prof*`) l'icona `g✳` diventa `P` e si toglie il punto finale di "pythagoras." (`.brand-dot`).
3. **Verifica**: `pytest` e controllo delle pagine nel browser.

## Look "Refined" (proposta A)

Obiettivo: testi leggibili anche da lontano senza cambiare il layout.

1. In coda a `room.css`, dentro `@media (min-width:701px)` (i telefoni restano come prima): gerarchia tipografica con minimo 14 px, grigi con contrasto AA, domanda 26 px, timer 30 px, stato dell'agente 20 px, profondità 24 px, titolo upload 56 px; da 1550 px in su gli elementi chiave crescono ancora (domanda 36 px, timer 40 px).
2. Pagina di caricamento: la card demo sale sopra la citazione, con il pulsante verde pieno visibile senza scorrere.
3. `interview.html`: tolto lo stile inline del `#mic-heard`, ora gestito da `room.css`.
4. Verifica: screenshot a 1280×720, 1920×1080 e 390 px; `pytest`.
