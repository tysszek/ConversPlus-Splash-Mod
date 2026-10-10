# Polskie napisy menu — V5.3.4

## Zakres

V5.3.4 jest kontynuacją zweryfikowanej wersji CD V5.3.3. Użytkownik potwierdził, że pozycje `Green` i `Lunar Sky` są widoczne na fizycznym liczniku po wejściu do menu motywów. Zostały więc przetłumaczone razem z pozostałymi aktywnymi pozycjami.

Zmiana dotyczy wyłącznie dwóch napisów w:

```text
CS7T-14C026-CD.vbf
```

Nie zmieniano `ED`, `AA`, obsługi CAN ani logiki komunikatów. Komunikat o niskim poziomie płynu chłodniczego pozostaje poza zakresem tej wersji.

## Końcowe nazwy sześciu widocznych motywów

| Oryginał | Polski |
|---|---|
| Ciemny | Ciemny |
| Niebieski | Niebieski |
| Szary | Szary |
| Czerwony | Czerwony |
| Green | Zielony |
| Lunar Sky | Nocne niebo |

Poprzednie poprawki menu V5.3.3 pozostają zachowane, w tym napisy menu głównego, nagłówki `Ostrz. kolizji` i `Czujność`, `Kolory`, `Zaawansowane`, `Tempomat` oraz poprawka `Dokladnie` → `przychodzi` w ED.

## Ochrona struktury rekordów

Oba wpisy są aktywnymi rekordami menu. Patch zmienia tylko tekst w miejscu, bez przesuwania danych:

| Wpis | Adres napisu | Adres rekordu | Flaga zachowana |
|---|---:|---:|---:|
| Green → Zielony | `0xD78A0` | `0xD7804` | `0x40008A61` |
| Lunar Sky → Nocne niebo | `0xD78B0` | `0xD784C` | `0x40008A1D` |

Wskaźniki rekordów i flagi pozostały niezmienione. Dzięki temu wybór motywu zachowuje dotychczasową strukturę ustawień.

## Odtworzenie patcha

Skrypt jest przypięty do dokładnej bazy V5.3.3 i odmówi pracy na innym pliku:

```bash
python tools/apply_theme_labels_v534.py \
  CS7T-14C026-CD_V5_3_3.vbf \
  CS7T-14C026-CD_V5_3_4.vbf
```

Skrypt sprawdza SHA-256 wejścia, pełne rekordy motywów, wskaźniki, flagi, stare napisy, a po zmianie przelicza CRC16 i `file_checksum`.

## Wyniki walidacji

| Plik | SHA-256 | CRC16 | file_checksum |
|---|---|---:|---:|
| CD V5.3.3 — wejście | `212ef4f577a5acdce4ab276b9daff3f057647dc7b5317f437d09586ef4584756` | `DA3C` | `449BB259` |
| CD V5.3.4 — wynik | `dde96153e4ad9948596fb0f4d93e723949bd351625bd99f599d0ce0ab12d8f03` | `13CC` | `37D37491` |

Audyt wynikowy:

- zmieniono 18 bajtów payloadu — tylko dwa napisy,
- wszystkie pięć plików VBF w paczce przechodzi weryfikację,
- sumy SHA-256 paczki są zgodne,
- `AA` i `ED` pozostały identyczne względem V5.3.3,
- nie dodano komunikatu o płynie chłodniczym ani nowej obsługi sygnału CAN.

## Bezpieczeństwo

Przed wgraniem zachowaj oryginalne pliki oraz paczkę odzyskiwania. Modyfikacja firmware licznika wiąże się z ryzykiem jego unieruchomienia. Repozytorium zawiera dokumentację i skrypty, ale nie zawiera binarnego firmware Forda.
