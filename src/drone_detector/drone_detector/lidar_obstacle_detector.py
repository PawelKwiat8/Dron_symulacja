import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
import struct
import math

class LidarObstacleDetector(Node):
    def __init__(self):
        super().__init__('lidar_obstacle_detector')
        
        # Subskrypcja tematu lidar
        self.subscription = self.create_subscription(
            PointCloud2,
            '/lidar',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning
        
        self.get_logger().info('Lidar Obstacle Detector started. Listening on /lidar...')
        
        # Parametry detekcji
        self.warning_distance = 1.0  # Metry
        self.critical_distance = 0.5 # Metry

    def listener_callback(self, msg):
        # Prosty parser PointCloud2 (zakładamy format float32 x, y, z)
        # W ROS2 zazwyczaj używa się sensor_msgs_py, ale zrobimy to ręcznie dla pewności
        
        # Sprawdźmy strukturę danych
        # PointField: x (offset 0), y (offset 4), z (offset 8) -> 12 bajtów na punkt
        
        point_step = msg.point_step
        data = msg.data
        width = msg.width
        
        min_dist = float('inf')
        closest_point = None
        
        obstacle_count = 0
        
        # Iterujemy przez punkty
        # Uwaga: To jest prosta implementacja w Pythonie, dla dużych chmur może być wolna.
        # W produkcji używa się numpy.
        
        for i in range(0, len(data), point_step):
            # Odczyt x, y, z (float32)
            # struct.unpack zwraca krotkę
            try:
                x, y, z = struct.unpack_from('fff', data, i)
            except struct.error:
                break
                
            # Oblicz odległość euklidesową
            dist = math.sqrt(x*x + y*y + z*z)
            
            # Ignoruj błędy pomiarowe (bardzo bliskie 0)
            if dist < 0.05:
                continue
                
            if dist < min_dist:
                min_dist = dist
                closest_point = (x, y, z)
            
            if dist < self.warning_distance:
                obstacle_count += 1

        # Logika ostrzegania
        if min_dist < self.critical_distance:
            self.get_logger().error(f'CRITICAL: Obstacle detected at {min_dist:.2f}m! Coords: {closest_point}')
        elif min_dist < self.warning_distance:
            self.get_logger().warning(f'WARNING: Obstacle nearby at {min_dist:.2f}m. Count: {obstacle_count}')
        # else:
            # self.get_logger().info(f'Clear. Closest: {min_dist:.2f}m', throttle_duration_sec=2.0)

def main(args=None):
    rclpy.init(args=args)
    node = LidarObstacleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
