# Część 2: Gazebo

## Zasada Działania
LIDAR działa na zasadzie wysyłania impulsów światła laserowego i mierzenia czasu ich powrotu . Na podstawie tego czasu oblicza odległość od przeszkody.
W tej symulacji sensor skanuje **dolną półkulę** (360° dookoła i 90° w dół)

#
```bash
apt-get install ros-${ROS_DISTRO}-ros-gz-bridge
```

## Uruchomienie

Bridge jest już skonfigurowany w `start_px4_sim.sh`:

lub 

```bash
ros2 run ros_gz_bridge parameter_bridge \
  /lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked \
  --ros-args -r /lidar/points:=/lidar
```

## Konfiguracja model.sdf


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


## skonfigurowane pliki 

| Plik | Lokalizacja |
|------|-------------|
| `model.sdf` | Docker knr_drone_px4: `/tools/PX4-Autopilot/Tools/simulation/gz/models/tiltrotor/model.sdf` |

---

# Część 3: Wizualizacja w RViz

## Uruchomienie RViz z zapisaną konfiguracją

```bash

rviz2 -d ~/ros_ws/src/rviz_configs/lidar_config.rviz
```

## Konfiguracja TF (Pozycja drona)

TF (Transform Frames) to system w ROS, który pozwala śledzić relacje przestrzenne między różnymi elementami robota (np. "gdzie jest lidar względem drona?") oraz między robotem a światem ("gdzie jest dron na mapie?").

W naszej symulacji:
1.  **Gazebo** zna dokładną pozycję modelu `tiltrotor`.
2.  **ros_gz_bridge** (skonfigurowany w `start_px4_sim.sh`) pobiera tę pozycję z tematu Gazebo `/model/tiltrotor/pose` i publikuje ją jako wiadomość ROS na temat `/tf`.
3.  **RViz** nasłuchuje na `/tf` i dzięki temu wie, jak narysować drona i podpięte do niego sensory w przestrzeni 3D.

W RViz:
*   **Fixed Frame**: To punkt odniesienia dla całego widoku. Ustawiliśmy go na `tiltrotor`, co oznacza "widok z perspektywy drona" (dron jest w centrum i zawsze stoi prosto, a świat przesuwa się wokół niego). To bardzo wygodne do testowania sensorów.
*   **PointCloud2**: Wyświetla chmurę punktów. Dzięki TF, punkty są rysowane w odpowiedniej odległości i orientacji względem drona.
