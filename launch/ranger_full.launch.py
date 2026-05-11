"""
Full-system launch for Ranger Mini 2.0 — chassis + sensors + SLAM + Nav2.

Usage:
  # Mapping mode (no map loaded, SLAM builds map)
  ros2 launch ranger_nav ranger_full.launch.py mode:=mapping

  # Navigation mode (load map, localize, navigate)
  ros2 launch ranger_nav ranger_full.launch.py mode:=nav map:=/path/to/map.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('ranger_nav')

    # --- Mode selection ---
    mode = LaunchConfiguration('mode', default='mapping')
    is_mapping = PythonExpression(["'", mode, "' == 'mapping'"])
    is_nav = PythonExpression(["'", mode, "' == 'nav'"])

    map_yaml = LaunchConfiguration('map', default='/home/robot/maps/ranger_map.yaml')
    use_rviz = LaunchConfiguration('use_rviz', default='true')

    # --- Sub-launches (always on) ---
    ranger_base_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'ranger_base.launch.py')
        ),
    )

    ranger_sensors_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'ranger_sensors.launch.py')
        ),
    )

    # ============================================================
    # Mapping mode: slam_toolbox async SLAM
    # ============================================================
    slam_mapping_config = os.path.join(pkg_dir, 'config', 'slam_toolbox_mapping.yaml')

    slam_mapping_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_mapping_config],
        condition=IfCondition(is_mapping),
    )

    # ============================================================
    # Navigation mode: localization + Nav2 stack
    # ============================================================
    slam_localization_config = os.path.join(
        pkg_dir, 'config', 'slam_toolbox_localization.yaml'
    )

    localization_node = Node(
        package='slam_toolbox',
        executable='localization_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_localization_config],
        condition=IfCondition(is_nav),
    )

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_yaml}],
        condition=IfCondition(is_nav),
    )

    nav2_config = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[nav2_config],
        condition=IfCondition(is_nav),
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[nav2_config],
        condition=IfCondition(is_nav),
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[nav2_config],
        condition=IfCondition(is_nav),
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[nav2_config],
        condition=IfCondition(is_nav),
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': [
                'map_server',
                'controller_server',
                'planner_server',
                'behavior_server',
                'bt_navigator',
            ],
        }],
        condition=IfCondition(is_nav),
    )

    # ============================================================
    # RViz2
    # ============================================================
    rviz_config = os.path.join(pkg_dir, 'rviz', 'ranger_nav.rviz')
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='mapping',
                              description="'mapping' or 'nav'"),
        DeclareLaunchArgument('map', default_value='/home/robot/maps/ranger_map.yaml'),
        DeclareLaunchArgument('use_rviz', default_value='true'),

        # Always-on: chassis + sensors
        ranger_base_launch,
        ranger_sensors_launch,

        # Mode: mapping
        slam_mapping_node,

        # Mode: nav
        localization_node,
        map_server_node,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        lifecycle_manager,

        rviz2_node,
    ])
