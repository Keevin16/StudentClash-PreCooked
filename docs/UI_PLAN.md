# Piano di implementazione: ritocchi UI

1. **Topbar**: in `pythagoras/static/index.html` si toglie "Pythagoras never grades" (punto verde e divisore compresi); resta il link "Professor ↗".
2. **Logo**: in tutte le pagine (`index`, `interview`, `prof*`) l'icona `g✳` diventa `P` e si toglie il punto finale di "pythagoras." (`.brand-dot`).
3. **Testo più grande**: in `pythagoras/static/room.css` (pagine team: upload e intervista, dove i testi vanno da 7 a 12 px) ogni `font-size` in px cresce del 15% (minimo +1 px). Le pagine professore (`app.css`) hanno già testi 13-17 px e restano uguali.
4. **Verifica**: `pytest` e controllo delle pagine nel browser.
