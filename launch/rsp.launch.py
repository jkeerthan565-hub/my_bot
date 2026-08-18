import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro
def generate_launch_description():

    # Check if we're told to use sim time and rviz
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('rviz')

    # Process the URDF file
    pkg_path = get_package_share_directory('my_bot')
    xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file).toxml()
    world_file_path = os.path.join(pkg_path, 'worlds', 'empty.world')
    config_path = os.path.join(pkg_path, 'config', 'gz_rob1.config')
    # Create a robot_state_publisher node
    params = {'robot_description': robot_description_config, 'use_sim_time': use_sim_time}
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params]
    )

    # Create a joint_state_publisher node
    node_joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # RViz Node (Conditional)
    node_rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', os.path.join(pkg_path, 'config', 'viewbot_rviz.rviz')],
        condition=IfCondition(use_rviz)
    )

    # ROS-GZ Bridge Node using YAML config
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': os.path.join(pkg_path, 'config', 'ros_gz_bridge.yaml'),
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
        }],
        output='screen'
    )

    # Launch Gazebo window (Fortress / Ignition)
    ign_gazebo = ExecuteProcess(
        cmd=['ign', 'gazebo', '-r', 'empty.sdf',world_file_path, '--gui-config', config_path],
        output='screen'
    )

    # Spawn entity into Gazebo
    node_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description'],
        output='screen'
    )

    # Command Velocity Bridge ROS 2 <-> Gazebo
    node_ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
                   '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
                   '/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
                   '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
                   '/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo'],
        output='screen'
    )
# Compress the raw image stream for lower bandwidth usage
   # Compress the raw image stream to compressed topic
    node_image_compressor = Node(
        package='image_transport',
        executable='republish',
        arguments=['raw', 'compressed'],
        remappings=[
            ('in', '/image_raw'),
            ('out', '/image_raw')  # Automatically outputs to /image_raw/compressed
        ],
        parameters=[{
            'use_sim_time': use_sim_time,
            'in_transport_qos': 'best_effort'  # Matches Gazebo's Best Effort publisher
        }],
        output='screen'
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use sim time if true'),

        DeclareLaunchArgument(
            'rviz',
            default_value='true',
            description='Open RViz if true'),

        node_robot_state_publisher,
        node_joint_state_publisher,
        node_rviz,
        ign_gazebo,
        node_spawn_entity,
        node_ros_gz_bridge,
        bridge,
        node_image_compressor
    ])
