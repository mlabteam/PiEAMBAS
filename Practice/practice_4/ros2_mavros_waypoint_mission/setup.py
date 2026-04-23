from setuptools import setup

package_name = "ros2_mavros_waypoint_mission"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/waypoint_mission.launch.py"]),
        (f"share/{package_name}/config", ["config/waypoints.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="user",
    maintainer_email="user@example.com",
    description="ROS2 Python package for MAVROS waypoint-only mission with return-to-home landing.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "waypoint_mission = ros2_mavros_waypoint_mission.waypoint_mission_node:main",
        ],
    },
)
