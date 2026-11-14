# Piano di implementazione: ritocchi UI

1. **Topbar**: in `pythagoras/static/index.html` si toglie "Pythagoras never grades" (punto verde e divisore compresi); resta il link "Professor ↗".
2. **Logo**: in tutte le pagine (`index`, `interview`, `prof*`) l'icona `g✳` diventa `P` e si toglie il punto finale di "pythagoras." (`.brand-dot`).
3. **Verifica**: `pytest` e controllo delle pagine nel browser.
