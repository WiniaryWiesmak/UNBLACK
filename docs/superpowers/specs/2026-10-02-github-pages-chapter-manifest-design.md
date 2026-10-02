# UNBLACK: automatyczny spis rozdziałów z nazw plików

## Cel

Czytelnik UNBLACK ma automatycznie wyświetlać rozdziały dodane do repozytorium GitHub Pages. Autor dodaje PDF zgodny z konwencją `numer-nazwa.pdf` i nie edytuje przy tym `index.html` ani ręcznego spisu treści.

Przykłady:

- `0-wstęp.pdf` → numer `00`, tytuł `Wstęp`
- `1-xyz.pdf` → numer `01`, tytuł `Xyz`
- `2-czym-jest-unblack.pdf` → numer `02`, tytuł `Czym jest unblack`

## Zakres

Zmiana obejmuje:

- zastąpienie wykrywania `0.pdf`, `1.pdf` itd. manifestem plików;
- dodanie szablonu `chapters.json`, przetwarzanego automatycznie przez Jekyll na GitHub Pages;
- odczyt, walidację i sortowanie manifestu w `index.html`;
- pobieranie numeru i tytułu rozdziału z nazwy pliku;
- przemianowanie obecnego `0.pdf` na `0-wstęp.pdf`;
- zachowanie czytnika PDF, pobierania, otwierania w nowej karcie i nawigacji.

Zmiana nie obejmuje panelu administracyjnego, przesyłania plików z poziomu strony ani serwera aplikacyjnego.

## Konwencja nazw

Akceptowane są pliki pasujące do wzoru:

```text
<nieujemny numer>-<niepusta nazwa>.pdf
```

Rozszerzenie małymi literami `.pdf` jest konwencją projektu. Numer może mieć dowolną liczbę cyfr. Pliki są sortowane po wartości numerycznej, a nie alfabetycznie. Luki w numeracji są dozwolone.

Tytuł powstaje przez:

1. usunięcie prefiksu numerycznego i rozszerzenia;
2. zamianę myślników i podkreśleń na pojedyncze spacje;
3. usunięcie nadmiarowych spacji;
4. zamianę pierwszej litery na wielką z uwzględnieniem polskich znaków.

Pozostała część tytułu zachowuje wielkość liter z nazwy pliku.

## Architektura i przepływ danych

GitHub Pages będzie publikowany bezpośrednio z gałęzi, z włączonym domyślnym przetwarzaniem Jekyll.

Plik `chapters.json` będzie miał front matter Jekyll i użyje `site.static_files`, aby podczas publikacji wygenerować tablicę wszystkich plików PDF. Każdy wpis będzie zawierał oryginalną nazwę i ścieżkę przetworzoną filtrem `relative_url`, dzięki czemu strona zadziała także pod adresem projektu, np. `/unblack/`.

Po uruchomieniu `index.html`:

1. pobiera `chapters.json` z wyłączoną pamięcią podręczną;
2. sprawdza format odpowiedzi;
3. filtruje nazwy niepasujące do konwencji;
4. odrzuca duplikaty numerów jako błąd konfiguracji;
5. sortuje wpisy numerycznie;
6. buduje listę i uruchamia pierwszy rozdział.

Nie zostanie dodane zapytanie do GitHub API. Dzięki temu strona nie będzie zależeć od limitów API ani od nazwy konta i repozytorium.

## Stany i obsługa błędów

- Podczas pobierania manifestu wyświetlany jest istniejący stan ładowania.
- Brak pasujących plików daje komunikat z przykładem `0-wstęp.pdf`.
- Niedostępny lub niepoprawny manifest daje komunikat o błędzie konfiguracji GitHub Pages.
- Dwa pliki z tym samym numerem dają czytelny błąd i wymieniają konfliktowy numer.
- Pliki PDF bez poprawnego prefiksu i nazwy są ignorowane.
- Przy otwarciu przez `file://` strona używa awaryjnie `0-wstęp.pdf` i informuje, że pełne wykrywanie działa po publikacji przez GitHub Pages.

## Interfejs

Numer wyświetlany w spisie i nagłówku pochodzi z prefiksu pliku i jest dopełniany do co najmniej dwóch cyfr. Tytuł pochodzi z części po pierwszym myślniku. Pobierany dokument zachowuje oryginalną nazwę pliku.

Wygląd czarno-czerwony, responsywność i dostępność obecnego interfejsu pozostają bez zmian.

## Wdrożenie na GitHub Pages

Repozytorium musi publikować stronę przez `Deploy from a branch`. Nie należy dodawać pliku `.nojekyll`, ponieważ wyłączyłby generowanie manifestu.

Po dodaniu lub zmianie pliku PDF kolejny build GitHub Pages ponownie wygeneruje `chapters.json`. Nie jest potrzebna osobna akcja GitHub ani usługa zewnętrzna.

## Testy i kryteria akceptacji

- Manifest zawierający `0-wstęp.pdf` i `1-xyz.pdf` tworzy dwa rozdziały w kolejności `0`, `1`.
- `10-dziesiąty.pdf` jest sortowany po liczbie, a nie przed `2-drugi.pdf`.
- Myślniki i podkreślenia w nazwie są zamieniane na spacje.
- Plik bez zgodnej nazwy jest ignorowany.
- Duplikat numeru pokazuje błąd konfiguracji.
- Kliknięcie rozdziału aktualizuje czytnik, link otwierania i pobieranie.
- Widoki 390 px i 1440 px nie mają poziomego przepełnienia.
- Tryb `file://` pokazuje `0-wstęp.pdf` wraz z informacją o ograniczeniu.

