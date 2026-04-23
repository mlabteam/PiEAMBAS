from setuptools import setup

package_name = "ros2_mavros_distance_home"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/distance_home.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="user",
    maintainer_email="user@example.com",
    description="ROS2 Python package that publishes 3D distance to home point.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "distance_home = ros2_mavros_distance_home.distance_home_node:main",
        ],
    },
)