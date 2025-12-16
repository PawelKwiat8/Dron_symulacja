from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='ros_gz_bridge',
            arguments=[
                # Lidar: Gz topic -> ROS topic
                '/lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
                # TF: Gz pose -> ROS /tf
                '/model/tiltrotor/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'
            ],
            remappings=[
                ('/lidar/points', '/lidar'),
                ('/model/tiltrotor/pose', '/tf')
            ],
            output='screen'
        )
    ])
