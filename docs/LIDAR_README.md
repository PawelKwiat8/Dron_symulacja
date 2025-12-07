# Konfiguracja Lidaru 3D

---

# Część 1: Webots + ArduPilot SITL

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

---

# Część 2: Gazebo + PX4 SITL

## Wymagania

Na kontenerze Docker (`knr_drone_px4`) należy doinstalować bridge ROS-Gazebo:

```bash
apt-get install ros-${ROS_DISTRO}-ros-gz-bridge
```

## Uruchomienie

Bridge jest już skonfigurowany w `start_px4_sim.sh`:

```bash
ros2 run ros_gz_bridge parameter_bridge \
  /lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked \
  --ros-args -r /lidar/points:=/lidar
```

## Konfiguracja model.sdf

Plik `model.sdf` znajduje się na dockerze w:
```
/tools/PX4-Autopilot/Tools/simulation/gz/models/tiltrotor/model.sdf
```

Dodano nowy link z lidarem:

```xml
<link name="lidar_link">
  <pose>0 0 -0.1 0 0 0</pose>   <!-- 10cm pod dronem -->
  <sensor name="lidar" type="gpu_ray">
    <ray>
      <scan>
        <horizontal>
          <samples>720</samples>              <!-- promienie w poziomie -->
          <min_angle>-3.14159</min_angle>     <!-- -180° -->
          <max_angle>3.14159</max_angle>      <!-- +180° -->
        </horizontal>
        <vertical>
          <samples>32</samples>               <!-- warstwy pionowe -->
          <min_angle>-1.5707</min_angle>      <!-- -90° (dół) -->
          <max_angle>0</max_angle>            <!-- 0° (poziom) -->
        </vertical>
      </scan>
      <range>
        <min>0.05</min>
        <max>30.0</max>
      </range>
    </ray>
    <update_rate>10</update_rate>
    <topic>lidar</topic>
  </sensor>
</link>

<joint name="lidar_joint" type="fixed">
  <parent>base_link</parent>
  <child>lidar_link</child>
</joint>
```


## Parametry do zmiany

| Parametr | Opis |
|----------|------|
| `samples` (horizontal) | Liczba promieni w poziomie (720 = co 0.5°) |
| `samples` (vertical) | Liczba warstw pionowych |
| `min/max` (range) | Zakres pomiaru [m] |
| `update_rate` | Częstotliwość publikacji [Hz] |
| `pose` | Pozycja lidaru względem drona |

## skonfigurowane pliki 

| Plik | Lokalizacja |
|------|-------------|
| `model.sdf` | Docker: `/tools/PX4-Autopilot/Tools/simulation/gz/models/tiltrotor/` |
| `start_px4_sim.sh` | `docker/start_sim/` (bridge ROS-Gazebo) |

