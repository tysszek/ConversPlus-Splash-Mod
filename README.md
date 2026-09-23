# Ford Convers+ Splash Mod

Narzędzia i dokumentacja do podmiany grafiki startowej `Ford / FordConvers+` w liczniku Ford Convers+.

Projekt powstał na podstawie analizy firmware:

- `CS7T-14C026-ED.vbf`
- `CS7T-14C026-CD.vbf`

Dla analizowanej wersji poliftowej grafika startowa ma **400×198 px**, jest zapisana jako **8-bit indexed** i skompresowana prostym **RLE**.

> [!WARNING]
> Modyfikacja firmware zawsze wiąże się z ryzykiem unieruchomienia licznika. Zrób kopię oryginalnych plików i upewnij się, że masz możliwość przywrócenia fabrycznego `ED`.
>
> Domyślne offsety w tych skryptach są przeznaczone dla przeanalizowanego `CS7T-14C026-ED`. Inny numer softu może mieć inne adresy.

## Co znajduje się w repozytorium

```text
ConversPlus-Splash-Mod/
├── README.md
├── requirements.txt
├── LICENSE
├── palettes/
│   └── cs7t_theme_observed.json
└── tools/
    ├── extract_splash.py
    ├── encode_splash.py
    └── patch_ed.py
```

Repozytorium **nie zawiera firmware Forda**. Użytkownik pracuje na własnych plikach VBF.

## Najważniejsze ustalenia

Dla analizowanego `CS7T-14C026-ED.vbf`:

```text
IMAGE FRAME : 0x08BAEC
RLE DATA    : 0x08BAF8
DESCRIPTOR  : 0x08EFBC

width       : 400
height      : 198
stride      : 400
```

Nagłówek `IMAGE FRAME` ma 12 bajtów:

```text
00 00 00 FF 01 00 00 00 00 00 00 00
```

Po dekompresji obraz musi mieć dokładnie:

```text
400 × 198 = 79 200 pikseli
```

## Instalacja

```bash
pip install -r requirements.txt
```

## Wydobycie oryginalnego splasha

```bash
python tools/extract_splash.py CS7T-14C026-ED.vbf \
  --palette palettes/cs7t_theme_observed.json \
  --out-dir extracted
```

Skrypt odczytuje descriptor, pobiera adres `FRAME` i `DATA`, dekoduje RLE, sprawdza liczbę pikseli i zapisuje podglądy oraz indeksy.

## Przygotowanie własnej grafiki

```bash
python tools/encode_splash.py moje_auto.png \
  --palette palettes/cs7t_theme_observed.json \
  --out-dir encoded
```

Skrypt dopasowuje obraz do `400×198`, mapuje RGB do indeksów palety, kompresuje do RLE i wykonuje test round-trip.

## Format RLE

Powtarzające się piksele:

```text
<count> <value>
```

Dane literalne:

```text
00 <length> <pixel1> <pixel2> ...
```

## Relokacja grafiki

Oryginalny obszar danych RLE ma około 13,5 kB. W analizowanym ED znaleziono duży pusty obszar od około `0x120000`, dlatego nowy splash można umieścić jako:

```text
FRAME = 0x120000
DATA  = 0x12000C
```

W descriptorze:

```text
30 08 BA F8    ->    30 12 00 0C
30 08 BA EC    ->    30 12 00 00
```

## Patchowanie ED

```bash
python tools/patch_ed.py \
  CS7T-14C026-ED.vbf \
  encoded/splash_frame.bin \
  CS7T-14C026-ED_SPLASH.vbf
```

Skrypt sprawdza pusty obszar, wstawia frame, aktualizuje wskaźniki, przelicza checksumy VBF i wykonuje audyt integralności.

## Checksumy VBF

Dla przeanalizowanego pliku potwierdzono:

- końcowy CRC16: CRC-16/CCITT, init `0xFFFF`, zakres od file offset `0x426` do dwóch ostatnich bajtów,
- `file_checksum`: CRC32 od file offset `0x41E` do końca pliku po wcześniejszym zapisaniu nowego CRC16.

## Co trzeba modyfikować

Dla samej podmiany splasha zmieniany jest:

```text
CS7T-14C026-ED.vbf
```

Nie trzeba modyfikować:

```text
CS7T-14C026-CD.vbf
7M2T-14C025-AA.vbf
```

## Audyt przed flashowaniem

Sprawdź:

```text
[ ] width = 400
[ ] height = 198
[ ] stride = 400
[ ] nowy obszar był pusty przed zapisem
[ ] FRAME wskazuje nową lokalizację
[ ] DATA wskazuje FRAME + 12
[ ] RLE dekoduje dokładnie 79 200 indeksów
[ ] round-trip RLE przechodzi poprawnie
[ ] CRC16 jest poprawny
[ ] file_checksum CRC32 jest poprawny
[ ] zachowany jest oryginalny plik ED do przywrócenia
```

Najbezpieczniejsza metoda kontroli to ponowne wydobycie grafiki z gotowego, już zmodyfikowanego VBF.

## Inne wersje firmware

Nie kopiuj tych offsetów w ciemno do innego softu. Najpierw znajdź descriptor, potwierdź geometrię, wskaźniki `FRAME` / `DATA` i zdekoduj oryginalny obraz.

## Źródła

- MicroHacker / Convers+ reverse engineering: https://microhacker.denkdose.de/
- vbftool: https://github.com/dsch/vbftool

Niniejsze repozytorium nie jest projektem Ford Motor Company i nie jest przez Forda wspierane ani zatwierdzone.

## Licencja

Kod narzędzi w tym repozytorium udostępniany jest na licencji MIT. Firmware, logotypy oraz inne zasoby należą do ich odpowiednich właścicieli i nie są częścią licencji tego repozytorium.
