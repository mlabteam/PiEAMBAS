#!/usr/bin/env python3

import math
import time
from typing import List, Optional, Tuple

import rclpy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import SetMode
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy


class WaypointMissionNode(Node):

    def __init__(self) -> None:
        super().__init__("waypoint_mission_node")

        # Режимы автопилота:
        # - guided_mode: рабочий режим для полета по setpoint.
        # - land_mode: режим для завершения миссии посадкой.
        # - set_guided_mode_on_start: запрашивать ли GUIDED в начале миссии.

        self.declare_parameter("guided_mode", "GUIDED")
        self.declare_parameter("land_mode", "LAND")
        self.declare_parameter("set_guided_mode_on_start", True)

        # Таймауты и служебные паузы для старта миссии.
        self.declare_parameter("service_timeout_sec", 10.0)
        self.declare_parameter("connection_timeout_sec", 30.0)
        self.declare_parameter("preflight_wait_sec", 3.0)

        # Параметры контура полета:
        # - частота публикации setpoint,
        # - допустимое отклонение от точки,
        # - таймаут достижения точки,
        # - выдержка в точке,
        # - минимальная высота, выше которой считаем аппарат "в воздухе".
        self.declare_parameter("command_rate_hz", 10.0)
        self.declare_parameter("waypoint_tolerance_m", 0.5)
        self.declare_parameter("waypoint_timeout_sec", 120.0)
        self.declare_parameter("hold_time_sec", 2.0)
        self.declare_parameter("airborne_altitude_threshold_m", 0.5)

        # Координаты waypoint в локальной системе ENU (массивы одинаковой длины).
        self.declare_parameter("waypoints_x_m", [0.0])
        self.declare_parameter("waypoints_y_m", [0.0])
        self.declare_parameter("waypoints_z_m", [2.0])

        # Чтение параметров в локальные поля, чтобы не обращаться к параметрам повторно.
        self.guided_mode = str(self.get_parameter("guided_mode").value)
        self.land_mode = str(self.get_parameter("land_mode").value)
        self.set_guided_mode_on_start = bool(
            self.get_parameter("set_guided_mode_on_start").value
        )

        self.service_timeout = float(self.get_parameter("service_timeout_sec").value)
        self.connection_timeout = float(self.get_parameter("connection_timeout_sec").value)
        self.preflight_wait_sec = float(self.get_parameter("preflight_wait_sec").value)

        self.command_rate_hz = float(self.get_parameter("command_rate_hz").value)
        self.waypoint_tolerance = float(self.get_parameter("waypoint_tolerance_m").value)
        self.waypoint_timeout = float(self.get_parameter("waypoint_timeout_sec").value)
        self.hold_time_sec = float(self.get_parameter("hold_time_sec").value)
        self.airborne_altitude_threshold = float(
            self.get_parameter("airborne_altitude_threshold_m").value
        )

        self.waypoints_x = [float(v) for v in self.get_parameter("waypoints_x_m").value]
        self.waypoints_y = [float(v) for v in self.get_parameter("waypoints_y_m").value]
        self.waypoints_z = [float(v) for v in self.get_parameter("waypoints_z_m").value]

        # Базовая валидация параметров на старте — чтобы завершиться быстро и явно,
        # если конфиг миссии задан некорректно.
        self._validate_waypoint_parameters()

        # Последнее известное состояние дрона.
        self.current_state: Optional[State] = None
        self.current_pose: Optional[PoseStamped] = None

        pose_qos = QoSProfile(depth=10)
        pose_qos.reliability = ReliabilityPolicy.BEST_EFFORT

        # Подписки на состояние FCU и локальную позу.
        self.create_subscription(State, "/mavros/state", self._state_cb, 10)
        self.create_subscription(PoseStamped, "/mavros/local_position/pose", self._pose_cb, pose_qos)

        # Публикатор локальных setpoint и клиент для смены полетного режима.
        self.setpoint_pub = self.create_publisher(PoseStamped, "/mavros/setpoint_position/local", 10)
        self.mode_client = self.create_client(SetMode, "/mavros/set_mode")

    def _validate_waypoint_parameters(self) -> None:
        """Проверяет корректность параметров миссии.

        Критерии валидности:
        1. Массив waypoint не должен быть пустым.
        2. Все координатные массивы должны иметь одинаковую длину.
        3. Частота публикации и допуск должны быть положительными.
        """
        if len(self.waypoints_x) == 0:
            raise ValueError("waypoints_x_m is empty")
        if not (len(self.waypoints_x) == len(self.waypoints_y) == len(self.waypoints_z)):
            raise ValueError("waypoints arrays must have equal lengths")
        if self.command_rate_hz <= 0.0:
            raise ValueError("command_rate_hz must be > 0")
        if self.waypoint_tolerance <= 0.0:
            raise ValueError("waypoint_tolerance_m must be > 0")

    def _state_cb(self, msg: State) -> None:
        """Колбэк состояния FCU (/mavros/state)."""
        self.current_state = msg

    def _pose_cb(self, msg: PoseStamped) -> None:
        """Колбэк локальной позиции (/mavros/local_position/pose)."""
        self.current_pose = msg

    def _wait_for_service(self, client, name: str, timeout: float) -> bool:
        """Ожидает появления ROS-сервиса с ограничением по времени."""
        start = time.monotonic()
        while not client.wait_for_service(timeout_sec=1.0):
            if (time.monotonic() - start) > timeout:
                self.get_logger().error(f"Timeout waiting for service {name}")
                return False
            self.get_logger().info(f"Waiting for service {name}...")
        return True

    def _wait_connected(self, timeout: float) -> bool:
        """Ожидает соединение MAVROS с FCU."""
        start = time.monotonic()
        self.get_logger().info("Waiting for FCU connection...")
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.current_state is not None and self.current_state.connected:
                self.get_logger().info("FCU connected")
                return True
            if (time.monotonic() - start) > timeout:
                self.get_logger().error("Timeout waiting for FCU connection")
                return False
        return False

    def _call_set_mode(self, mode: str) -> bool:
        """Запрашивает переключение полетного режима (GUIDED/LAND и т.д.)."""
        req = SetMode.Request()
        req.custom_mode = mode

        future = self.mode_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=self.service_timeout)
        if not future.done():
            self.get_logger().error(f"SetMode timeout for mode {mode}")
            return False

        res = future.result()
        if res is None or not res.mode_sent:
            self.get_logger().error(f"Failed to switch mode to {mode}")
            return False

        self.get_logger().info(f"Mode switch requested: {mode}")
        return True

    def _distance_to(self, x: float, y: float, z: float) -> Optional[float]:
        """Считает 3D-расстояние от текущей позиции до целевой точки."""
        if self.current_pose is None:
            return None

        px = self.current_pose.pose.position.x
        py = self.current_pose.pose.position.y
        pz = self.current_pose.pose.position.z
        return math.sqrt((px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2)

    def _publish_setpoint(self, x: float, y: float, z: float) -> None:
        """Публикует целевой setpoint в локальной системе координат.

        Ориентация фиксируется в нейтральное значение (w=1.0), поскольку
        в данной задаче управляем только положением.
        """
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z
        msg.pose.orientation.w = 1.0
        self.setpoint_pub.publish(msg)

    def _wait_until_reached(self, x: float, y: float, z: float, timeout: float) -> bool:
        """Удерживает публикацию setpoint до достижения точки или таймаута.

        В MAVROS setpoint нужно публиковать непрерывно, поэтому внутри цикла
        выполняется регулярная отправка команды позиции и проверка расстояния.
        """
        start = time.monotonic()
        rate_dt = 1.0 / self.command_rate_hz

        while rclpy.ok():
            # Непрерывно подаем целевую точку в FCU.
            self._publish_setpoint(x, y, z)
            rclpy.spin_once(self, timeout_sec=rate_dt)

            # Проверяем, достаточно ли близко к целевой точке.
            distance = self._distance_to(x, y, z)
            if distance is not None and distance <= self.waypoint_tolerance:
                return True
            # self.get_logger().info(
            #     f"distance: {distance if distance is not None else float('nan'):.2f}"
            # )

            # Если точка не достигнута за отведенное время — считаем миссию неуспешной.
            if (time.monotonic() - start) > timeout:
                self.get_logger().error(
                    f"Waypoint timeout at ({x:.1f}, {y:.1f}, {z:.1f}); "
                    f"last distance={distance if distance is not None else float('nan'):.2f}"
                )
                return False

        return False

    def _ensure_armed_and_flying(self) -> bool:
        """Проверяет условия допуска к миссии.
        """
        if self.current_state is None or self.current_pose is None:
            self.get_logger().error("No telemetry yet from /mavros/state or /mavros/local_position/pose")
            return False

        if not self.current_state.armed:
            self.get_logger().error("Vehicle is not armed; mission requires pre-armed state")
            return False

        if self.current_pose.pose.position.z < self.airborne_altitude_threshold:
            self.get_logger().error("Vehicle is not in air; mission requires already flying state")
            return False

        return True

    def _build_waypoints(self) -> List[Tuple[float, float, float]]:
        """Собирает список waypoint в формате [(x, y, z), ...]."""
        return list(zip(self.waypoints_x, self.waypoints_y, self.waypoints_z))

    def execute(self) -> bool:
        """Выполняет миссию полета по точкам и возвращения с посадкой."""
        # 1) Готовность MAVROS и связь с FCU.
        if not self._wait_for_service(self.mode_client, "/mavros/set_mode", self.service_timeout):
            return False
        if not self._wait_connected(self.connection_timeout):
            return False

        # Даем подпискам короткое время, чтобы получить актуальные данные
        # перед проверками допуска к полету.
        warmup_until = time.monotonic() + self.preflight_wait_sec
        while rclpy.ok() and time.monotonic() < warmup_until:
            rclpy.spin_once(self, timeout_sec=0.1)

        # 2) Критические preflight-проверки.
        if not self._ensure_armed_and_flying():
            return False

        # 3) При необходимости переводим аппарат в рабочий режим GUIDED.
        if self.set_guided_mode_on_start:
            if not self._call_set_mode(self.guided_mode):
                return False

        if self.current_pose is None:
            self.get_logger().error("Current pose is unavailable")
            return False

        # 4) Фиксируем "домашнюю" точку как текущую позицию на старте миссии.
        home_x = float(self.current_pose.pose.position.x)
        home_y = float(self.current_pose.pose.position.y)
        home_z = float(self.current_pose.pose.position.z)

        self.get_logger().info(
            f"Home point captured: x={home_x:.2f}, y={home_y:.2f}, z={home_z:.2f}"
        )

        # 5) Проходим все waypoint по порядку.
        waypoints = self._build_waypoints()
        for idx, (x, y, z) in enumerate(waypoints, start=1):
            self.get_logger().info(f"Flying to waypoint {idx}/{len(waypoints)}: ({x:.1f}, {y:.1f}, {z:.1f})")
            if not self._wait_until_reached(x, y, z, self.waypoint_timeout):
                return False

            # Небольшая выдержка в точке нужна для стабилизации перед следующим сегментом.
            hold_until = time.monotonic() + self.hold_time_sec
            while rclpy.ok() and time.monotonic() < hold_until:
                self._publish_setpoint(x, y, z)
                rclpy.spin_once(self, timeout_sec=1.0 / self.command_rate_hz)

        # 6) После последней точки возвращаемся в домашнюю позицию.
        self.get_logger().info("All mission waypoints completed. Returning to home point.")
        if not self._wait_until_reached(home_x, home_y, home_z, self.waypoint_timeout):
            return False

        # 7) Инициируем посадку в точке возврата через LAND.
        self.get_logger().info("Home point reached. Switching to LAND mode.")
        if not self._call_set_mode(self.land_mode):
            return False

        self.get_logger().info("Landing initiated.")
        return True


def main(args=None) -> None:
    """Точка входа ROS2-приложения.
    """
    rclpy.init(args=args)

    try:
        node = WaypointMissionNode()
    except ValueError as exc:
        temp_node = Node("waypoint_mission_param_error")
        temp_node.get_logger().error(f"Invalid parameters: {exc}")
        temp_node.destroy_node()
        rclpy.shutdown()
        raise SystemExit(2) from exc

    try:
        ok = node.execute()
        if not ok:
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
