#!/bin/bash
# Rulează toate verificările automate și tipărește criteriile de „gata".
# Fără argumente: verifică ../intrebari.js. Cu argumente: fișierele date (ex. nou/*.json).
cd "$(dirname "$0")" || exit 1
FISIERE=("$@"); [ ${#FISIERE[@]} -eq 0 ] && FISIERE=(../intrebari.js)
ok=0
echo "== 1. schemă + unicitate ==";     python3 valideaza.py "${FISIERE[@]}"      || ok=1
echo "== 2. citate verbatim ==";        python3 check_citat.py "${FISIERE[@]}"    || ok=1
echo "== 3. articol + tematică ==";     python3 check_articol.py "${FISIERE[@]}"  || ok=1
if [ ${#FISIERE[@]} -eq 1 ] && [ "${FISIERE[0]}" = "../intrebari.js" ]; then
  echo "== 4. distribuție pe teste =="; python3 asambleaza.py --raport-din ../intrebari.js || ok=1
fi
[ $ok -eq 0 ] && echo "TOATE VERIFICĂRILE AUTOMATE: TREC" || echo "VERIFICĂRI EȘUATE — vezi mai sus"
exit $ok
