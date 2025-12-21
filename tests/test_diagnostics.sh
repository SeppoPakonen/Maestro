#!/bin/bash
echo "main.cpp:10:5: error: expected ';' before '}' token" >&2
echo "warning: unused variable 'x'" >&2
echo "info: optimization enabled" >&2
exit 1