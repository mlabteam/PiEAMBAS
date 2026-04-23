from setuptools import setup

# Имя Python-пакета должно совпадать с именем директории модуля.
package_name = "ros2_mavros_takeoff"

setup(
    # Базовые сведения о пакете.
    name=package_name,
    version="0.0.1",
    packages=[package_name],

    # Указываем файлы, которые нужно установить вместе с пакетом:
    # - ресурсный маркер ament,
    # - package.xml,
    # - launch-файл.
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/arm_takeoff.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="user",
    maintainer_email="user@example.com",
    description="ROS2 Python package for arming and takeoff via MAVROS.",
    license="MIT",
    tests_require=["pytest"],

    # Точка входа для команды:
    # ros2 run ros2_mavros_takeoff arm_takeoff
    entry_points={
        "console_scripts": [
            "arm_takeoff = ros2_mavros_takeoff.arm_takeoff_node:main",
        ],
    },
)
