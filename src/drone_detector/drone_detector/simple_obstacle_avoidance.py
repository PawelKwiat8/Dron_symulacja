import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from drone_interfaces.msg import VelocityVectors
import numpy as np
import math

class SimpleObstacleAvoidance(Node):
    def __init__(self):
        super().__init__('simple_obstacle_avoidance')
        
        # Declare parameters
        # Safety geometry (2D slice)
        # - obstacle_width: width of the safety "tunnel" around the motion path (drone radius + margin)*2
        # - vertical_limit: we only consider points with |z| <= vertical_limit (approx 2D)
        # INCREASED vertical_limit significantly to account for drone PITCH at high speeds!
        # At 5m/s with 20 deg pitch, obstacles appear at different Z in body frame.
        self.declare_parameter('obstacle_width', 1.5)   # [m] Wider tunnel
        self.declare_parameter('vertical_limit', 2.0)   # [m] Much larger vertical slice to catch walls during pitch

        # Safety distances / dynamics
        # stop_distance here means "buffer" before an obstacle where commanded speed should be 0.
        # We also account for reaction_time + max_decel to stop reliably at higher speeds.
        self.declare_parameter('stop_distance', 2.0)    # [m] Reduced slightly to fit range
        self.declare_parameter('slow_distance', 14.5)   # [m] Match Lidar range (15m) with safety margin
        self.declare_parameter('reaction_time', 0.5)    # [s] Faster reaction needed
        self.declare_parameter('max_decel', 2.5)        # [m/s^2] Stronger braking needed for short range!

        # Misc
        self.declare_parameter('lidar_frame_id', 'lidar_link')
        
        # Topics
        self.lidar_sub = self.create_subscription(
            PointCloud2,
            '/lidar',
            self.lidar_callback,
            10
        )
        
        # Input from user scripts (User should publish here)
        self.cmd_sub = self.create_subscription(
            VelocityVectors,
            'knr_hardware/velocity_vectors_user',
            self.cmd_callback,
            10
        )
        
        # Output to drone hardware (Safety node publishes here)
        self.cmd_pub = self.create_publisher(
            VelocityVectors,
            'knr_hardware/velocity_vectors',
            10
        )
        
        # State
        self.latest_scan = None

        self.obs_width = float(self.get_parameter('obstacle_width').value)
        self.tunnel_radius = max(0.05, self.obs_width / 2.0)
        self.vert_limit = float(self.get_parameter('vertical_limit').value)

        self.stop_dist = float(self.get_parameter('stop_distance').value)
        self.max_considered_dist = float(self.get_parameter('slow_distance').value)
        self.reaction_time = float(self.get_parameter('reaction_time').value)
        self.max_decel = float(self.get_parameter('max_decel').value)
        
        self.get_logger().info('SimpleObstacleAvoidance Node Started')
        self.get_logger().info(
            f'Parameters: tunnel_width={self.obs_width:.2f}m (radius={self.tunnel_radius:.2f}), '
            f'vert_limit=±{self.vert_limit:.2f}m, buffer(stop_distance)={self.stop_dist:.2f}m, '
            f'max_range={self.max_considered_dist:.1f}m, reaction_time={self.reaction_time:.2f}s, '
            f'max_decel={self.max_decel:.2f}m/s^2'
        )
        self.get_logger().info('Please publish control commands to: knr_hardware/velocity_vectors_user')

    def lidar_callback(self, msg):
        # Store the latest scan for processing in the command callback
        # Parsing PC2 is expensive, so we might want to do it here or on demand.
        # Doing it here ensures we have fresh obstacle info.
        self.latest_scan = self.process_point_cloud(msg)

    def process_point_cloud(self, msg):
        """
        Convert PointCloud2 to a numpy array of 2D points (X,Y) in lidar/body frame.
        We keep only points within |z|<=vertical_limit to approximate a 2D slice.
        """
        # Simplified parser assuming float32 fields x, y, z
        # In a robust production node, we should check msg.fields for offsets
        
        # Get field offsets (assuming x,y,z exist)
        offset_x = -1
        offset_y = -1
        offset_z = -1
        
        for field in msg.fields:
            if field.name == 'x': offset_x = field.offset
            if field.name == 'y': offset_y = field.offset
            if field.name == 'z': offset_z = field.offset
            
        if offset_x == -1 or offset_y == -1 or offset_z == -1:
            return None

        # Assuming little endian and float32 (4 bytes)
        # Point step is the byte length of one point
        point_step = msg.point_step
        width = msg.width
        height = msg.height
        data = np.frombuffer(msg.data, dtype=np.uint8)
        
        # Reshape to access points
        # This is a raw view, we need to extract x,y,z based on offsets
        # A faster way with numpy structure
        
        # Create a structured dtype
        # We need to handle padding if point_step > 12
        # But constructing a complex dtype can be tricky if padding is irregular.
        # Simple method: View buffer as void, stride by point_step
        
        # Let's assume standard packed float32 x,y,z for now or use a slower iterator if needed.
        # But for performance in python, numpy struct array is best.
        
        # Build a dtype that matches the point_step
        # Example: if point_step=16 and x,y,z are at 0,4,8
        # dtype = [('x', 'f4'), ('y', 'f4'), ('z', 'f4'), ('pad', 'V4')]
        
        # Determine packing
        dtype_list = []
        current_offset = 0
        
        # Sort fields by offset to build struct
        sorted_fields = sorted([f for f in msg.fields if f.name in ['x', 'y', 'z']], key=lambda f: f.offset)
        
        # This dynamic construction is safer
        # Warning: This doesn't handle overlapping fields or complex types, but standard PC2 is simple.
        
        # Actually, simpler: just read x, y, z strided
        
        try:
            points_num = width * height
            if points_num == 0:
                return None
                
            # Extract columns
            # View as byte array
            # x_bytes = data[offset_x::point_step] -> this is simplistic, depends on flatness
            # msg.data is 1D array of bytes

            # Use structured array to handle the data safely
            # We construct a dtype that accounts for the point_step (full structure of one point)
            # This handles stride automatically
            # However, we need to know the exact layout.
            # Assuming typical float32 fields, we can try to extract just the needed bytes.

            # Alternative approach: simple slicing with stride
            # This works if the data is aligned and simple (which it often is)
            # But "To change to a dtype of a different size, the last axis must be contiguous" error
            # suggests slicing issues.

            # Let's fix by copying the sliced data using .copy() to ensure C-contiguity
            # This is critical for frombuffer or view if we wanted to change dtype, 
            # but actually we are extracting bytes. The issue with frombuffer is it expects a contiguous buffer.
            # Slicing numpy array [start::step] produces non-contiguous view.
            # We need to make it contiguous bytes before passing to frombuffer?
            # Actually, frombuffer expects a buffer interface.
            
            # Option C: Reshape and slice to get all 4 bytes of float32
            # 1. View as (N, point_step)
            # 2. Slice the 4 bytes for X, Y, Z
            # 3. View as float32

            points_num = width * height
            if points_num == 0:
                return None

            # Ensure data length matches expectations
            if len(data) != points_num * point_step:
                # self.get_logger().warn(f"Data length mismatch: {len(data)} != {points_num} * {point_step}")
                return None

            # Reshape to access each point as a row
            # This is safe because data is contiguous uint8
            points_data = data.reshape(points_num, point_step)

            # Extract 4 bytes for each field
            # We copy here to ensure contiguous memory for the float view
            x_bytes = points_data[:, offset_x : offset_x + 4].copy()
            y_bytes = points_data[:, offset_y : offset_y + 4].copy()
            z_bytes = points_data[:, offset_z : offset_z + 4].copy()

            # Now we have (N, 4) arrays of uint8. View them as (N, 1) float32
            # We need to flatten or view directly
            x = x_bytes.view(dtype=np.float32).flatten()
            y = y_bytes.view(dtype=np.float32).flatten()
            z = z_bytes.view(dtype=np.float32).flatten()
            
            # Combine
            # Filter NaNs and Infs
            mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
            
            # Filter Z (vertical slice)
            # User wants +/- 0.5m
            mask = mask & (np.abs(z) <= self.vert_limit)
            
            # Optional: ignore far points (performance + avoid far influence)
            if self.max_considered_dist > 0:
                r = np.sqrt(x * x + y * y)
                mask = mask & (r <= self.max_considered_dist)

            # Output 2D slice
            # FIX: Invert Y axis based on user report (Left/Right confusion)
            # Standard ROS: Y+ is Left. If controls/lidar are mismatched, we flip here.
            points_xy = np.column_stack((x[mask], -y[mask]))
            return points_xy
            
        except Exception as e:
            self.get_logger().error(f"Error parsing PointCloud2: {e}")
            return None

    def cmd_callback(self, msg):
        # Received a velocity command from user
        # Check against obstacles and republish
        
        safe_cmd = self.check_safety(msg)
        self.cmd_pub.publish(safe_cmd)

    def _min_free_distance_along_path(self, points_xy: np.ndarray, ux: float, uy: float) -> float:
        """
        Compute the minimum "free distance" along direction u=(ux,uy) before entering the safety radius.
        """
        if points_xy is None or len(points_xy) == 0:
            return float('inf')

        px = points_xy[:, 0]
        py = points_xy[:, 1]

        along = px * ux + py * uy
        cross = np.abs(px * uy - py * ux)

        # FIX: Check only points AHEAD of movement vector (positive along).
        # Previously we checked points inside the drone radius "behind" center, which blocked escape from obstacles.
        # If along < 0, the obstacle is behind us (relative to motion), so moving forward is SAFE (we are moving away).
        
        # We use a tiny negative margin just to catch points exactly at 0 (noise), but generally must be > -small_epsilon.
        # NOT -radius.
        mask = (along > -0.05) & (cross < self.tunnel_radius)
        
        if not np.any(mask):
            return float('inf')

        cross_m = cross[mask]
        along_m = along[mask]

        # Calculate geometric intersection
        # Collision happens when center of drone is at distance 'd' such that point is on the edge of circle.
        # dist_to_collision = along - sqrt(radius^2 - cross^2)
        # If term inside sqrt is negative, it means point is inside the 'lane' but deeper than radius?
        # Actually cross < radius guarantees positive term.
        
        safety_buffer = 0.05 # Extra 5cm margin on radius calculation to be safe
        effective_radius = self.tunnel_radius + safety_buffer
        
        # If cross > effective_radius, no collision (should be filtered by mask, but safety check)
        # We use max(0, ...)
        
        delta = np.sqrt(np.maximum(effective_radius * effective_radius - cross_m * cross_m, 0.0))
        
        # free distance is how much we can move FORWARD from current (0,0)
        # free = along_point - delta
        free = along_m - delta
        
        # If free < 0, it means we are already colliding (or point is inside the buffer zone)
        return float(np.min(free))

    def _max_safe_speed_for_free_distance(self, free_dist: float) -> float:
        """
        Maximum speed calculation using a simple LINEAR RAMP.
        This is more stable than physics-based stopping distance when controllers conflict.
        
        Logic:
          - Inside stop_dist: Max speed = 0
          - Between stop_dist and slow_dist: Linear ramp
          - Slope (gain) determines how aggressively we verify distance.
        """
        if not math.isfinite(free_dist):
            return float('inf')

        # Hard stop
        if free_dist <= self.stop_dist:
            return 0.0
            
        # Linear ramp parameters
        # Gain: how many m/s allowed per meter of free space?
        # 0.4 means: for 10m of free space, we allow 4 m/s.
        # Increased to 0.4 because we have shorter range, so we need to allow speed closer to wall
        # but stop firmly.
        gain = 0.4 
        
        allowed = (free_dist - self.stop_dist) * gain
        return max(0.0, allowed)

    def _scale_xy_to_safe(self, points_xy: np.ndarray, vx: float, vy: float) -> tuple[float, float]:
        speed = math.hypot(vx, vy)
        if speed < 1e-3:
            return (0.0, 0.0)

        ux = vx / speed
        uy = vy / speed

        free = self._min_free_distance_along_path(points_xy, ux, uy)
        v_allow = self._max_safe_speed_for_free_distance(free)
        if speed <= v_allow:
            return (vx, vy)

        if v_allow <= 0.0:
            return (0.0, 0.0)

        k = v_allow / speed
        return (vx * k, vy * k)

    def check_safety(self, cmd):
        points_xy = self.latest_scan
        if points_xy is None or len(points_xy) == 0:
            return cmd

        # Create safe command as copy
        safe_cmd = VelocityVectors()
        safe_cmd.vx = cmd.vx
        safe_cmd.vy = cmd.vy
        safe_cmd.vz = cmd.vz
        safe_cmd.yaw = cmd.yaw
        
        vx_d = float(cmd.vx)
        vy_d = float(cmd.vy)

        desired_speed = math.hypot(vx_d, vy_d)
        if desired_speed < 0.05:
            return safe_cmd

        # ------------------------------------------------------------------
        # "Full safety, minimal blocking" strategy
        #
        # 1) Limit each axis independently (vx limited by obstacles in ±X tunnel, vy limited by obstacles in ±Y tunnel)
        #    -> allows sliding along walls (e.g., forward blocked but sideways allowed).
        # 2) Validate the resulting combined vector against obstacles in its actual direction (diagonal safety).
        #    -> prevents diagonal collision cases.
        # 3) If diagonal safety forces too much slowdown, allow falling back to a pure-axis motion (vx-only or vy-only),
        #    but NEVER invent motion that user didn't request (no autonomous sidestep if vy=0 etc).
        # ------------------------------------------------------------------

        # Step 1: axis limiter (component-wise)
        # FIX: Also invert check direction for Y axis because of Lidar/Control mismatch found earlier?
        # We inverted Y in process_point_cloud, so points_xy are now in correct "Control Frame" (Y+ = Left).
        # So here we should use standard logic: vy > 0 means LEFT, so check vector (0, 1).
        
        vx_l = vx_d
        if abs(vx_d) >= 0.05:
            sx = 1.0 if vx_d > 0.0 else -1.0
            free_x = self._min_free_distance_along_path(points_xy, sx, 0.0)
            vx_allow = self._max_safe_speed_for_free_distance(free_x)
            vx_l = sx * min(abs(vx_d), vx_allow)

        vy_l = vy_d
        if abs(vy_d) >= 0.05:
            # vy_d > 0 means LEFT. u = (0, 1).
            sy = 1.0 if vy_d > 0.0 else -1.0
            free_y = self._min_free_distance_along_path(points_xy, 0.0, sy)
            vy_allow = self._max_safe_speed_for_free_distance(free_y)
            vy_l = sy * min(abs(vy_d), vy_allow)

        # Step 2: diagonal safety scaling for the combined vector
        vx_main, vy_main = self._scale_xy_to_safe(points_xy, vx_l, vy_l)

        # Step 3: fallback candidates (only if user commanded that axis)
        candidates: list[tuple[float, float]] = [(vx_main, vy_main)]

        if abs(vx_d) >= 0.05:
            vx_only, vy_only = self._scale_xy_to_safe(points_xy, vx_l, 0.0)
            candidates.append((vx_only, vy_only))

        if abs(vy_d) >= 0.05:
            vx_only, vy_only = self._scale_xy_to_safe(points_xy, 0.0, vy_l)
            candidates.append((vx_only, vy_only))

        candidates.append((0.0, 0.0))

        # Pick candidate that is closest to the user command (least blocking),
        # with a small bias toward keeping some motion if equal.
        best_vx, best_vy = candidates[0]
        best_score = float('inf')
        for cx, cy in candidates:
            diff = (cx - vx_d) * (cx - vx_d) + (cy - vy_d) * (cy - vy_d)
            # small preference for non-zero movement (break ties)
            score = diff - 1e-3 * math.hypot(cx, cy)
            if score < best_score:
                best_score = score
                best_vx, best_vy = cx, cy

        safe_cmd.vx = float(best_vx)
        safe_cmd.vy = float(best_vy)

        return safe_cmd

def main(args=None):
    rclpy.init(args=args)
    node = SimpleObstacleAvoidance()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

