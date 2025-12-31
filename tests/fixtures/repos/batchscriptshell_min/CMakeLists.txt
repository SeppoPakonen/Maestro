cmake_minimum_required(VERSION 3.10)
project(bss)

add_executable(bss shell.c redirection_function.c)

# Additional targets to test multiple targets
add_library(common_lib common.c)