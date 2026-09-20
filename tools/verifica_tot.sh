#!/bin/bash
# Rulează toate verificările automate și tipărește criteriile de „gata".
# Fără argumente: verifică ../intrebari.js. Cu argumente: fișierele date (ex. nou/*.json).
# Cu --semantic rulează în plus poarta semantică (TypeSafe) — cere TYPESAFE_API_KEY,
# durează ~70 s pentru banca întreagă și consumă tokens, deci nu pornește niciodată singură.
cd "$(dirname "$0")" || exit 1
# Poarta semantică are nevoie de typesafe-sdk, instalat în venv-ul local; pașii 1-4
# n-au dependențe externe și merg cu python3 de sistem.
PY_TS="python3"
[ -x ./.venv-ts/bin/python ] && PY_TS="./.venv-ts/bin/python"
SEMANTIC=0
ARGS=()
for a in "$@"; do
  if [ "$a" = "--semantic" ]; then SEMANTIC=1; else ARGS+=("$a"); fi
done
FISIERE=("${ARGS[@]}"); [ ${#FISIERE[@]} -eq 0 ] && FISIERE=(../intrebari.js)
ok=0
echo "== 1. schemă + unicitate ==";       python3 valideaza.py "${FISIERE[@]}"      || ok=1
echo "== 2. citate verbatim ==";          python3 check_citat.py "${FISIERE[@]}"    || ok=1
echo "== 3. articol + tematică ==";       python3 check_articol.py "${FISIERE[@]}"  || ok=1
echo "== 4. referiri poziționale ==";     python3 check_semantic.py --doar-pozitionale "${FISIERE[@]}" || ok=1
if [ ${#FISIERE[@]} -eq 1 ] && [ "${FISIERE[0]}" = "../intrebari.js" ]; then
  echo "== 5. distribuție pe teste =="; python3 asambleaza.py --raport-din ../intrebari.js || ok=1
fi
if [ $SEMANTIC -eq 1 ]; then
  echo "== 6. poartă semantică (TypeSafe) =="
  "$PY_TS" check_semantic.py "${FISIERE[@]}" || ok=1
fi
[ $ok -eq 0 ] && echo "TOATE VERIFICĂRILE AUTOMATE: TREC" || echo "VERIFICĂRI EȘUATE — vezi mai sus"
exit $ok
