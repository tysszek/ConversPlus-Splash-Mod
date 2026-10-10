# Convers+ — polskie menu V5.3.3

Dokument opisuje aktualny patch widocznych polskich napisów w firmware Ford Convers+ 1412-FL. Repozytorium nie zawiera binarnego firmware Forda — przechowuje dokumentację i skrypty odtworzeniowe do użycia na własnych plikach VBF.

## Zakres zmian

Patch dotyczy wyłącznie aktywnych polskich wpisów wyświetlanych na liczniku. Kopie innych języków oraz nieużywane wpisy tabel systemowych pozostają bez zmian.

| Oryginał | Nazwa na liczniku |
| --- | --- |
| Zmieniacz płyt CD | Płyta CD |
| wejście Auxiliary | Multimedia USB/BT |
| Forward Alert | Ostrz. kolizji |
| Driver Alert | Czujność |
| Colour themes | Kolory |
| Advanced | Zaawansowane |
| Cruise Control | Tempomat |
| Dokladnie | przychodzi |

## Zawartość menu „Kolory”

Aktywne opcje motywów przetłumaczono następująco:

| Oryginał | Nazwa na liczniku |
| --- | --- |
| Dark | Ciemny |
| Blue | Niebieski |
| Grey | Szary |
| Red | Czerwony |

Pola deskryptora motywów zachowują swoje oryginalne rozmiary, a dłuższe napisy są zapisane w sprawdzonej wolnej puli. Napisy Green i Lunar Sky znajdujące się w nieużywanym obszarze nie zostały zmienione, ponieważ w przeanalizowanej ścieżce menu nie mają aktywnych odwołań.

## Odtworzenie patcha

Skrypty są przypięte do konkretnych baz SHA-256 i odmawiają pracy na innym obrazie bez ponownej analizy offsetów.

Dla CD:

~~~bash
python tools/build_menu_labels_v531_physical_fix.py   CS7T-14C026-CD_V5_2.vbf   CS7T-14C026-CD_V5_3_2.vbf

python tools/apply_theme_labels_v533.py   CS7T-14C026-CD_V5_3_2.vbf   CS7T-14C026-CD_V5_3_3.vbf
~~~

Dla ED:

~~~bash
python tools/apply_ed_phone_fix_v53.py   CS7T-14C026-ED_BAZA.vbf   CS7T-14C026-ED_V5_3.vbf
~~~

Pierwszy skrypt CD zawiera również wcześniejsze zmiany V5.3: menu główne, nagłówki, „Tempomat” oraz fizycznie potwierdzone wskaźniki nagłówków. Skrypt ED zmienia „Dokladnie” na „przychodzi”, zachowując rozmiar zasobu przez skrócenie sąsiedniego „Akcept.” do „Akcept”.

## Zweryfikowane obrazy

| Plik | SHA-256 | CRC16 | file_checksum |
| --- | --- | --- | --- |
| CS7T-14C026-CD V5.3.3 | 212ef4f577a5acdce4ab276b9daff3f057647dc7b5317f437d09586ef4584756 | DA3C | 449BB259 |
| CS7T-14C026-ED V5.3 | c283d7ae243bbbaba4f27ed163c70b8bd9e29888f878507dadebddf1336f2568 | 9A13 | 980FC989 |
| 7M2T-14C025-AA bez zmian | 61d445cbee401500a132b1ea904a398563c6a0a385142158ca646c00e1cbc2ab | — | — |
| CD V5.2 do odzyskiwania | 21058ce5f64949e7926e2225eda00c06b43e5308ecd77a651f5ca0f96a631d49 | CAB2 | DF611AEB |
| ED baza do odzyskiwania | 6b8a0a3d72338014570e4493ffb4749299c0f18dcc40a6754f229ec92c7ccab2 | 9A13 | 980FC989 |

## Audyt V5.3.3

Wykonane kontrole:

- wszystkie 5 plików VBF przechodzi vbf_tool.py verify;
- SHA256SUMS.txt przechodzi w całości;
- unzip -t pakietu przechodzi bez błędów;
- skrypt V5.3.3 odtworzony z V5.3.2 tworzy wynik bitowo identyczny z obrazem V5.3.3;
- 18 kontroli napisów, wskaźników oraz pól deskryptora przechodzi;
- AA pozostaje niezmieniony, a ED nie zawiera zmian graficznych.

Wgranie V5.3.3 do fizycznego licznika nie zostało jeszcze wykonane. To oznacza, że kontrola struktury i danych jest pozytywna, ale zgodność konkretnego egzemplarza licznika powinna zostać potwierdzona po bezpiecznym flashowaniu i sprawdzeniu menu.

## Poza zakresem

Nie dodano komunikatu „Niski poziom płynu chłodniczego” ani obsługi jego zdarzenia CAN/PCM. To osobna zmiana funkcjonalna, nie samo tłumaczenie tekstu.

Przed programowaniem zachowaj oryginalne CD, ED, AA/SBL i EEPROM, sprawdź sumy SHA-256 oraz używaj stabilnego zasilania. Modyfikujesz firmware na własne ryzyko.
