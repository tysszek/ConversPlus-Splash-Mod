# Convers+ — polskie etykiety menu V5.3

Dokument opisuje poprawkę widocznych polskich napisów w firmware Ford Convers+ 1412-FL. Repozytorium nie zawiera firmware Forda — przechowujemy wyłącznie dokumentację patcha; skrypty odtwarzające patch są dołączone w pakiecie V5.3.

## Zakres V5.3

Patch dotyczy wyłącznie rekordów języka polskiego używanych przez menu i komunikaty wyświetlane na liczniku. Kopie innych języków oraz nieużywane wpisy systemowe pozostają bez zmian.

| Oryginał | Nowa nazwa |
| --- | --- |
| Forward Alert | Ostrz. kolizji |
| Driver Alert | Czujność |
| Colour themes | Kolory |
| Advanced | Zaawansowane |
| Cruise Control | Tempomat |
| Dokladnie | przychodzi |

W bazowej wersji V5.2 były już obecne wcześniejsze zmiany menu głównego:

| Oryginał | Nowa nazwa |
| --- | --- |
| Zmieniacz płyt CD | Płyta CD |
| wejście Auxiliary | Multimedia USB/BT |

## Ważna uwaga dotycząca telefonu

W zasobie ED teksty są zapisane w rekordzie o stałym rozmiarze. przychodzi jest o jeden bajt dłuższe niż Dokladnie, dlatego w tym samym rekordzie skrócono sąsiednią etykietę przycisku:

~~~text
Akcept. -> Akcept
~~~

Nie zmienia to funkcji przycisku. Pozostałe wystąpienia Akcept. nie są częścią tej poprawki.

## Właściwe pliki wejściowe

Skrypty celowo sprawdzają numer części, rozmiar bloku oraz SHA-256 wejścia. Nie uruchamiaj ich na innym firmware bez ponownej analizy offsetów.

### CD — menu

~~~text
CS7T-14C026-CD.vbf
wejściowy SHA-256: 21058ce5f64949e7926e2225eda00c06b43e5308ecd77a651f5ca0f96a631d49
wynikowy SHA-256:  b0b4d596c668a98e61c8ddb44626b5a4a94da4aee835bf1a937b566ed411cfb9
CRC16:             0xCAB2
file_checksum:     0xDF611AEB
~~~

### ED — komunikat telefonu

~~~text
CS7T-14C026-ED.vbf
wejściowy SHA-256: 6b8a0a3d72338014570e4493ffb4749299c0f18dcc40a6754f229ec92c7ccab2
wynikowy SHA-256:  c283d7ae243bbbaba4f27ed163c70b8bd9e29888f878507dadebddf1336f2568
CRC16:             0x9A13
file_checksum:     0x980FC989
~~~

Plik 7M2T-14C025-AA.vbf pozostaje niezmieniony. Ostrzeżenie Niski poziom płynu chłodniczego nie jest częścią V5.3, ponieważ wymaga potwierdzenia obsługi właściwego zdarzenia CAN/PCM, a nie tylko dodania tekstu.

## Odtworzenie patcha

Z katalogu głównego repozytorium:

~~~bash
python tools/apply_menu_labels_v53.py CS7T-14C026-CD.vbf CS7T-14C026-CD_V5_3.vbf
python tools/apply_ed_phone_fix_v53.py CS7T-14C026-ED.vbf CS7T-14C026-ED_V5_3.vbf
~~~

Skrypty aktualizują CRC16 i file_checksum CRC32, a następnie sprawdzają wynik. Przed wgraniem zachowaj oryginalne CD, ED, AA/SBL i EEPROM oraz używaj stabilnego zasilania.

## Status

Wersja V5.3 została zweryfikowana strukturalnie i checksumami VBF. Nie była jeszcze potwierdzona fizycznym wgraniem do licznika. Modyfikujesz firmware na własne ryzyko.
