# Copyright 2022 Trossen Robotics
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the copyright holder nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from interbotix_xs_modules.xs_common import (
    get_interbotix_xslocobot_models,
)
from interbotix_xs_modules.xs_launch import (
    declare_interbotix_xslocobot_robot_description_launch_arguments,
)
from interbotix_xs_modules.xs_launch.xs_launch import determine_use_sim_time_param

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.conditions import IfCondition, LaunchConfigurationEquals, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    robot_model_launch_arg = LaunchConfiguration('robot_model')
    use_rviz_launch_arg = LaunchConfiguration('use_rviz')
    rviz_frame_launch_arg = LaunchConfiguration('rviz_frame')
    use_base_launch_arg = LaunchConfiguration('use_base')
    # use_dock_launch_arg = LaunchConfiguration('use_dock')
    use_lidar_launch_arg = LaunchConfiguration('use_lidar')

    use_camera_launch_arg = LaunchConfiguration('use_camera')
    rs_camera_pointcloud_enable_launch_arg = LaunchConfiguration('rs_camera_pointcloud_enable')
    rs_rbg_camera_profile_launch_arg = LaunchConfiguration('rs_rbg_camera_profile')
    rs_depth_module_profile_launch_arg = LaunchConfiguration('rs_depth_module_profile')
    rs_camera_logging_level_launch_arg = LaunchConfiguration('rs_camera_logging_level')
    rs_camera_output_location_launch_arg = LaunchConfiguration('rs_camera_output_location')
    rs_camera_align_depth_launch_arg = LaunchConfiguration('rs_camera_align_depth')
    rs_camera_initial_reset_launch_arg = LaunchConfiguration('rs_camera_initial_reset')

    motor_configs_launch_arg = LaunchConfiguration('motor_configs')
    mode_configs_launch_arg = LaunchConfiguration('mode_configs')
    load_configs_launch_arg = LaunchConfiguration('load_configs')
    use_sim_launch_arg = LaunchConfiguration('use_sim')
    robot_description_launch_arg = LaunchConfiguration('robot_description')
    hardware_type_launch_arg = LaunchConfiguration('hardware_type')
    xs_driver_logging_level_launch_arg = LaunchConfiguration('xs_driver_logging_level')

    # sets use_sim_time parameter to 'true' if using gazebo hardware
    use_sim_time_param = determine_use_sim_time_param(
        context=context,
        hardware_type_launch_arg=hardware_type_launch_arg
    )

    kobuki_ros_node_parameter_file = ParameterFile(
        param_file=PathJoinSubstitution([
            FindPackageShare('interbotix_xslocobot_control'),
            'config',
            'kobuki_node_params.yaml',
        ]),
        allow_substs=True,
    )

    xslocobot_description_launch_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('interbotix_xslocobot_descriptions'),
                'launch',
                'xslocobot_description.launch.py'
            ])
        ]),
        launch_arguments={
            'robot_model': robot_model_launch_arg,
            'use_rviz': use_rviz_launch_arg,
            'rviz_frame': rviz_frame_launch_arg,
            'use_joint_pub': 'true',
            'rate': '100',
            'source_list': '[dynamixel/joint_states, mobile_base/joint_states]',
            'robot_description': robot_description_launch_arg,
            'use_sim_time': use_sim_time_param,
        }.items(),
    )

    xs_sdk_node = Node(
        condition=UnlessCondition(use_sim_launch_arg),
        package='interbotix_xs_sdk',
        executable='xs_sdk',
        name='xs_sdk',
        arguments=[],
        parameters=[{
            'motor_configs': motor_configs_launch_arg,
            'mode_configs': mode_configs_launch_arg,
            'load_configs': load_configs_launch_arg,
            'robot_description': ParameterValue(robot_description_launch_arg, value_type=str),
            'use_sim_time': use_sim_time_param,
            'xs_driver_logging_level': xs_driver_logging_level_launch_arg,
        }],
        output={
            'stdout': 'screen',
            'stderr': 'screen',
        },
    )

    xs_sdk_sim_node = Node(
        condition=IfCondition(use_sim_launch_arg),
        package='interbotix_xs_sdk',
        executable='xs_sdk_sim.py',
        name='xs_sdk_sim',
        arguments=[],
        parameters=[{
            'motor_configs': motor_configs_launch_arg,
            'mode_configs': mode_configs_launch_arg,
            'robot_description': ParameterValue(robot_description_launch_arg, value_type=str),
            'use_sim_time': use_sim_time_param,
        }],
        output={
            'stdout': 'screen',
            'stderr': 'screen',
        },
    )

    kobuki_node = Node(
        condition=(
            IfCondition(use_base_launch_arg) and LaunchConfigurationEquals('base_type', 'kobuki')
        ),
        package='kobuki_node',
        executable='kobuki_ros_node',
        name='kobuki_ros_node',
        output={'both': 'screen'},
        parameters=[
            kobuki_ros_node_parameter_file
        ],
    )

    rplidar_node = Node(
        condition=IfCondition(use_lidar_launch_arg),
        executable='rplidar_scan_publisher',
        name='rplidar_scan_publisher',
        output={'both': 'screen'},
        parameters=[{
            'serial_port': '/dev/rplidar',
            'serial_baudrate': '115200',
            'frame_id': 'laser_frame_link',
            'inverted': 'false',
            'angle_conpensate': 'true',
        }],
    )

    rs_camera_launch_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('realsense2_camera'),
                'launch',
                'rs_launch.py',
            ])
        ]),
        launch_arguments={
            'camera_name': 'camera',
            'rgb_camera.profile': rs_rbg_camera_profile_launch_arg,
            'depth_module.profile': rs_depth_module_profile_launch_arg,
            'enable_pointcloud': rs_camera_pointcloud_enable_launch_arg,
            'align_depth': rs_camera_align_depth_launch_arg,
            'initial_reset': rs_camera_initial_reset_launch_arg,
            'log_level': rs_camera_logging_level_launch_arg,
            'output': rs_camera_output_location_launch_arg,
        }.items(),
        condition=IfCondition(use_camera_launch_arg),
    )

    return [
        xslocobot_description_launch_include,
        xs_sdk_node,
        xs_sdk_sim_node,
        kobuki_node,
        rplidar_node,
        rs_camera_launch_include,
    ]


