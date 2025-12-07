# Konfiguracja Lidaru 3D w Webots + ArduPilot SITL


## Uruchomienie

```bash
ros2 launch drone_bringup drone_simulation.launch.py world:=lidar_test.wbt
```


## Konfiguracja pliku .wbt

```
DEF Iris Iris {
  translation 0 0 0.13
  controller "ardupilot_sitl_controller"
  controllerArgs [
    # ...
    # ...
    "--lidar-fps"          # <-- OPCJONALNA ZMIANA
    "5"
  ]
  extensionSlot [
    Lidar {
      translation 0 0 -0.18       # pozycja względem środka drona
      rotation 0 0 1 0            # orientacja
      name "Lidar"                # WAŻNE: musi pasować do --lidar
      horizontalResolution 180    # liczba promieni w poziomie <-- OPCJONALNA ZMIANA
      fieldOfView 6.28318         # 360° (2π radianów)
      verticalFieldOfView 3.14159 # 180° (π radianów) - półkula
      numberOfLayers 30           # liczba warstw pionowych <-- OPCJONALNA ZMIANA
      minRange 0.05                # minimalna odległość [m] 
      maxRange 30                 # maksymalna odległość [m]
    }
    # ... reszta sensorów (kamera, GPS, etc.)
  ]
}
```

> ⚠️ **Uwaga**: W Webots **nie ma możliwości skonfigurowania lidaru tak, aby skanował tylko dolną półkulę**. Dlatego zastosowano obejście - w kodzie dodano filtr `if p.z > 0: continue`, który odrzuca punkty z górnej półkuli. Jeśli ustawisz `numberOfLayers = 30`, efektywnie tylko **15 warstw** będzie używanych (dolna połowa).


## webots_vehicle_ros.py

Plik odpowiada za komunikację między Webots a ROS2. Pobiera dane z lidaru Webots, filtruje nieprawidłowe punkty i publikuje chmurę punktów na topic `/lidar` jako `PointCloud2`.


## Pliki skonfigurowane do obsługi lidaru

| Plik | Ścieżka |
|------|---------|
| `webots_vehicle_ros.py` | `src/webots_simulation/resource/controllers/ardupilot_sitl_controller/` |
| `ardupilot_sitl_controller.py` | `src/webots_simulation/resource/controllers/ardupilot_sitl_controller/` |
| `lidar_test.wbt` | `src/webots_simulation/resource/worlds/` |
| `IrisSimple.proto` | `src/webots_simulation/resource/protos/` |

