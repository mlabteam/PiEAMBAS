from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="ros2_mavros_distance_home",
                executable="distance_home",
                name="distance_home_node",
                output="screen",
            )
        ]
    )