def generate_launch_description():
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            'robot_model',
            choices=get_interbotix_xslocobot_models(),
            description=(
              'model type of the Interbotix LoCoBot such as `locobot_base` or `locobot_wx250s`.'
            )
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'arm_model',
            default_value=PythonExpression([
                '"mobile_" + "', LaunchConfiguration('robot_model'), '".split("_")[1]'
            ]),
            description=(
                'the Interbotix Arm model on the LoCoBot; this should never be set manually but '
                'rather left to its default value.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_rviz',
            default_value='false',
            choices=('true', 'false'),
            description='launches RViz if set to `true`.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rviz_frame',
            default_value='base_footprint',
            description=(
                'fixed frame in RViz; this should be changed to `map` or `odom` if '
                'mapping or using local odometry respectively.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_base',
            default_value='false',
            choices=('true', 'false'),
            description='if `true`, the base ROS nodes are launched.',
        )
    )
    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         'use_dock',
    #         default_value='false',
    #         choices=('true', 'false'),
    #         description='if `true`, loads AutoDock features.',
    #     )
    # )
    declared_arguments.append(
        DeclareLaunchArgument(
            'base_type',
            default_value='create3',
            choices=('kobuki', 'create3'),
            description='the type of mobile base used by the robot.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_lidar',
            default_value='false',
            choices=('true', 'false'),
            description='if `true`, the RPLidar node is launched.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_camera',
            default_value='false',
            choices=('true', 'false'),
            description='if `true`, the RealSense camera nodes are launched.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_pointcloud_enable',
            default_value='true',
            choices=('true', 'false'),
            description="enables the RealSense camera's pointcloud.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_rbg_camera_profile',
            default_value='640x480x30',
            description='profile for the rbg camera image stream, in `<width>x<height>x<fps>`.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_depth_module_profile',
            default_value='640x480x30',
            description='profile for the depth module stream, in `<width>x<height>x<fps>`.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_logging_level',
            default_value='info',
            choices=('debug', 'info', 'warn', 'error', 'fatal'),
            description='set the logging level for the realsense2_camera launch include.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_output_location',
            default_value='screen',
            choices=('screen', 'log'),
            description='set the logging location for the realsense2_camera launch include.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_align_depth',
            default_value='false',
            choices=('true', 'false'),
            description=(
                'whether to publish topics with the depth stream aligned with the color stream.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_initial_reset',
            default_value='false',
            choices=('true', 'false'),
            description=(
                'On occasions the RealSense camera is not closed properly and due to firmware '
                'issues needs to reset. If set to `true`, the device will reset prior to usage.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'motor_configs',
            default_value=[PathJoinSubstitution([
                FindPackageShare('interbotix_xslocobot_control'),
                'config',
                LaunchConfiguration('robot_model')]),
                '.yaml'
            ],
            description="the file path to the 'motor config' YAML file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'mode_type',
            default_value=(
                PythonExpression([
                    '"base" if "',
                    LaunchConfiguration('robot_model'),
                    '" == "locobot_base" else "all"'
                ])
            ),
            description='`base` if the robot_model is locobot_base; `all` otherwise',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'mode_configs',
            default_value=[PathJoinSubstitution([
                FindPackageShare('interbotix_xslocobot_control'),
                'config',
                'modes_',
            ]), LaunchConfiguration('mode_type'), '.yaml'],
            description="the file path to the 'mode config' YAML file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'load_configs',
            default_value='true',
            choices=('true', 'false'),
            description=(
                'a boolean that specifies whether or not the initial register values '
                "(under the 'motors' heading) in a Motor Config file should be written "
                "to the motors; as the values being written are stored in each motor's "
                'EEPROM (which means the values are retained even after a power cycle), '
                'this can be set to `false` after the first time using the robot. Setting '
                'to `false` also shortens the node startup time by a few seconds and '
                'preserves the life of the EEPROM.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'xs_driver_logging_level',
            default_value='INFO',
            choices=('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'),
            description='set the logging level of the X-Series Driver.'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_sim',
            default_value='false',
            choices=('true', 'false'),
            description=(
                'if `true`, the DYNAMIXEL simulator node is run; use RViz to visualize the'
                " robot's motion; if `false`, the real DYNAMIXEL driver node is run."
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            choices=('true', 'false'),
            description=(
                'tells ROS nodes asking for time to get the Gazebo-published simulation time, '
                'published over the ROS topic /clock; this value is automatically set to `true` if'
                ' using Gazebo hardware.'
            )
        )
    )
    declared_arguments.extend(
        declare_interbotix_xslocobot_robot_description_launch_arguments()
    )

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])