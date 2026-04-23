from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Формирует launch-описание для запуска 
    """
    takeoff_altitude_arg = DeclareLaunchArgument(
        "takeoff_altitude",
        default_value="3.0",
        description="Target takeoff altitude in meters.",
    )

    # Описываем сам запускаемый ROS2-узел и передаем параметр высоты взлета.
    node = Node(
        package="ros2_mavros_takeoff",
        executable="arm_takeoff",
        name="arm_takeoff_node",
        output="screen",
        parameters=[
            {
                "takeoff_altitude": LaunchConfiguration("takeoff_altitude"),
            }
        ],
    )

    # Возвращаем итоговый список действий launch-сценария.
    return LaunchDescription([
        takeoff_altitude_arg,
        node,
    ])
