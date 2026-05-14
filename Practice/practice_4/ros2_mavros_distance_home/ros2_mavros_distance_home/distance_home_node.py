#!/usr/bin/env python3

import math
from typing import Optional, Tuple

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64


class DistanceHomeNode(Node):
    def __init__(self) -> None:
        super().__init__("distance_home_node")

        self.declare_parameter("pose_topic", "/mavros/local_position/pose")
        self.declare_parameter("distance_topic", "/distance_to_home")

        pose_topic = str(self.get_parameter("pose_topic").value)
        distance_topic = str(self.get_parameter("distance_topic").value)

        self.home_position: Optional[Tuple[float, float, float]] = None
        self.current_pose: Optional[PoseStamped] = None

        pose_qos = QoSProfile(depth=10)
        pose_qos.reliability = ReliabilityPolicy.BEST_EFFORT

        self.distance_pub = self.create_publisher(Float64, distance_topic, 10)
        self.create_subscription(PoseStamped, pose_topic, self._pose_cb, pose_qos)

        self.get_logger().info(
            f"Distance-to-home publisher started: pose={pose_topic}, out={distance_topic}"
        )

    def _distance_to_home(self) -> Optional[float]:
        if self.current_pose is None or self.home_position is None:
            return None

        x, y, z = self.home_position
        px = self.current_pose.pose.position.x
        py = self.current_pose.pose.position.y
        pz = self.current_pose.pose.position.z
        return math.sqrt((px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2)

    def _pose_cb(self, msg: PoseStamped) -> None:
        self.current_pose = msg

        if self.home_position is None:
            self.home_position = (
                msg.pose.position.x,
                msg.pose.position.y,
                msg.pose.position.z,
            )
            self.get_logger().info(
                "Home point captured: "
                f"x={self.home_position[0]:.2f}, "
                f"y={self.home_position[1]:.2f}, "
                f"z={self.home_position[2]:.2f}"
            )

        distance = self._distance_to_home()
        if distance is None:
            return

        out = Float64()
        out.data = distance
        self.distance_pub.publish(out)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DistanceHomeNode()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()