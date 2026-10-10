# Convers+ — patch nazw Menu głównego na bazie BT Audio V5.2

Dokument opisuje zmianę dwóch polskich etykiet w zweryfikowanym firmware Ford Convers+ 1412-FL. Repozytorium nie zawiera firmware Forda — przechowujemy wyłącznie opis patcha i metodę odtworzenia.

## Zmiana

| Oryginał | Nowa nazwa |
|---|---|
| `Zmieniacz płyt CD` | `Płyta CD` |
| `wejście Auxiliary` | `Multimedia USB/BT` |

Każda etykieta występuje w bazie trzy razy. Zmieniono wszystkie wystąpienia.

## Właściwa baza

Patch należy wykonywać wyłącznie na pliku `CS7T-14C026-CD.vbf` z przygotowanej wersji Bluetooth Audio V5.2.

- wejściowy SHA-256 V5.2: `4553f72f4a2527b890b92c08be5ab3d4c1f69c2c2926bdce6179acab143af9c7`
- wynikowy SHA-256 po zmianie etykiet: `21058ce5f64949e7926e2225eda00c06b43e5308ecd77a651f5ca0f96a631d49`
- bazowe offsety CD: `0x924F7`, `0x926B4`, `0x93F1F`
- bazowe offsety AUX: `0x94199`, `0x94237`, `0xCEACD`

V5.2 zawiera wcześniejsze zmiany Bluetooth: centrowanie względem osi `X=297` oraz kolejność `wykonawca → tytuł → album` ze stałymi pozycjami `Y=120`, `Y=143`, `Y=166`.

## Kontrola VBF

- CRC16 bloku: `0x4249`
- `file_checksum` CRC32: `0x5D488907`
- liczba zmienionych bajtów względem V5.2: `103`

Patch zachowuje strukturę VBF i długość pliku. Dla krótszego `Płyta CD` używa dopełnienia w obrębie istniejącego pola.

## Procedura

1. Zachowaj oryginalny CD, ED, SBL i EEPROM.
2. Zweryfikuj SHA-256 wejściowego pliku V5.2.
3. Zastosuj skrypt patchujący na dokładnie tej bazie.
4. Zweryfikuj wynikowy SHA-256 oraz checksumy VBF.
5. Nie mieszaj plików CD/ED/AA z innymi wersjami.
6. Do licznika użyj stabilnego zasilania i wyłącznie wcześniej sprawdzonej procedury.

Plik AA/SBL pozostaje niezmieniony. V5.2 nie wymaga ponownego programowania ED. Firmware jest nieoficjalną modyfikacją i jego flashowanie wykonujesz na własne ryzyko.