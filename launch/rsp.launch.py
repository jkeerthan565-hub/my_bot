import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
def generate_launch_description():

    # Check if we're told to use sim time and rviz
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('rviz')

    # Process the URDF file
    pkg_path = get_package_share_directory('my_bot')
    xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file).toxml()
    world_file_path = os.path.join(pkg_path, 'worlds', 'world1.world')
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
        cmd=['ign', 'gazebo', '-r','empty.sdf'],
        output='screen'
    )

    # Spawn entity into Gazebo
    node_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description','-name', 'robot101',],
        output='screen'
    )

    node_point_cloud = ComposableNodeContainer(
        name='depth_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[
            ComposableNode(
                package='depth_image_proc',
                plugin='depth_image_proc::PointCloudXyzNode',
                name='point_cloud_xyz_node',
                remappings=[
                    ('image_rect', '/depth_camera/points/depth_image'),
                    ('camera_info', '/depth_camera/points/camera_info'),
                    ('points', '/depth_camera/points')
                ],
                parameters=[{'use_sim_time': use_sim_time}]
            )
        ],
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
                   '/depth_camera@sensor_msgs/msg/Image@gz.msgs.Image',
                   '/depth_camera/depth_image@sensor_msgs/msg/Image@gz.msgs.Image',
                   '/depth_camera/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloud2',
                   '/depth_camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo'],
        output='screen'
    )
# Compress the raw image stream for lower bandwidth usage
   # Compress the raw image stream to compressed topic
    node_image_compressor = Node(
        package='image_transport',
        executable='republish',
        arguments=['raw', 'compressed'],
        remappings=[
            ('in/raw', '/depth_camera/image_raw'),
            ('out/compressed', '/depth_camera/compressed_image')  # Automatically outputs to /image_raw/compressed
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
        node_image_compressor,
        node_point_cloud
    ])
