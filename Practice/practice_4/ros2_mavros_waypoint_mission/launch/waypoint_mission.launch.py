from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory("ros2_mavros_waypoint_mission")
    default_params = os.path.join(package_share, "config", "waypoints.yaml")

    mission_node = Node(
        package="ros2_mavros_waypoint_mission",
        executable="waypoint_mission",
        name="waypoint_mission_node",
        output="screen",
        parameters=[default_params],
    )

    return LaunchDescription([mission_node])