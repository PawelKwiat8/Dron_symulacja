# Skrypt startowy symulacji PX4 (start_px4_sim.sh)

Skrypt ten automatyzuje uruchamianie pełnego środowiska symulacyjnego w jednym oknie terminala (Terminator), podzielonym na panele.
## Spis treści

- [I. Wymagania](#i-wymagania)
- [II. Jak uruchomić symulację](#ii-jak-uruchomić-symulację)
- [III. Opis okna konsoli](#iii-opis-okna-konsoli)
- [IV. Opis procesu](#iv-opis-procesu)
## I. Wymagania

### Terminator
```bash
sudo apt install terminator
```

### QGroundControl 
musi być w tym folderze jako `QGroundControl-x86_64.AppImage`.

## II. Jak uruchomić symulację

Po prostu wejdź do folderu i odpal skrypt:
```bash
cd ~/Dron_symulacja/docker/start_sim
./start_px4_sim.sh
```

Opcjonalnie wykonaj poniższą komendę w terminalu, aby stworzyć skrót na pulpicie:
```bash
ln -s ~/Dron_symulacja/docker/start_sim/start_px4_sim.sh ~/Desktop/Start_PX4_Sim
```
(Po stworzeniu skrótu, kliknij na niego prawym przyciskiem na pulpicie i wybierz "Allow Launching", jeśli to konieczne).

## III. Opis okna konsoli
### Panel 1: PX4 SITL (na hoście)
- Czyści stare procesy.
- Uruchamia właściwą symulację (fizyka, Gazebo).
```bash
cd KNR_Drone_PX4_Autopilot
pkill -9 px4; pkill -9 gz; pkill -9 ruby
make px4_sitl gz_tiltrotor_aruco
```

### Panel 2: MicroXRCEAgent (Docker)
Mostek tłumaczący MAVLink na ROS2.
1. Wchodzi do kontenera:
```bash
docker exec -it knr_drone_px4 bash
```
2. Wewnątrz kontenera uruchamia:
```bash
source /opt/ros/jazzy/setup.bash && source ~/ros_ws/install/setup.bash
pkill -f MicroXRCEAgent
MicroXRCEAgent udp4 -p 8888
```

### Panel 3: Drone_handler_px4 (Docker)
Główny węzeł sterujący dronem
1. Wchodzi do kontenera:
```bash
docker exec -it knr_drone_px4 bash
```
2. Wewnątrz kontenera uruchamia:
```bash
source /opt/ros/jazzy/setup.bash && source ~/ros_ws/install/setup.bash
pkill -f drone_handler_px4
ros2 run drone_hardware drone_handler_px4
```

### Panel 4: Shell (Docker)
Otwiera  konsolę  wewnątrz kontenera .
```bash
docker exec -it knr_drone_px4 bash -c 'cd ~/ros_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && exec bash'
```

> **Wskazówka:** Jeśli w Panelu 2 lub 3 przerwiesz proces (np. `Ctrl+C`), skrypt **automatycznie** otworzy konsolę wewnątrz kontenera z załadowanym środowiskiem ROS (`source ...`), więc nie musisz wpisywać tego ręcznie.


## IV. Opis procesu 

1.  **Terminator Config**: Generuje plik layoutu `/tmp/terminator_px4_config`.
2.  **Docker Start**: Uruchamia kontener `knr_drone_px4` jeśli nie działa.
3.  **QGroundControl**: Uruchamia `./QGroundControl-x86_64.AppImage` jeśli nie działa.
4.  **Terminator**: Otwiera okno z wyżej wymienionymi komendami.





