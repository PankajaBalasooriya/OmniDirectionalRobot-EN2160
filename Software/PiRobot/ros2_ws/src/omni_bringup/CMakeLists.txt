cmake_minimum_required(VERSION 3.8)
project(omni_bringup)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(DIRECTORY launch config rviz DESTINATION share/${PROJECT_NAME})
if(BUILD_TESTING)
  enable_testing()
  add_test(NAME mount_config_validation
    COMMAND /usr/bin/python3 -m unittest discover -s ${CMAKE_CURRENT_SOURCE_DIR}/test)
  set_tests_properties(mount_config_validation PROPERTIES
    ENVIRONMENT "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}")
endif()
ament_package()
