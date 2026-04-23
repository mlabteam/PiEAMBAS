#!/usr/bin/env python3
"""
Сценарий работы:
1. Дождаться доступности MAVROS-сервисов.
2. Дождаться подключения к FCU.
3. Переключить режим полета (по умолчанию GUIDED).
4. Выполнить ARM.
5. Отправить команду TAKEOFF на заданную высоту.
6. Дождаться набора целевой высоты по локальной позиции.
"""

import time
from typing import Optional

import rclpy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, CommandTOL, SetMode
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy


class ArmTakeoffNode(Node):
    def __init__(self) -> None:
        super().__init__("arm_takeoff_node")


        self.declare_parameter("takeoff_altitude", 3.0)
        self.declare_parameter("flight_mode", "GUIDED")
        self.declare_parameter("service_timeout", 10.0)
        self.declare_parameter("connection_timeout", 30.0)
        self.declare_parameter("arm_timeout", 10.0)
        self.declare_parameter("takeoff_timeout", 30.0)
        self.declare_parameter("airborne_altitude_threshold", 0.5)

        # Считываем параметры один раз при старте.
        self.takeoff_altitude = float(self.get_parameter("takeoff_altitude").value)
        self.flight_mode = str(self.get_parameter("flight_mode").value)
        self.service_timeout = float(self.get_parameter("service_timeout").value)
        self.connection_timeout = float(self.get_parameter("connection_timeout").value)
        self.arm_timeout = float(self.get_parameter("arm_timeout").value)
        self.takeoff_timeout = float(self.get_parameter("takeoff_timeout").value)
        self.airborne_altitude_threshold = float(
            self.get_parameter("airborne_altitude_threshold").value
        )

        # Последнее известное состояние FCU и текущая высота из локальной позиции.
        self.current_state: Optional[State] = None
        self.current_altitude: Optional[float] = None

        pose_qos = QoSProfile(depth=10)
        pose_qos.reliability = ReliabilityPolicy.BEST_EFFORT

        # Подписка на состояние автопилота (подключен/вооружен/режим).
        self.create_subscription(State, "/mavros/state", self._state_cb, 10)
        # Подписка на локальную позицию для контроля фактического набора высоты.
        self.create_subscription(
            PoseStamped,
            "/mavros/local_position/pose",
            self._pose_cb,
            pose_qos,
        )

        # Клиенты MAVROS-сервисов управления режимом, ARM и TAKEOFF.
        self.arm_client = self.create_client(CommandBool, "/mavros/cmd/arming")
        self.takeoff_client = self.create_client(CommandTOL, "/mavros/cmd/takeoff")
        self.mode_client = self.create_client(SetMode, "/mavros/set_mode")

    def _state_cb(self, msg: State) -> None:
        """Колбэк состояния FCU."""
        self.current_state = msg

    def _pose_cb(self, msg: PoseStamped) -> None:
        """Колбэк локальной позиции: сохраняем только Z (высоту)."""
        self.current_altitude = msg.pose.position.z

    def _wait_for_service(self, client, name: str, timeout: float) -> bool:
        """Ожидает появления ROS2-сервиса с ограничением по времени."""
        start = time.monotonic()
        while not client.wait_for_service(timeout_sec=1.0):
            elapsed = time.monotonic() - start
            self.get_logger().info(f"Waiting for service {name}... {elapsed:.1f}s")
            if elapsed > timeout:
                self.get_logger().error(f"Timeout waiting for service {name}")
                return False
        return True

    def _call_service(self, client, request, timeout: float):
        """Унифицированный асинхронный вызов сервиса с ожиданием результата."""
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done():
            self.get_logger().error("Service call timed out")
            return None
        return future.result()

    def _wait_connected(self, timeout: float) -> bool:
        """Ожидает факт подключения MAVROS к полетному контроллеру (FCU)."""
        self.get_logger().info("Waiting for FCU connection on /mavros/state...")
        start = time.monotonic()
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.current_state is not None and self.current_state.connected:
                self.get_logger().info("FCU connected")
                return True
            if (time.monotonic() - start) > timeout:
                self.get_logger().error("Timeout waiting for FCU connection")
                return False
        return False

    def _set_mode(self, mode: str) -> bool:
        """Запрашивает у FCU смену полетного режима (например, GUIDED)."""
        req = SetMode.Request()
        req.custom_mode = mode

        res = self._call_service(self.mode_client, req, self.service_timeout)
        if res is None:
            return False

        if not res.mode_sent:
            self.get_logger().error(f"FCU rejected mode change to {mode}")
            return False

        self.get_logger().info(f"Mode change requested: {mode}")
        return True

    def _arm(self) -> bool:
        """Отправляет команду ARM (взведение моторов)."""
        req = CommandBool.Request()
        req.value = True

        res = self._call_service(self.arm_client, req, self.arm_timeout)
        if res is None:
            return False

        if not res.success:
            self.get_logger().error("Arming command was rejected")
            return False

        self.get_logger().info("Arming command accepted")
        return True

    def _takeoff(self, altitude: float) -> bool:
        """Отправляет команду автоматического взлета на заданную высоту."""
        req = CommandTOL.Request()
        # Высота целевого взлета в метрах относительно локальной системы.
        req.altitude = altitude
        # Для ArduPilot в локальном взлете эти поля обычно не используются,
        # но структура сервиса требует их заполнения.
        req.latitude = 0.0
        req.longitude = 0.0
        req.min_pitch = 0.0
        # yaw = NaN означает "не изменять курс принудительно".
        req.yaw = float("nan")

        res = self._call_service(self.takeoff_client, req, self.takeoff_timeout)
        if res is None:
            return False

        if not res.success:
            self.get_logger().error("Takeoff command was rejected")
            return False

        self.get_logger().info(f"Takeoff command accepted, target altitude: {altitude:.2f} m")
        return True

    def _already_armed_and_flying(self) -> bool:
        """Проверяет, что аппарат уже заармлен и находится в воздухе."""
        if self.current_state is None or self.current_altitude is None:
            return False

        return self.current_state.armed and (
            self.current_altitude >= self.airborne_altitude_threshold
        )

    def _wait_target_altitude(self, target: float, timeout: float) -> bool:
        """Ожидает набор высоты до 90% от цели или завершает по таймауту."""
        if target <= 0.0:
            return True

        start = time.monotonic()
        # Допуск 10% нужен, чтобы не зависнуть из-за шумов и колебаний по высоте.
        threshold = target * 0.9
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.current_altitude is not None and self.current_altitude >= threshold:
                self.get_logger().info(
                    f"Reached altitude {self.current_altitude:.2f} m (target {target:.2f} m)"
                )
                return True
            if (time.monotonic() - start) > timeout:
                if self.current_altitude is None:
                    self.get_logger().warning(
                        "Takeoff sent, but altitude feedback is unavailable on "
                        "/mavros/local_position/pose"
                    )
                    return True
                self.get_logger().error(
                    f"Takeoff timeout: current altitude {self.current_altitude:.2f} m, "
                    f"target {target:.2f} m"
                )
                return False
        return False

    def execute(self) -> bool:
        """Выполняет полный сценарий ARM + TAKEOFF с проверками на каждом шаге."""
        # 1) Ждем, пока MAVROS-сервисы станут доступны.
        if not self._wait_for_service(self.mode_client, "/mavros/set_mode", self.service_timeout):
            return False
        if not self._wait_for_service(self.arm_client, "/mavros/cmd/arming", self.service_timeout):
            return False
        if not self._wait_for_service(
            self.takeoff_client,
            "/mavros/cmd/takeoff",
            self.service_timeout,
        ):
            return False

        # 2) Проверяем, что есть связь с FCU.
        if not self._wait_connected(self.connection_timeout):
            return False

        # Даем пару циклов подпискам, чтобы получить актуальную высоту перед решением.
        for _ in range(20):
            rclpy.spin_once(self, timeout_sec=0.1)

        # Если дрон уже заармлен и находится в воздухе, повторные ARM/TAKEOFF не отправляем.
        if self._already_armed_and_flying():
            self.get_logger().warning(
                "Vehicle is already armed and flying; skipping ARM/TAKEOFF commands"
            )
            return True

        # 3) Переключаем режим в GUIDED (или заданный параметром).
        if not self._set_mode(self.flight_mode):
            return False

        # 4) Выполняем ARM.
        if not self._arm():
            return False

        # 5) Отправляем TAKEOFF.
        if not self._takeoff(self.takeoff_altitude):
            return False

        # 6) Контролируем достижение целевой высоты.
        return self._wait_target_altitude(self.takeoff_altitude, self.takeoff_timeout)


def main(args=None) -> None:
    """Точка входа ROS2-приложения."""
    rclpy.init(args=args)
    node = ArmTakeoffNode()

    try:
        success = node.execute()
        if success:
            node.get_logger().info("Mission step completed: ARM + TAKEOFF")
        else:
            node.get_logger().error("Mission failed")
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
