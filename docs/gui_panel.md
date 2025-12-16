# 1. Dokumentacja Techniczna: Panel Sterowania (GUI Panel)

Panel stanowi uniwersalne narzędzie kontroli misji oraz diagnostyki drona. Głównym celem jest zapewnienie interfejsu do manualnej kontroli i podglądu telemetrii, z dodatkowym modułem dedykowanym do testowania algorytmu "Follow ArUco".

## 2. Architektura Systemu

Node `gui_panel` realizuje pętlę sterowania z częstotliwością **10 Hz**. Aplikacja łączy w sobie dwie warstwy:
1.  **Warstwa Bazowa (`DroneController`)**: Obsługa telemetrii, trybów lotu (ARM/DISARM, TAKEOFF/LAND) i komunikacji MAVROS/DDS.
2.  **Warstwa Logiki (`FollowArucoSimulator`)**: Rozszerzenie o logikę przetwarzania obrazu i pętlę PID dla autonomii.

## 3. Moduł Autonomii: Follow ArUco

Jest to "dodatek" funkcjonalny pozwalający na testowanie algorytmów wizyjnych. Sterowanie odbywa się w trybie **Offboard Velocity Control**.

### 3.1. Algorytm Sterowania (Pętla 10Hz)

Przepływ danych w pętli sterowania wygląda następująco:

1.  **Akwizycja Danych**:
    *   Subskrypcja `/aruco_markers` -> Pobranie współrzędnych `(x, y)` w pikselach.

2.  **Przetwarzanie Sygnału**:
    *   **Normalizacja**: Skalowanie odchyłki do zakresu `[-1.0, 1.0]`.
    *   **Deadband**: Zerowanie odchyłek mniejszych niż `50px` (zapobieganie drganiom).
    *   **Low-pass Filter**: Filtracja dolnoprzepustowa (`err_f = (1-a)*err_f + a*err_raw`) w celu redukcji szumu.

3.  **Logika PID**:
    *   **Oś X (Przód/Tył)** sterowana przez odchyłkę Y na obrazie.
    *   **Oś Y (Lewo/Prawo)** sterowana przez odchyłkę X na obrazie.
    *   **Oś Z** pozostaje niezależna (utrzymywanie wysokości).

### 3.2. Parametry Strojenia (Tuning)

Parametry wpływające na zachowanie drona w trybie autonomicznym:

*   **Regulator PID**:
    *   **Kp**: Wzmocnienie błędu (sztywność reakcji).
    *   **Ki**: Eliminacja uchybu ustalonego (z Anti-windup do `[-1.0, 1.0]`).
    *   **Kd**: Tłumienie oscylacji (reakcja na zmianę błędu).
*   **Dynamika**:
    *   **Max Prędkość**: Twardy limit prędkości wyjściowej (Clamp).
    *   **Wygładzanie (0.0-0.9)**: Współczynnik bezwładności dla zadanych prędkości.

### 3.3. Bezpieczeństwo (Failsafe)

*   **Timeout Markera**: Brak detekcji przez >1.0s powoduje zatrzymanie drona (tryb HOLD).
*   **Priorytet Manuala**: Wciśnięcie klawisza sterowania ręcznego natychmiast przerywa autonomię.

## 4. Sterowanie Manualne

Funkcja dostępna niezależnie od trybu ArUco. Pozwala na bezpośrednie wysyłanie wektorów prędkości w układzie Body Frame.
*   **Wymagania**: Okno aplikacji musi posiadać fokus (aktywne).
*   **Mapowanie**:
    *   **WSAD**: Ruch w płaszczyźnie poziomej.
    *   **RF**: Zmiana wysokości (Oś Z).
    *   **QE**: Obrót (Yaw).

## 5. Interfejsy ROS 2

Node komunikuje się z resztą systemu poprzez:

*   **Subskrypcje**:
    *   `/aruco_markers` (`drone_interfaces/msg/MiddleOfAruco`)
*   **Publikacje/Serwisy**:
    *   Komendy prędkości do autopilota (via `mavlink`).
    *   Serwis `ToggleVelocityControl`.
